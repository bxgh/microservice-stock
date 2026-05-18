# -*- coding: utf-8 -*-
"""
[E14-S2-P2-T4] AI 政策分析核心主控引擎 policy_analyzer.py
融合上一期措辞比对、大模型 JSON 提纯解析、板块去重融合映射以及幂等落库。
"""

import re
import json
import logging
import datetime
from typing import Dict, Any, List, Optional

from shared.db.connection import execute_query
from shared.utils.llm_client import LLMClient
from shared.utils.policy_classifier import classify_policy
from shared.utils.segment_extractor import extract_key_segment
import shared.utils.prompts as prompts
from shared.utils.schemas import GeneralSummaryOutput, WordingContrastOutput

logger = logging.getLogger(__name__)


class PolicyAnalyzer:
    """
    [E14-S2-P2-T4] 政策 AI 分析主控类
    """
    def __init__(self):
        self.llm_client = LLMClient()

    async def _get_policy_row(self, policy_id: int) -> Optional[Dict[str, Any]]:
        """
        从数据库获取政策详情
        """
        sql = "SELECT * FROM ods_policy_info WHERE id = %s AND is_deleted = 0"
        rows = await execute_query(sql, (policy_id,), is_select=True)
        return rows[0] if rows else None

    async def _update_policy_type(self, policy_id: int, policy_type: str):
        """
        同步更新原始政策表的分类字段
        """
        sql = "UPDATE ods_policy_info SET policy_type = %s WHERE id = %s"
        try:
            await execute_query(sql, (policy_type, policy_id), is_select=False)
        except Exception as e:
            logger.error(f"Failed to update policy_type for id {policy_id}: {e}")

    async def _find_previous_baseline(self, ts_code: str, policy_type: str, current_publish_date: Any) -> Optional[Dict[str, Any]]:
        """
        追溯相同发布方 (ts_code) 和同分类 (policy_type) 的上一期政策作为比对基准
        """
        sql = """
        SELECT id, title, content_text, publish_date 
        FROM ods_policy_info
        WHERE ts_code = %s
          AND policy_type = %s
          AND publish_date < %s
          AND is_deleted = 0
        ORDER BY publish_date DESC
        LIMIT 1
        """
        try:
            rows = await execute_query(sql, (ts_code, policy_type, current_publish_date), is_select=True)
            return rows[0] if rows else None
        except Exception as e:
            logger.error(f"Failed to query previous policy baseline: {e}")
            return None

    async def _get_rule_based_sectors(self, content_text: str) -> List[Dict[str, Any]]:
        """
        通过关键词规则库 (dim_policy_keyword_sector) 提取默认利好板块
        """
        rule_sectors = []
        try:
            sql = "SELECT * FROM dim_policy_keyword_sector WHERE is_deleted = 0"
            rules = await execute_query(sql, is_select=True)
            
            for r in rules:
                keyword = r['keyword']
                # 忽略大小写及空白进行包含匹配
                if keyword and re.search(re.escape(keyword), content_text, re.IGNORECASE):
                    rule_sectors.append({
                        "sector_code_sw": r["sector_code_sw"],
                        "sector_name": r["sector_name"],
                        "impact_direction": "positive",  # 种子规则默认为受益行业
                        "impact_strength": 3,           # 默认中等影响强度
                        "representative_stocks": r["representative_stocks"] or "",
                        "mapping_source": "rule"
                    })
        except Exception as e:
            logger.error(f"Failed to extract rule-based sectors: {e}")
            
        return rule_sectors

    def _merge_sectors(self, llm_sectors: List[Dict[str, Any]], rule_sectors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        混合板块并集去重融合算法 (SectorMapper)
        """
        merged_map = {}
        
        # 1. 灌入规则板块 (基础映射)
        for r in rule_sectors:
            code = r["sector_code_sw"]
            merged_map[code] = r
            
        # 2. 灌入大模型提取的板块，并进行深度融合
        for ls in llm_sectors:
            code = ls.get("sector_code_sw")
            name = ls.get("sector_name")
            
            # 对齐板块识别标识 (申万二级代码)
            key = code if code else name
            if not key:
                continue
                
            direction_raw = ls.get("impact_direction", "positive")
            if not isinstance(direction_raw, str):
                direction_raw = str(direction_raw)
            direction_raw = direction_raw.lower().strip()
            
            if "positive" in direction_raw or "利好" in direction_raw or "增强" in direction_raw:
                direction = "positive"
            elif "negative" in direction_raw or "利空" in direction_raw or "减弱" in direction_raw:
                direction = "negative"
            else:
                direction = "neutral"
            # 允许 LLM 将默认强度 3 覆盖为定制化强度
            strength = ls.get("impact_strength", 3)
            
            # 若已有相同板块规则记录，执行融合
            if key in merged_map:
                existing = merged_map[key]
                merged_map[key] = {
                    "sector_code_sw": existing["sector_code_sw"],
                    "sector_name": name if name else existing["sector_name"],
                    "impact_direction": direction,
                    "impact_strength": strength if strength != 3 else existing["impact_strength"],
                    "representative_stocks": existing["representative_stocks"], # 保留维度表中的股票龙头标的
                    "mapping_source": "merged"
                }
            else:
                # 独属于 LLM 提取的板块
                merged_map[key] = {
                    "sector_code_sw": code if code else "",
                    "sector_name": name,
                    "impact_direction": direction,
                    "impact_strength": strength,
                    "representative_stocks": "",
                    "mapping_source": "llm"
                }
                
        return list(merged_map.values())

    def _robust_parse_json(self, raw_content: str, model_class: Any) -> Dict[str, Any]:
        """
        [E14-S2-P2-T4] 强力 Regex JSON 提纯解析器，杜绝 Markdown 被包裹及 thinking 杂音导致崩溃
        引入 Pydantic 强校验支持，并保留极其顽强的退化兜底防死锁！
        """
        if not raw_content:
            return {}
            
        # 1. 尝试使用正则表达式截取最外层的 { ... }
        match = re.search(r"(\{.*\})", raw_content, re.DOTALL)
        json_str = match.group(1) if match else raw_content
        
        try:
            # 优先采用 Pydantic 强校验与字段填充
            validated_obj = model_class.model_validate_json(json_str)
            dumped_dict = validated_obj.model_dump()
            try:
                raw_dict = json.loads(json_str)
                if isinstance(raw_dict, dict):
                    # 混合合并：保留大模型输出的所有非 Pydantic 额外字段（如 intensity_change 等）
                    return {**raw_dict, **dumped_dict}
            except Exception:
                pass
            return dumped_dict
        except Exception as e:
            logger.warning(f"Pydantic strong validation failed: {e}. Attempting basic JSON parsing fallback...")
            try:
                # 尝试剥除一些常见的反斜杠转义
                fixed_str = json_str.encode('utf-8').decode('unicode_escape')
                match_2 = re.search(r"(\{.*\})", fixed_str, re.DOTALL)
                if match_2:
                    validated_obj_2 = model_class.model_validate_json(match_2.group(1))
                    dumped_dict_2 = validated_obj_2.model_dump()
                    try:
                        raw_dict_2 = json.loads(match_2.group(1))
                        if isinstance(raw_dict_2, dict):
                            return {**raw_dict_2, **dumped_dict_2}
                    except Exception:
                        pass
                    return dumped_dict_2
            except Exception as e2:
                logger.error(f"Second stage Pydantic validation also failed: {e2}")
                
            # 第三层极速退化大防线：退回最基础的 JSON 解析，跳过校验，防止大模型幻觉引起的 Validation 报错导致崩库
            try:
                logger.info("Triggering raw JSON load as a final bypass fallback...")
                return json.loads(json_str)
            except Exception as raw_e:
                logger.error(f"Raw JSON loads also failed: {raw_e}")

            # 最终降级字典，防止系统崩溃
            return {
                "summary_three_sentences": "AI 措辞解析发生异常，已退化为基础降级模式。",
                "importance_level": 3,
                "key_points": [],
                "sectors": []
            }

    async def analyze_policy(
        self, 
        policy_id_or_row: Any, 
        force_deep_mode: str = None, 
        disable_db_write: bool = False,
        reasoning_effort: Optional[str] = None,
        analysis_path: str = 'llm',
        analysis_stage: str = 'triage_and_deep'
    ) -> Dict[str, Any]:
        """
        核心分析逻辑
        """
        # 1. 容错解析入参
        if isinstance(policy_id_or_row, int):
            row = await self._get_policy_row(policy_id_or_row)
        else:
            row = policy_id_or_row
            
        if not row:
            raise ValueError("Target policy row is empty or deleted!")
            
        policy_id = row['id']
        title = row['title']
        content_text = row['content_text']
        ts_code = row['ts_code']
        publish_date = row['publish_date']
        policy_type = row.get('policy_type', 'other')
        
        logger.info(f"--- Starting Policy Analysis [ID: {policy_id}] Title: '{title}' ---")
        
        # 2. 智能补全政策分类 (ods 物理回填)
        if not policy_type or policy_type == "other":
            policy_type = await classify_policy(title, content_text)
            await self._update_policy_type(policy_id, policy_type)
            
        # 3. 结构化长文智能切片
        segment_extracted = 1
        segment_used = extract_key_segment(title, content_text, policy_type)
        if len(segment_used) < len(content_text) and "... [此处省略中间" in segment_used:
            # 触发了 Fallback 动态拼接
            segment_extracted = 0
            
        input_truncated = 1 if len(segment_used) < len(content_text) else 0
        
        # 4. 追溯相同分类上一期基准
        contrast_baseline_id = None
        previous_baseline = await self._find_previous_baseline(ts_code, policy_type, publish_date)
        
        if force_deep_mode == 'triage_only':
            mode = "flash"
            system_prompt = getattr(prompts, 'TRIAGE_CLASSIFIER_SYSTEM_V1', prompts.GENERAL_SUMMARY_SYSTEM_V3)
            user_prompt = f"请初筛分类以下政策：\n【标题】{title}\n【正文】\n{segment_used}"
            prompt_name = "TRIAGE_CLASSIFIER_V1"
            prompt_version = "1.0"
            previous_baseline = None
            analysis_stage = "triage_only"
            logger.info("Executing Stage 1: Triage Classification...")
        else:
            mode = "flash"
            system_prompt = prompts.GENERAL_SUMMARY_SYSTEM_V3

        if previous_baseline:
            contrast_baseline_id = previous_baseline['id']
            # 对上期文本也做一次提取，防止超长
            previous_segment = extract_key_segment(previous_baseline['title'], previous_baseline['content_text'], policy_type)
            
            # 升级为 deepseek-reasoner (思维链高阶分析)
            mode = "pro-thinking"
            system_prompt = prompts.WORDING_CONTRAST_SYSTEM_V3
            user_prompt = (
                f"请对比以下两期政策：\n"
                f"【上期政策】\n{previous_segment}\n\n"
                f"【本期政策】\n{segment_used}"
            )
            prompt_name = "WORDING_CONTRAST_V3"
            prompt_version = "3.0"
            logger.info(f"Baseline policy anchored (ID: {contrast_baseline_id}). Upgrading model to 'pro-thinking'...")
        elif force_deep_mode != 'triage_only':
            # 通用单期摘要模式
            mode = "deep"
            system_prompt = prompts.GENERAL_SUMMARY_SYSTEM_V3
            user_prompt = (
                f"请分析以下政策：\n"
                f"【标题】{title}\n"
                f"【正文】\n{segment_used}"
            )
            prompt_name = "GENERAL_SUMMARY_V3"
            prompt_version = "3.0"
            logger.info("No baseline policy found. Running standard summary mode via 'deep'...")

        # 5. 调用大模型客户端并进行成本审计 (CLS 可观测性日志闭环)
        try:
            llm_result = await self.llm_client.chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                mode=mode,
                temperature=0.1,
                reasoning_effort=reasoning_effort,
                prompt_name=prompt_name,
                prompt_version=prompt_version
            )
            # CLS 成功结构化日志
            cls_log = {
                "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "level": "INFO",
                "event": "llm_call_completed",
                "policy_id": policy_id,
                "prompt_name": prompt_name,
                "prompt_version": prompt_version,
                "model": llm_result["model_name"],
                "thinking_enabled": True if mode == "pro-thinking" else False,
                "input_cache_hit_tokens": llm_result["input_cache_hit_tokens"],
                "input_cache_miss_tokens": llm_result["input_cache_miss_tokens"],
                "output_tokens": llm_result["output_tokens"],
                "reasoning_tokens": llm_result["reasoning_tokens"],
                "cost_cny": llm_result["cost_cny"],
                "duration_ms": llm_result["duration_ms"],
                "status": "success",
                "is_cache_hit": llm_result.get("is_cache_hit", False)
            }
            logger.info(f"CLS_STRUCTURED_LOG: {json.dumps(cls_log, ensure_ascii=False)}")
        except Exception as e:
            # CLS 失败结构化日志 (P0 级告警源)
            cls_log = {
                "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "level": "ERROR",
                "event": "llm_call_completed",
                "policy_id": policy_id,
                "prompt_name": prompt_name,
                "prompt_version": prompt_version,
                "model": "deepseek-reasoner" if mode == "pro-thinking" else "deepseek-chat",
                "thinking_enabled": True if mode == "pro-thinking" else False,
                "input_cache_hit_tokens": 0,
                "input_cache_miss_tokens": 0,
                "output_tokens": 0,
                "reasoning_tokens": 0,
                "cost_cny": 0.0,
                "duration_ms": 0,
                "status": "api_error",
                "error_message": str(e)
            }
            logger.error(f"CLS_STRUCTURED_LOG: {json.dumps(cls_log, ensure_ascii=False)}")
            raise e
        
        # 6. 正则防崩提纯 JSON
        if force_deep_mode == 'triage_only':
            from shared.utils.schemas import TriageOutput
            target_model = TriageOutput
        else:
            target_model = WordingContrastOutput if previous_baseline else GeneralSummaryOutput
        analysis_data = self._robust_parse_json(llm_result.get("content", ""), target_model)
        
        # 7. 提取与融合申万板块影响
        llm_sectors = analysis_data.get("sectors", [])
        rule_sectors = await self._get_rule_based_sectors(segment_used)
        merged_sectors = self._merge_sectors(llm_sectors, rule_sectors)
        
        if disable_db_write:
            triage_summary = analysis_data.get("triage_summary")
            summary_three = analysis_data.get("summary_three_sentences")
            return {
                "policy_id": policy_id,
                "analysis_id": None,
                "policy_type": policy_type,
                "summary": triage_summary or summary_three or "未生成摘要。",
                "importance_level": analysis_data.get("importance_level", 3),
                "intensity_change": analysis_data.get("intensity_change", "N/A"),
                "cost_cny": llm_result["cost_cny"]
            }
            
        # 8. 执行物理表数据落库/更新至 dwd_policy_analysis (联合唯一索引防重入)
        # 对齐数据契约列名
        summary_str = analysis_data.get("summary_three_sentences", "未生成摘要。")
        importance_level = analysis_data.get("importance_level", 3)
        importance_reason = analysis_data.get("importance_reason", "无特定理由。")
        intensity_change = analysis_data.get("intensity_change", "N/A")
        
        # 将 positive 与 negative 板块分类提取存入明细
        pos_sectors = [s for s in merged_sectors if s['impact_direction'] == 'positive']
        neg_sectors = [s for s in merged_sectors if s['impact_direction'] == 'negative']
        
        key_diff_str = json.dumps(analysis_data.get("contrast_details", []), ensure_ascii=False)
        implication_str = analysis_data.get("implication", "市场暂无明显指引。")
        
        # 若发生缓存拦截命中，改写 analysis_path 并覆盖所有的消费/token 数据为 0
        final_analysis_path = 'cache' if llm_result.get("is_cache_hit") else analysis_path
        
        sql_analysis = """
        INSERT INTO dwd_policy_analysis (
            policy_id, analysis_path, analysis_stage, summary, importance_level, importance_reason, 
            sectors_positive, sectors_negative, intensity_change, key_differences, 
            implication, contrast_baseline_id, segment_used, segment_extracted, 
            input_truncated, prompt_name, prompt_version, model_name, 
            thinking_enabled, reasoning_effort, input_cache_hit_tokens, 
            input_cache_miss_tokens, output_tokens, reasoning_tokens, cost_cny
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        ) ON DUPLICATE KEY UPDATE 
            analysis_path = VALUES(analysis_path),
            analysis_stage = VALUES(analysis_stage),
            summary = VALUES(summary),
            importance_level = VALUES(importance_level),
            importance_reason = VALUES(importance_reason),
            sectors_positive = VALUES(sectors_positive),
            sectors_negative = VALUES(sectors_negative),
            intensity_change = VALUES(intensity_change),
            key_differences = VALUES(key_differences),
            implication = VALUES(implication),
            contrast_baseline_id = VALUES(contrast_baseline_id),
            segment_used = VALUES(segment_used),
            segment_extracted = VALUES(segment_extracted),
            input_truncated = VALUES(input_truncated),
            model_name = VALUES(model_name),
            input_cache_hit_tokens = VALUES(input_cache_hit_tokens),
            input_cache_miss_tokens = VALUES(input_cache_miss_tokens),
            output_tokens = VALUES(output_tokens),
            reasoning_tokens = VALUES(reasoning_tokens),
            cost_cny = VALUES(cost_cny),
            updated_at = CURRENT_TIMESTAMP
        """
        
        thinking_enabled = 1 if mode == "pro-thinking" else 0
        
        if llm_result.get("is_cache_hit"):
            cache_hit_tok = 0
            cache_miss_tok = 0
            out_tok = 0
            reas_tok = 0
            cost_val = 0.000000
        else:
            cache_hit_tok = llm_result["input_cache_hit_tokens"]
            cache_miss_tok = llm_result["input_cache_miss_tokens"]
            out_tok = llm_result["output_tokens"]
            reas_tok = llm_result["reasoning_tokens"]
            cost_val = llm_result["cost_cny"]

        params_analysis = (
            policy_id, final_analysis_path, analysis_stage, summary_str, importance_level, importance_reason,
            json.dumps(pos_sectors, ensure_ascii=False), json.dumps(neg_sectors, ensure_ascii=False),
            intensity_change, key_diff_str, implication_str, contrast_baseline_id,
            segment_used, segment_extracted, input_truncated, prompt_name, prompt_version,
            llm_result["model_name"], thinking_enabled, reasoning_effort or ("medium" if thinking_enabled else None),
            cache_hit_tok, cache_miss_tok, out_tok, reas_tok, cost_val
        )
        
        # 物理灌入明细
        await execute_query(sql_analysis, params_analysis, is_select=False)
        
        # 获取刚才写入的明细自增 ID
        sql_get_id = """
        SELECT id FROM dwd_policy_analysis 
        WHERE policy_id = %s AND prompt_name = %s AND prompt_version = %s
        """
        rows_id = await execute_query(sql_get_id, (policy_id, prompt_name, prompt_version), is_select=True)
        analysis_id = rows_id[0]['id']
        
        # 9. 刷新板块明细扁平表 (保证零数据冗余)
        await execute_query(
            "DELETE FROM dwd_policy_sector_impact WHERE policy_id = %s AND analysis_id = %s",
            (policy_id, analysis_id),
            is_select=False
        )
        
        if merged_sectors:
            sql_sector = """
            INSERT INTO dwd_policy_sector_impact (
                policy_id, analysis_id, sector_code_sw, sector_name, 
                impact_direction, impact_strength, representative_stocks, mapping_source
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            for s in merged_sectors:
                # 剔除受损或中性打标中为空的板块
                if not s["sector_code_sw"] and not s["sector_name"]:
                    continue
                await execute_query(
                    sql_sector,
                    (
                        policy_id, analysis_id, s["sector_code_sw"], s["sector_name"],
                        s["impact_direction"], s["impact_strength"], s["representative_stocks"],
                        s["mapping_source"]
                    ),
                    is_select=False
                )
                
        logger.info(f"--- Policy Analysis Completed [ID: {policy_id}] Analysis ID: {analysis_id} Cost: ¥{cost_val:.6f} ---")
        
        # 更新 policy 状态为已分析就绪
        await execute_query(
            "UPDATE ods_policy_info SET analysis_status = 'analyzed' WHERE id = %s",
            (policy_id,),
            is_select=False
        )
        
        return {
            "policy_id": policy_id,
            "analysis_id": analysis_id,
            "policy_type": policy_type,
            "summary": summary_str,
            "importance_level": importance_level,
            "intensity_change": intensity_change,
            "cost_cny": cost_val
        }

