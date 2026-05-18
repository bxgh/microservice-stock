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

logger = logging.getLogger(__name__)

class QuotaExceededError(Exception):
    """日成本限额超支熔断异常"""
    pass

class LLMClient:
    """
    [E14-S2-P1-T4] 统一异步大模型客户端，支持 DeepSeek V4 高精度计费与配额超支熔断保护
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
        查询指定日期已累计花费的费用 (人民币 CNY)
        """
        sql = "SELECT total_cost_cny FROM meta_llm_daily_cost WHERE cost_date = %s"
        try:
            from shared.db.connection import execute_query
            rows = await execute_query(sql, (cost_date,), is_select=True)
            if rows:
                return float(rows[0]['total_cost_cny'])
            return 0.0
        except Exception as e:
            logger.error(f"Failed to query daily cost from DB: {e}")
            return 0.0

    async def _update_daily_cost(self, cost_date: str, cost: float, input_tokens: int, output_tokens: int):
        """
        使用 MySQL ON DUPLICATE KEY 线程安全更新天级累计消费账目
        """
        sql = """
        INSERT INTO meta_llm_daily_cost (cost_date, total_cost_cny, total_calls, total_input_tokens, total_output_tokens)
        VALUES (%s, %s, 1, %s, %s)
        ON DUPLICATE KEY UPDATE 
            total_cost_cny = total_cost_cny + VALUES(total_cost_cny),
            total_calls = total_calls + 1,
            total_input_tokens = total_input_tokens + VALUES(total_input_tokens),
            total_output_tokens = total_output_tokens + VALUES(total_output_tokens)
        """
        try:
            from shared.db.connection import execute_query
            await execute_query(sql, (cost_date, cost, input_tokens, output_tokens), is_select=False)
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
        依据 DeepSeek 官方计费协议对 token 进行高精度分级计算 (单位：元/CNY)
        
        计费口径：
        1. deepseek-chat (flash & pro 档位)
           - 缓存命中：0.000001元/token (¥1/百万)
           - 缓存未命中：0.000004元/token (¥4/百万)
           - 输出 token：0.000008元/token (¥8/百万)
        2. deepseek-reasoner (pro-thinking 档位)
           - 缓存命中：0.000002元/token (¥2/百万)
           - 缓存未命中：0.000008元/token (¥8/百万)
           - 输出 token (含推理)：0.000016元/token (¥16/百万)
        
        错峰折扣：在 is_off_peak 为 True (00:30-08:30) 时，官方提供折半优惠。
        """
        if mode == "pro-thinking":
            # deepseek-reasoner
            input_cost = (cache_hit_tokens * 0.000002) + (cache_miss_tokens * 0.000008)
            output_cost = output_tokens * 0.000016
        else:
            # deepseek-chat (flash & pro)
            input_cost = (cache_hit_tokens * 0.000001) + (cache_miss_tokens * 0.000004)
            output_cost = output_tokens * 0.000008
            
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
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        """
        大模型异步请求主入口
        
        返回 Dict 结构:
        {
            "content": str,                 # 模型生成正文
            "reasoning_content": str,       # 思考链中间内容 (pro-thinking 专属)
            "input_cache_hit_tokens": int,
            "input_cache_miss_tokens": int,
            "output_tokens": int,
            "reasoning_tokens": int,
            "cost_cny": float,              # 人民币实际计费价格
            "model_name": str,
            "duration_ms": int,             # 耗时
            "is_off_peak": bool             # 是否为错峰计费时段
        }
        """
        # 1. 自动计算当前是否为错峰时段 (北京时间 00:30 - 08:30)
        now_time = datetime.datetime.now().time()
        is_off_peak = datetime.time(0, 30) <= now_time <= datetime.time(8, 30)

        # 2. 预算配额前置安全审计
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        current_daily_cost = await self.get_daily_cost(today_str)
        if current_daily_cost >= self.daily_cost_limit:
            err_msg = f"LLM daily budget exceeded limit! (Current: ¥{current_daily_cost:.4f}, Limit: ¥{self.daily_cost_limit:.4f})"
            logger.error(err_msg)
            raise QuotaExceededError(err_msg)

        # 2. 时延与重试配置
        model = self.reasoner_model if mode == "pro-thinking" else self.chat_model
        timeout = 60.0 if mode == "pro-thinking" else 30.0
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "content" if mode == "pro-thinking" and "deepseek-reasoner" in model else "user", "content": user_prompt}
        ]
        # 兼容官方 API 协议：部分 reasoner 可能不支持 system 字段或 temperature 必须为默认，这里做个平滑处理
        if "deepseek-reasoner" in model:
            # 官方 deepseek-reasoner temperature 必须为 1.0 或不传
            kwargs = {}
            # 官方不支持 system 角色，将其合并为单个 user 提示词
            messages = [
                {"role": "user", "content": f"{system_prompt}\n\n[Context/Input]:\n{user_prompt}"}
            ]
        else:
            kwargs = {"temperature": temperature}

        start_time = datetime.datetime.now()
        
        # 指数退避 3 次重试熔断器
        last_exception = None
        for attempt in range(3):
            try:
                logger.info(f"LLM request starting (Model: {model}, Mode: {mode}, Attempt: {attempt + 1})...")
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
                
                # 3. 提取 Token 使用数据与思考链
                usage = response.usage
                
                # 官方计费划分
                input_tokens = usage.prompt_tokens
                output_tokens = usage.completion_tokens
                
                # 获取缓存命中情况 (OpenAI & DeepSeek 专属 usage 细化)
                cache_hit_tokens = 0
                if hasattr(usage, 'prompt_tokens_details') and usage.prompt_tokens_details:
                    cache_hit_tokens = getattr(usage.prompt_tokens_details, 'cached_tokens', 0)
                # 兼容部分三方接口
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
                
                # 4. 高精度成本测算
                cost = self.calculate_cost(mode, cache_hit_tokens, cache_miss_tokens, output_tokens, is_off_peak=is_off_peak)
                
                # 5. 线程安全持久化天级账单
                await self._update_daily_cost(today_str, cost, input_tokens, output_tokens)
                
                logger.info(f"LLM successful. Cost: ¥{cost:.6f}, reasoning_tokens: {reasoning_tokens}, duration: {duration_ms}ms")
                
                return {
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
