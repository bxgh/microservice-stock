# -*- coding: utf-8 -*-
"""
[E15-M1-T3] 多级路由分析调度器 staged_analyzer.py
实现规则零费用阻断、影子对照双跑（shadow）、降准混合解读（rule_then_llm）与防裸奔 Fallback 兜底。
"""

import os
import json
import logging
import datetime
from typing import Dict, Any, Optional

from shared.db.connection import execute_query
from shared.utils.policy_analyzer import PolicyAnalyzer
from shared.utils.simhash import compute_simhash, hamming_distance
from shared.extractors.rule_based.lpr_extractor import LPRExtractor
from shared.extractors.rule_based.omo_extractor import OMOExtractor
from shared.extractors.rule_based.mlf_extractor import MLFExtractor
from shared.extractors.rule_based.rrr_extractor import RRRExtractor
from shared.extractors.rule_based.holiday_extractor import HolidayExtractor

logger = logging.getLogger(__name__)

class StagedAnalyzer:
    """
    分级政策分析调度主控
    """
    async def find_similar_previous_policy(
        self, 
        current_policy_id: int, 
        current_ts_code: str, 
        current_policy_type: str, 
        current_publish_date: Any, 
        current_simhash: str
    ) -> Optional[Dict[str, Any]]:
        """
        E6-S1: 在 dwd_policy_analysis 中查找同 ts_code 和 policy_type 且距离最近的已分析历史政策。
        返回包含最相似记录、汉明距离及相似度分类的字典，若未找到则返回 None。
        """
        if not current_simhash or current_simhash == "0000000000000000":
            return None

        # 查询同 ts_code 与 policy_type 的历史记录 (按发布时间倒序，取前 5 条以做汉明距离比对，找到最相似的一条)
        sql = """
        SELECT a.id, a.policy_id, a.core_segment_simhash, o.title, o.publish_date
        FROM dwd_policy_analysis a
        JOIN ods_policy_info o ON a.policy_id = o.id
        WHERE o.ts_code = %s
          AND o.policy_type = %s
          AND o.id != %s
          AND o.publish_date <= %s
          AND a.core_segment_simhash IS NOT NULL
          AND o.is_deleted = 0
        ORDER BY o.publish_date DESC
        LIMIT 5
        """
        try:
            rows = await execute_query(sql, (current_ts_code, current_policy_type, current_policy_id, current_publish_date), is_select=True)
            if not rows:
                return None
                
            best_match = None
            min_distance = 64
            
            for row in rows:
                hist_hash = row["core_segment_simhash"]
                distance = hamming_distance(current_simhash, hist_hash)
                if distance < min_distance:
                    min_distance = distance
                    best_match = row
                    
            if best_match:
                # 判定相似度等级
                if min_distance <= 3:
                    rating = "high"
                elif min_distance <= 8:
                    rating = "moderate"
                else:
                    rating = "low"
                    
                return {
                    "matched_policy_id": best_match["policy_id"],
                    "matched_analysis_id": best_match["id"],
                    "matched_title": best_match["title"],
                    "matched_publish_date": best_match["publish_date"],
                    "hamming_distance": min_distance,
                    "similarity_rating": rating
                }
        except Exception as e:
            logger.error(f"Failed to find similar previous policy: {e}")
            
        return None

    def __init__(self):
        self.analyzer = PolicyAnalyzer()
        # 初始化 5 大零成本提取器
        self.extractors = {
            "HolidayExtractor": HolidayExtractor(),
            "OMOExtractor": OMOExtractor(),
            "MLFExtractor": MLFExtractor(),
            "LPRExtractor": LPRExtractor(),
            "RRRExtractor": RRRExtractor()
        }
        
        # 加载思考预算配置矩阵
        import yaml
        self.reasoning_matrix = {}
        matrix_path = os.path.join(os.path.dirname(__file__), "reasoning_effort_matrix.yaml")
        if os.path.exists(matrix_path):
            try:
                with open(matrix_path, "r", encoding="utf-8") as f:
                    self.reasoning_matrix = yaml.safe_load(f) or {}
                logger.info(f"Successfully loaded reasoning effort matrix config from {matrix_path}")
            except Exception as e:
                logger.error(f"Failed to parse reasoning_effort_matrix.yaml: {e}")

    def _resolve_reasoning_effort(self, policy_type: str, importance: int) -> Optional[str]:
        """
        根据政策分类与初筛重要性星级从配置矩阵中决策大模型推理档位 (high / max / None)
        """
        if not self.reasoning_matrix:
            return None
        
        type_config = self.reasoning_matrix.get(policy_type)
        if not type_config:
            type_config = self.reasoning_matrix.get("default", {})
            
        return type_config.get(importance)

    async def analyze_policy(self, policy_id_or_row: Any) -> Dict[str, Any]:
        """
        分级分析调度主入口
        """
        # 1. 解析 row 详情
        if isinstance(policy_id_or_row, int):
            row = await self.analyzer._get_policy_row(policy_id_or_row)
        else:
            row = policy_id_or_row
 
        if not row:
            raise ValueError("Target policy row is empty or deleted!")
 
        policy_id = row['id']
        title = row['title']
        content_text = row['content_text']
        ts_code = row['ts_code']
        publish_date = row['publish_date']
        
        logger.info(f"--- [StagedAnalyzer] Starting analysis for Policy ID: {policy_id} Title: '{title}' ---")
 
        # 智能获取调度路径配置，默认为 shadow 影子跑，防止裸奔
        route_enabled = os.getenv("RULE_BASED_PATH_ENABLED", "shadow").lower().strip()
        logger.info(f"Current Staged Routing Mode: '{route_enabled}'")
 
        # 2. 依次遍历提取器进行零成本匹配
        matched_extractor_name = None
        matched_data = None
        matched_extractor = None
 
        for name, extractor in self.extractors.items():
            try:
                data = extractor.extract(title, content_text)
                if data is not None:
                    matched_extractor_name = name
                    matched_data = data
                    matched_extractor = extractor
                    logger.info(f"Matched rule-based extractor: '{name}' v{extractor.VERSION} with data: {data}")
                    break
            except Exception as e:
                logger.error(f"Rule extractor '{name}' encountered error during extract: {e}")
 
        # 3. 分级路由核心判定树
        if matched_extractor_name is not None:
            # Case 3.1: 如果是放假/休市行政通知 (HolidayExtractor) -> 直接零 Token 阻断！
            if matched_extractor_name == "HolidayExtractor":
                logger.info(f"[Zero-Token BLOCK] Holiday notice identified by HolidayExtractor. Bypassing LLM directly.")
                return await self._write_rule_result_to_db(
                    row=row,
                    extractor_name=matched_extractor_name,
                    extractor=matched_extractor,
                    extracted_data=matched_data,
                    target_table="dwd_policy_analysis"
                )
 
            # Case 3.2: 如果是存款准备金率 (RRRExtractor) -> 执行 rule_then_llm 专家混合链路！
            elif matched_extractor_name == "RRRExtractor":
                logger.info("[Hybrid Route] RRR cut identified. Triggering 'rule_then_llm' expert-hybrid flow...")
                return await self._run_rule_then_llm_hybrid(
                    row=row,
                    extracted_data=matched_data,
                    extractor=matched_extractor
                )
 
            # Case 3.3: 如果是常规业务货政 (OMO, MLF, LPR) -> 根据环境变量进行路由
            else:
                if route_enabled == "disabled":
                    logger.info("Rule-based path is 'disabled'. Routing to standard LLM path.")
                    return await self.analyzer.analyze_policy(
                        row, 
                        analysis_path='llm', 
                        analysis_stage='triage_and_deep'
                    )
 
                elif route_enabled == "shadow":
                    logger.info("[Shadow Dual-Run] Routing to parallel write. Rule result -> Shadow Table, LLM result -> Prod Table.")
                    # 1. 规则提取静默落入影子对照表
                    try:
                        await self._write_rule_result_to_db(
                            row=row,
                            extractor_name=matched_extractor_name,
                            extractor=matched_extractor,
                            extracted_data=matched_data,
                            target_table="dwd_policy_analysis_shadow"
                        )
                        logger.info("Shadow rule result successfully written to 'dwd_policy_analysis_shadow'.")
                    except Exception as e:
                        logger.error(f"[Shadow Write Fail-Safe] Shadow database insert failed: {e}")
                    
                    # 2. 主线依然拉起原大模型全路径，保证生产环境不受任何格式或内容泄漏污染
                    return await self.analyzer.analyze_policy(
                        row, 
                        analysis_path='llm', 
                        analysis_stage='triage_and_deep'
                    )
 
                elif route_enabled == "production":
                    logger.info("[Production Cut-Through] Direct cutting to rule-based path! Saving LLM tokens.")
                    try:
                        return await self._write_rule_result_to_db(
                            row=row,
                            extractor_name=matched_extractor_name,
                            extractor=matched_extractor,
                            extracted_data=matched_data,
                            target_table="dwd_policy_analysis"
                        )
                    except Exception as e:
                        # P0 防御大底座：如果规则落库在 production 下不幸报错，立刻 fallback 兜底回大模型全链路！
                        logger.error(f"[FAILSAFE-FALLBACK] Production rule write failed: {e}. Fallbacking to full LLM route!")
                        # 强力回流，并在返回数据中注入 bypass_failed=1 标志
                        res = await self.analyzer.analyze_policy(
                            row,
                            analysis_path='llm',
                            analysis_stage='triage_and_deep'
                        )
                        res["bypass_failed"] = 1
                        return res
                else:
                    logger.warning(f"Unknown routing mode '{route_enabled}'. Defaulting to LLM path.")
                    return await self.analyzer.analyze_policy(
                        row,
                        analysis_path='llm',
                        analysis_stage='triage_and_deep'
                    )
 
        # Case 4: 没有任何规则匹配上 -> 执行 E15-S2 初筛分级路由
        if os.getenv('STAGED_ANALYSIS_ENABLED', 'true').lower() == 'false':
            from shared.utils.segment_extractor import extract_key_segment
            from shared.utils.policy_classifier import classify_policy
            
            policy_type = row.get('policy_type')
            if not policy_type or policy_type == "other":
                policy_type = await classify_policy(title, content_text)
                
            segment_used = extract_key_segment(title, content_text, policy_type)
            current_simhash = compute_simhash(segment_used)
            
            similar_info = await self.find_similar_previous_policy(
                current_policy_id=policy_id,
                current_ts_code=ts_code,
                current_policy_type=policy_type,
                current_publish_date=publish_date,
                current_simhash=current_simhash
            )
            
            if similar_info:
                dist = similar_info["hamming_distance"]
                rating = similar_info["similarity_rating"]
                logger.info(
                    f"[Similarity Check] Found similar historical policy (ID: {similar_info['matched_policy_id']}, "
                    f"Title: '{similar_info['matched_title']}'). Hamming Distance: {dist}, Rating: {rating}"
                )
                if rating == "high":
                    logger.warning(
                        f"[Similarity Alert] Highly similar policy detected (Distance: {dist} <= 3)! "
                        f"Targeting for future E6-S2 Diff route."
                    )
            
            res = await self.analyzer.analyze_policy(
                row,
                analysis_path='llm',
                analysis_stage='triage_and_deep'
            )
            if similar_info:
                res["similarity_detection"] = similar_info
            return res
 
        logger.info("No rule extractors matched. Initiating Stage 1: Triage Classification...")
        
        # 为了兼容旧代码，这里直接调用原分析器。实际 E15-S2 会拉起 triage_only
        triage_res = await self.analyzer.analyze_policy(
            row, 
            force_deep_mode='triage_only', 
            disable_db_write=True,
            analysis_path='llm',
            analysis_stage='triage_only'
        )
        importance = triage_res.get('importance_level', 3)
        confidence = triage_res.get('triage_confidence', 1.0)
        
        # 智能补齐政策分类
        policy_type = row.get('policy_type')
        if not policy_type or policy_type == "other":
            from shared.utils.policy_classifier import classify_policy
            policy_type = await classify_policy(title, content_text)

        # E6-S1: 进行相似度前置检测
        current_simhash = triage_res.get("core_segment_simhash")
        similar_info = await self.find_similar_previous_policy(
            current_policy_id=policy_id,
            current_ts_code=ts_code,
            current_policy_type=policy_type,
            current_publish_date=publish_date,
            current_simhash=current_simhash
        )
        
        if similar_info:
            dist = similar_info["hamming_distance"]
            rating = similar_info["similarity_rating"]
            logger.info(
                f"[Similarity Check] Found similar historical policy (ID: {similar_info['matched_policy_id']}, "
                f"Title: '{similar_info['matched_title']}'). Hamming Distance: {dist}, Rating: {rating}"
            )
            if rating == "high":
                logger.warning(
                    f"[Similarity Alert] Highly similar policy detected (Distance: {dist} <= 3)! "
                    f"Targeting for future E6-S2 Diff route."
                )

        if importance <= 3 and confidence > 0.8:
            logger.info("[Token Saved] Low importance policy blocked by triage. Skipping deep analysis.")
            triage_res['routing_path'] = 'triage_only'
            # 简化版：直接落库
            await self._write_triage_to_db(row, triage_res)
            if similar_info:
                triage_res["similarity_detection"] = similar_info
            return triage_res
            
        elif importance == 4 or (importance <= 3 and confidence <= 0.8):
            logger.info("Upgrading to triage_and_deep path.")
            effort = self._resolve_reasoning_effort(policy_type, importance)
            res = await self.analyzer.analyze_policy(
                row,
                reasoning_effort=effort,
                analysis_path='llm',
                analysis_stage='triage_and_deep'
            )
            res['routing_path'] = 'triage_and_deep'
            if similar_info:
                res["similarity_detection"] = similar_info
            return res
            
        else:
            logger.info("Upgrading to triage_and_voting path (5-star policy).")
            import asyncio
            effort = self._resolve_reasoning_effort(policy_type, importance)
            coros = [
                self.analyzer.analyze_policy(
                    row, 
                    force_deep_mode='deep_only', 
                    disable_db_write=True,
                    reasoning_effort=effort,
                    analysis_path='llm',
                    analysis_stage='triage_and_voting'
                ) for _ in range(3)
            ]
            results = await asyncio.gather(*coros, return_exceptions=True)
            valid_results = [r for r in results if not isinstance(r, Exception)]
            
            if not valid_results:
                logger.warning("All 3 voting branches failed with exceptions! Fallbacking to standard.")
                res = await self.analyzer.analyze_policy(
                    row,
                    analysis_path='llm',
                    analysis_stage='triage_and_deep'
                )
                res['routing_path'] = 'triage_and_deep'
                if similar_info:
                    res["similarity_detection"] = similar_info
                return res
            
            # 取第一票作为兜底
            best_res = valid_results[0]
            best_res['routing_path'] = 'triage_and_voting'
            
            # 计算 majority intensity
            from collections import Counter
            intensities = [r.get('intensity_change') for r in valid_results if r.get('intensity_change')]
            if intensities:
                best_res['intensity_change'] = Counter(intensities).most_common(1)[0][0]
                
            await self._write_triage_to_db(row, best_res)
            if similar_info:
                best_res["similarity_detection"] = similar_info
            return best_res

    async def _write_triage_to_db(self, row, triage_res):
        """简单落库逻辑"""
        target_table = "dwd_policy_analysis"
        
        # E6-S1: 保证获取并落库 simhash
        core_segment_simhash = triage_res.get("core_segment_simhash")
        if not core_segment_simhash:
            from shared.utils.segment_extractor import extract_key_segment
            segment_used = extract_key_segment(row['title'], row['content_text'], row.get('policy_type', 'other'))
            core_segment_simhash = compute_simhash(segment_used)
            triage_res["core_segment_simhash"] = core_segment_simhash

        sql = f"""
        INSERT INTO {target_table} (
            policy_id, analysis_path, analysis_stage, summary, importance_level, importance_reason,
            intensity_change, core_segment_simhash, updated_at
        ) VALUES (
            %s, 'llm', 'triage_only', %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
        ) ON DUPLICATE KEY UPDATE 
            analysis_path = VALUES(analysis_path),
            analysis_stage = VALUES(analysis_stage),
            summary = VALUES(summary),
            importance_level = VALUES(importance_level),
            importance_reason = VALUES(importance_reason),
            intensity_change = VALUES(intensity_change),
            core_segment_simhash = VALUES(core_segment_simhash),
            updated_at = CURRENT_TIMESTAMP
        """
        params = (
            row['id'], 
            triage_res.get('triage_summary', triage_res.get('summary', '')),
            triage_res.get('importance_level', 3),
            '【初筛】' + triage_res.get('importance_reason', ''),
            triage_res.get('intensity_change', 'neutral'),
            core_segment_simhash
        )
        try:
            from shared.db.connection import execute_query
            await execute_query(sql, params)
        except Exception as e:
            logger.error(f"DB Write failed: {e}")

    async def _write_rule_result_to_db(self, row: Dict[str, Any], extractor_name: str, extractor: Any, extracted_data: Dict[str, Any], target_table: str) -> Dict[str, Any]:
        """
        零费用规则分析结果写入物理目标表 (主表或影子表)
        """
        policy_id = row['id']
        title = row['title']
        content_text = row['content_text']
        
        # 依靠具体提取器的 generate_summary 生成对齐 DWD 契约的标准五元组
        summary_list, importance_level, sectors_positive, sectors_negative, intensity_change = extractor.generate_summary(extracted_data)
        
        summary_str = " ".join(summary_list)
        importance_reason = f"【规则判定】该政策经由内置 {extractor_name} 零成本规则器精确解析，自动对齐宏观货政知识库。"
        
        # 板块并集扁平化
        merged_sectors = sectors_positive + sectors_negative
        
        model_name = f"rule-based-{extractor_name}-v{extractor.VERSION}"
        
        # E6-S1: 计算核心段落的 simhash
        from shared.utils.segment_extractor import extract_key_segment
        policy_type = row.get("policy_type", "macro_policy")
        segment_used_extracted = extract_key_segment(title, content_text, policy_type)
        core_segment_simhash = compute_simhash(segment_used_extracted)
        
        sql = f"""
        INSERT INTO {target_table} (
            policy_id, analysis_path, analysis_stage, summary, importance_level, importance_reason, 
            sectors_positive, sectors_negative, intensity_change, key_differences, 
            implication, contrast_baseline_id, segment_used, segment_extracted, 
            input_truncated, prompt_name, prompt_version, model_name, 
            thinking_enabled, reasoning_effort, input_cache_hit_tokens, 
            input_cache_miss_tokens, output_tokens, reasoning_tokens, cost_cny,
            core_segment_simhash
        ) VALUES (
            %s, 'rule', 'triage_and_deep', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
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
            segment_used = VALUES(segment_used),
            segment_extracted = VALUES(segment_extracted),
            input_truncated = VALUES(input_truncated),
            model_name = VALUES(model_name),
            input_cache_hit_tokens = VALUES(input_cache_hit_tokens),
            input_cache_miss_tokens = VALUES(input_cache_miss_tokens),
            output_tokens = VALUES(output_tokens),
            reasoning_tokens = VALUES(reasoning_tokens),
            cost_cny = VALUES(cost_cny),
            core_segment_simhash = VALUES(core_segment_simhash),
            updated_at = CURRENT_TIMESTAMP
        """
        
        params = (
            policy_id, summary_str, importance_level, importance_reason,
            json.dumps(sectors_positive, ensure_ascii=False), json.dumps(sectors_negative, ensure_ascii=False),
            intensity_change, "[]", "零成本规则路径直切，无二次措辞比对提示。", None,
            content_text[:3000], 1, 0, "RULE_DIRECT_BYPASS", f"v{extractor.VERSION}",
            model_name, 0, None, 0, 0, 0, 0, 0.000000, core_segment_simhash
        )
        
        await execute_query(sql, params, is_select=False)
        
        # 如果是写入主表，还需要同步刷新扁平化板块表 dwd_policy_sector_impact，并更新 ods 表的状态
        if target_table == "dwd_policy_analysis":
            # 1. 捞取写入的 ID
            sql_get_id = f"SELECT id FROM dwd_policy_analysis WHERE policy_id = %s AND model_name = %s"
            rows_id = await execute_query(sql_get_id, (policy_id, model_name), is_select=True)
            analysis_id = rows_id[0]['id']
            
            # 2. 刷新扁平化映射
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
            
            # 3. 更新 ods 状态
            await execute_query(
                "UPDATE ods_policy_info SET analysis_status = 'analyzed' WHERE id = %s",
                (policy_id,),
                is_select=False
            )
            
        return {
            "policy_id": policy_id,
            "analysis_id": None if target_table != "dwd_policy_analysis" else analysis_id,
            "policy_type": "macro_policy",
            "summary": summary_str,
            "importance_level": importance_level,
            "intensity_change": intensity_change,
            "cost_cny": 0.0,
            "routing_path": f"rule-direct-{target_table}"
        }

    async def _run_rule_then_llm_hybrid(self, row: Dict[str, Any], extracted_data: Dict[str, Any], extractor: Any) -> Dict[str, Any]:
        """
        RRR 准备金率 5星级政策 -> 规则锚定基础数据 + 大模型宏观深度解读 (rule_then_llm 专家链路)
        """
        policy_id = row['id']
        title = row['title']
        content_text = row['content_text']
        
        # 1. 整理专家辅助数据
        action = extracted_data["action"]
        change_points = extracted_data["change_points"]
        eff_date = extracted_data["effective_date"]
        
        # 2. 注入大模型分析前置上下文
        # 临时将 PolicyAnalyzer 拦截拼接：我们通过手动触发 analyze_policy
        # 但我们用 monkeypatch 的思路，或者直接暂时修改其 user_prompt！
        # 最稳妥、优雅的金融级解法：暂时包装成一个特制 row，在 title 中附带校正信息，以便 policy_analyzer 组装
        hybrid_title = f"{title}（专家前置校准数据：方向={action}，幅度={change_points}个百分点，生效期={eff_date}）"
        
        # 3. 复制一个 row 进行欺骗式注入，让 policy_analyzer 在单期 summary 中无痕捕获！
        hybrid_row = row.copy()
        hybrid_row["title"] = hybrid_title
        
        logger.info(f"Injecting expert-hybrid data into user title: '{hybrid_title}'")
        
        # 4. 派发给标准 PolicyAnalyzer
        res = await self.analyzer.analyze_policy(
            hybrid_row,
            analysis_path='rule_then_llm',
            analysis_stage='triage_and_deep'
        )
        res["routing_path"] = "rule_then_llm_hybrid"
        
        # 5. 可选：在最终落库记录中，将 model_name 改写为 hybrid 标打，以便于后续审计
        sql_update_model = """
            UPDATE dwd_policy_analysis 
            SET model_name = CONCAT('hybrid-', model_name)
            WHERE id = %s
        """
        await execute_query(sql_update_model, (res["analysis_id"],), is_select=False)
        
        return res
