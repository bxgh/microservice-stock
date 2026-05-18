import os
import datetime
import asyncio
import logging
from typing import Optional, Dict, Any
try:
    from typing import Literal
except ImportError:
    try:
        from typing_extensions import Literal
    except ImportError:
        class LiteralDummy:
            def __getitem__(self, item):
                return Any
        Literal = LiteralDummy()
from openai import AsyncOpenAI

from shared.utils.off_peak_scheduler import OffPeakScheduler
from shared.utils.response_cache import ResponseCache

logger = logging.getLogger(__name__)

class QuotaExceededError(Exception):
    """日成本限额超支熔断异常"""
    pass

class LLMClient:
    """
    [E14-S2-P1-T4] 统一异步大模型客户端，支持 DeepSeek V4 高精度计费与配额超支熔断保护，支持缓存与错峰调度。
    """
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
        self.daily_cost_limit = float(os.getenv("LLM_DAILY_COST_LIMIT_CNY", 5.0))
        
        # 允许通过环境变量重写模型名，默认为 DeepSeek 官方接口标准
        self.chat_model = os.getenv("DEEPSEEK_CHAT_MODEL", "deepseek-chat")
        self.reasoner_model = os.getenv("DEEPSEEK_REASONER_MODEL", "deepseek-reasoner")
        
        if not self.api_key:
            logger.warning("DEEPSEEK_API_KEY is not configured in environment variables!")

        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def get_daily_cost(self, cost_date: str) -> float:
        """
        查询指定日期已累计花费的费用 (人民币 CNY，支持合并错峰/正常时段账单)
        """
        sql = "SELECT SUM(total_cost_cny) as total_cost_cny FROM meta_llm_daily_cost WHERE cost_date = %s"
        try:
            from shared.db.connection import execute_query
            rows = await execute_query(sql, (cost_date,), is_select=True)
            if rows and rows[0]['total_cost_cny'] is not None:
                return float(rows[0]['total_cost_cny'])
            return 0.0
        except Exception as e:
            logger.error(f"Failed to query daily cost from DB: {e}")
            return 0.0

    async def _update_daily_cost(self, cost_date: str, cost: float, input_tokens: int, output_tokens: int, is_off_peak: bool = False):
        """
        使用 MySQL ON DUPLICATE KEY 线程安全更新天级累计消费账目 (支持错峰复合主键分立)
        """
        sql = """
        INSERT INTO meta_llm_daily_cost (cost_date, is_off_peak, total_cost_cny, total_calls, total_input_tokens, total_output_tokens)
        VALUES (%s, %s, %s, 1, %s, %s)
        ON DUPLICATE KEY UPDATE 
            total_cost_cny = total_cost_cny + VALUES(total_cost_cny),
            total_calls = total_calls + 1,
            total_input_tokens = total_input_tokens + VALUES(total_input_tokens),
            total_output_tokens = total_output_tokens + VALUES(total_output_tokens)
        """
        try:
            from shared.db.connection import execute_query
            await execute_query(sql, (cost_date, 1 if is_off_peak else 0, cost, input_tokens, output_tokens), is_select=False)
        except Exception as e:
            logger.error(f"Failed to update daily cost in DB: {e}")

    def calculate_cost(
        self, 
        mode: Literal["flash", "pro", "pro-thinking"], 
        cache_hit_tokens: int, 
        cache_miss_tokens: int, 
        output_tokens: int,
        is_off_peak: bool = False
    ) -> float:
        """
        依据 DeepSeek 官方最新发布的 V4 (Mix-of-Experts) 计费协议进行高精度计算 (单位：元/CNY)
        - deepseek-v4-flash: 输入(未命中) 1元/百万, 输入(命中) 0.2元/百万, 输出 2元/百万
        - deepseek-v4-pro (Reasoner): 输入(未命中) 3元/百万, 输入(命中) 0.3元/百万, 输出 6元/百万
        """
        if mode == "pro-thinking":
            # deepseek-v4-pro / deepseek-reasoner
            input_cost = (cache_hit_tokens * 0.0000003) + (cache_miss_tokens * 0.000003)
            output_cost = output_tokens * 0.000006
        else:
            # deepseek-v4-flash / deepseek-chat
            input_cost = (cache_hit_tokens * 0.0000002) + (cache_miss_tokens * 0.000001)
            output_cost = output_tokens * 0.000002
            
        base_cost = input_cost + output_cost
        if is_off_peak:
            logger.info("Applying off-peak 50% discount to local cost auditing.")
            base_cost *= 0.5
            
        return round(base_cost, 6)

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        mode: Literal["flash", "pro", "pro-thinking"] = "flash",
        temperature: float = 0.2,
        reasoning_effort: Optional[str] = None,
        prompt_name: str = "DEFAULT_PROMPT",
        prompt_version: str = "1.0",
        is_heartbeat: bool = False
    ) -> Dict[str, Any]:
        """
        大模型异步请求主入口
        """
        # 1. 自动计算当前是否为错峰时段 (采用时区安全的 OffPeakScheduler)
        is_off_peak = OffPeakScheduler.is_off_peak()

        # 2. 确定物理模型与请求配置
        model = self.reasoner_model if mode == "pro-thinking" else self.chat_model
        timeout = 60.0 if mode == "pro-thinking" else 30.0

        # 3. 拦截应用层缓存 (心跳保活强制穿透)
        cache_key = ResponseCache.generate_key(prompt_name, prompt_version, model, user_prompt)
        if not is_heartbeat:
            cached_res = await ResponseCache.get(cache_key)
            if cached_res:
                logger.info(f"[ResponseCache HIT] Bypassing physical API call for key: {cache_key}")
                # 对齐高精度字段契约，覆盖消耗为 0
                cached_res["cost_cny"] = 0.000000
                cached_res["input_cache_hit_tokens"] = 0
                cached_res["input_cache_miss_tokens"] = 0
                cached_res["output_tokens"] = 0
                cached_res["reasoning_tokens"] = 0
                cached_res["is_cache_hit"] = True
                cached_res["duration_ms"] = 0
                return cached_res

        # 4. 预算配额前置安全审计
        today_str = OffPeakScheduler.get_beijing_now().strftime("%Y-%m-%d")
        current_daily_cost = await self.get_daily_cost(today_str)
        if current_daily_cost >= self.daily_cost_limit:
            err_msg = f"LLM daily budget exceeded limit! (Current: ¥{current_daily_cost:.4f}, Limit: ¥{self.daily_cost_limit:.4f})"
            logger.error(err_msg)
            raise QuotaExceededError(err_msg)

        # 5. 组装并格式化 Messages，支持 reasoning_effort 传递
        if "deepseek-reasoner" in model:
            # 官方 deepseek-reasoner 不支持 system 角色，将其合并为单个 user 提示词，且 temperature 恒定为 1.0/不传
            kwargs = {}
            if reasoning_effort:
                kwargs["reasoning_effort"] = reasoning_effort
            messages = [
                {"role": "user", "content": f"{system_prompt}\n\n[Context/Input]:\n{user_prompt}"}
            ]
        else:
            kwargs = {"temperature": temperature}
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

        start_time = datetime.datetime.now()
        
        # 指数退避 3 次重试熔断器
        last_exception = None
        for attempt in range(3):
            try:
                logger.info(f"LLM request starting (Model: {model}, Mode: {mode}, Attempt: {attempt + 1}, reasoning_effort: {reasoning_effort}, is_heartbeat: {is_heartbeat})...")
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=model,
                        messages=messages,
                        stream=False,
                        **kwargs
                    ),
                    timeout=timeout
                )
                
                # 请求耗时
                duration_ms = int((datetime.datetime.now() - start_time).total_seconds() * 1000)
                
                # 6. 提取 Token 使用数据与思考链
                usage = response.usage
                input_tokens = usage.prompt_tokens
                output_tokens = usage.completion_tokens
                
                # 获取缓存命中情况 (OpenAI & DeepSeek 专属 usage 细化)
                cache_hit_tokens = 0
                if hasattr(usage, 'prompt_tokens_details') and usage.prompt_tokens_details:
                    cache_hit_tokens = getattr(usage.prompt_tokens_details, 'cached_tokens', 0)
                elif hasattr(usage, 'prompt_cache_hit_tokens'):
                    cache_hit_tokens = usage.prompt_cache_hit_tokens
                    
                cache_miss_tokens = max(0, input_tokens - cache_hit_tokens)
                
                # 深度思考推理 Token
                reasoning_tokens = 0
                reasoning_content = ""
                message_obj = response.choices[0].message
                
                if hasattr(message_obj, 'reasoning_content') and message_obj.reasoning_content:
                    reasoning_content = message_obj.reasoning_content
                if hasattr(usage, 'completion_tokens_details') and usage.completion_tokens_details:
                    reasoning_tokens = getattr(usage.completion_tokens_details, 'reasoning_tokens', 0)
                
                # 7. 高精度成本测算
                cost = self.calculate_cost(mode, cache_hit_tokens, cache_miss_tokens, output_tokens, is_off_peak=is_off_peak)
                
                # 8. 线程安全持久化天级账单 (支持错峰复合主键分立)
                await self._update_daily_cost(today_str, cost, input_tokens, output_tokens, is_off_peak=is_off_peak)
                
                logger.info(f"LLM successful. Cost: ¥{cost:.6f}, reasoning_tokens: {reasoning_tokens}, duration: {duration_ms}ms")
                
                result = {
                    "content": message_obj.content,
                    "reasoning_content": reasoning_content,
                    "input_cache_hit_tokens": cache_hit_tokens,
                    "input_cache_miss_tokens": cache_miss_tokens,
                    "output_tokens": output_tokens,
                    "reasoning_tokens": reasoning_tokens,
                    "cost_cny": cost,
                    "model_name": model,
                    "duration_ms": duration_ms,
                    "is_off_peak": is_off_peak
                }

                # 9. 静默保存结果到物理缓存，以备下次拦截 (心跳保活不存入缓存)
                if not is_heartbeat:
                    save_dict = result.copy()
                    await ResponseCache.set(cache_key, prompt_name, prompt_version, model, save_dict)
                
                return result
                
            except asyncio.TimeoutError as e:
                logger.warning(f"LLM attempt {attempt + 1} timed out after {timeout} seconds.")
                last_exception = e
            except Exception as e:
                logger.warning(f"LLM attempt {attempt + 1} failed with error: {e}")
                last_exception = e
                
            if attempt < 2:
                # 1s, 2s 的退避重试时延
                await asyncio.sleep(2 ** attempt)
                
        # 所有尝试均告失败
        logger.error("LLM request failed completely after 3 attempts.")
        raise last_exception

