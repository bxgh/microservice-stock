# -*- coding: utf-8 -*-
import pytest
import os
import sys
import json

# 模拟导入系统路径以获取 shared
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from unittest.mock import patch, MagicMock
try:
    from unittest.mock import AsyncMock
except ImportError:
    class AsyncMock(MagicMock):
        async def __call__(self, *args, **kwargs):
            return super(AsyncMock, self).__call__(*args, **kwargs)

from shared.utils.staged_analyzer import StagedAnalyzer


def load_golden_policies():
    json_path = os.path.join(current_dir, "data", "golden_policies.json")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.asyncio
@patch("shared.utils.staged_analyzer.execute_query", new_callable=AsyncMock)
@patch("shared.utils.policy_analyzer.execute_query", new_callable=AsyncMock)
@patch("shared.utils.llm_client.LLMClient.chat", new_callable=AsyncMock)
async def test_golden_regression_flow(mock_chat, mock_policy_db, mock_staged_db):
    """
    E15-E2-T7: 金标准回归测试工具 (Gold Standard Regression Tool)
    加载 tests/data/golden_policies.json 的标准政策数据集，验证初筛漏报率为 0% 的高召回率要求。
    """
    golden_list = load_golden_policies()
    assert len(golden_list) > 0, "Golden policy dataset is empty!"

    # 模拟 DB 对照表及主表写回
    def mock_db_side_effect(sql, params=None, is_select=False):
        if is_select:
            if "SELECT id FROM dwd_policy_analysis" in sql:
                return [{"id": 888}]
            if "publish_date <" in sql:
                return []
        return []

    mock_staged_db.side_effect = mock_db_side_effect
    mock_policy_db.side_effect = mock_db_side_effect

    def chat_side_effect(system_prompt, user_prompt, mode, temperature=0.1, reasoning_effort=None, prompt_name="DEFAULT_PROMPT", prompt_version="1.0", is_heartbeat=False):
        if "Please classify this policy" in user_prompt:
            if "存款准备金" in user_prompt or "降准" in user_prompt:
                return {
                    "content": "rrr_announcement",
                    "model_name": "deepseek-chat-flash",
                    "input_cache_hit_tokens": 100,
                    "input_cache_miss_tokens": 20,
                    "output_tokens": 30,
                    "reasoning_tokens": 0,
                    "cost_cny": 0.0001,
                    "duration_ms": 200
                }
            return {
                "content": "other",
                "model_name": "deepseek-chat-flash",
                "input_cache_hit_tokens": 100,
                "input_cache_miss_tokens": 20,
                "output_tokens": 30,
                "reasoning_tokens": 0,
                "cost_cny": 0.0001,
                "duration_ms": 200
            }

        if "统一大市场" in user_prompt:
            if mode == "flash":
                return {
                    "content": '{"importance_level": 5, "policy_type": "executive_meeting", "requires_deep_analysis": true, "triage_confidence": 0.99, "triage_summary": "建设全国统一大市场。"}',
                    "model_name": "deepseek-chat-flash",
                    "input_cache_hit_tokens": 100,
                    "input_cache_miss_tokens": 20,
                    "output_tokens": 30,
                    "reasoning_tokens": 0,
                    "cost_cny": 0.0001,
                    "duration_ms": 200
                }
            else:
                return {
                    "content": '{"summary_three_sentences": "加快建设全国统一大市场；打破地方保护壁垒；利好商贸物流大基建板块。", "importance_level": 5, "importance_reason": "重大体制改革", "sectors": [{"sector_name": "物流", "sector_code_sw": "801191", "impact_direction": "positive", "rationale": "大市场畅通物流效率"}]}',
                    "model_name": "deepseek-chat",
                    "input_cache_hit_tokens": 200,
                    "input_cache_miss_tokens": 50,
                    "output_tokens": 100,
                    "reasoning_tokens": 0,
                    "cost_cny": 0.0003,
                    "duration_ms": 300
                }

        if "退市" in user_prompt:
            if mode == "flash":
                return {
                    "content": '{"importance_level": 3, "policy_type": "regulation_release", "requires_deep_analysis": false, "triage_confidence": 0.65, "triage_summary": "加强退市监管工作。"}',
                    "model_name": "deepseek-chat-flash",
                    "input_cache_hit_tokens": 100,
                    "input_cache_miss_tokens": 20,
                    "output_tokens": 30,
                    "reasoning_tokens": 0,
                    "cost_cny": 0.0001,
                    "duration_ms": 200
                }
            else:
                return {
                    "content": '{"summary_three_sentences": "证监会发布退市意见；防范系统性金融风险；淘汰劣质绩差股票。", "importance_level": 4, "importance_reason": "退市标准大幅收紧", "sectors": []}',
                    "model_name": "deepseek-chat",
                    "input_cache_hit_tokens": 200,
                    "input_cache_miss_tokens": 50,
                    "output_tokens": 100,
                    "reasoning_tokens": 0,
                    "cost_cny": 0.0003,
                    "duration_ms": 300
                }

        if "非税收入日常核查" in user_prompt:
            return {
                "content": '{"importance_level": 2, "policy_type": "other", "requires_deep_analysis": false, "triage_confidence": 0.95, "triage_summary": "日常非税核查通报。"}',
                "model_name": "deepseek-chat-flash",
                "input_cache_hit_tokens": 100,
                "input_cache_miss_tokens": 20,
                "output_tokens": 30,
                "reasoning_tokens": 0,
                "cost_cny": 0.0001,
                "duration_ms": 200
            }

        if "存款准备金" in user_prompt or "下调金融机构存款准备金率" in user_prompt:
            return {
                "content": '{"summary_three_sentences": "央行下调存款准备金率；支持实体经济发展；利好银行地产板块。", "importance_level": 4, "importance_reason": "降准释放长期资金", "sectors": [{"sector_name": "银行", "sector_code_sw": "801780", "impact_direction": "positive", "rationale": "降准降低银行负债成本"}]}',
                "model_name": "deepseek-chat",
                "input_cache_hit_tokens": 200,
                "input_cache_miss_tokens": 50,
                "output_tokens": 100,
                "reasoning_tokens": 0,
                "cost_cny": 0.0003,
                "duration_ms": 300
            }

        raise ValueError(f"Unexpected prompt in chat side effect: {user_prompt}")

    mock_chat.side_effect = chat_side_effect

    analyzer = StagedAnalyzer()

    false_negatives = []
    processed_count = 0

    for policy in golden_list:
        p_id = policy["id"]
        title = policy["title"]
        expected_stage = policy["expected_stage"]

        print(f"\\nProcessing Golden Policy ID {p_id}: '{title}'...")
        res = await analyzer.analyze_policy(policy)
        processed_count += 1

        routing = res.get("routing_path", "triage_only")

        if expected_stage == "rule_based_holiday":
            assert routing == "rule-direct-dwd_policy_analysis", "Holiday notice should bypass directly"
            assert res.get("intensity_change") == "neutral"
            assert "放假" in title
            print("-> Successfully blocked by HolidayExtractor!")

        elif expected_stage == "rule_based_rrr":
            assert routing in ["rule_then_llm", "rule_then_llm_hybrid", "triage_only", "triage_and_deep"]
            print("-> Successfully routed via RRRExtractor hybrid path!")

        elif expected_stage == "deep_or_voting":
            if routing == "triage_only":
                leak_reason = "Leakage! Policy expected to undergo deep analysis but was classified as triage_only!"
                print(f"[LEAKAGE DETECTED] ID {p_id}: {leak_reason}")
                false_negatives.append({
                    "id": p_id,
                    "title": title,
                    "reason": leak_reason
                })
            else:
                assert routing in ["triage_and_deep", "triage_and_voting"]
                print(f"-> Successfully upgraded to {routing}! (No Leakage)")

        elif expected_stage == "triage_only":
            assert routing == "triage_only", "Low importance policy should remain triage_only"
            print("-> Successfully filtered out to triage_only! (Token Saved)")

    leak_rate = len(false_negatives) / len([p for p in golden_list if p["expected_stage"] == "deep_or_voting"])
    print("\\n================ REGRESSION SUMMARY ================")
    print(f"Total processed golden policies: {processed_count}")
    print(f"False Negatives (Leakage): {len(false_negatives)}")
    print(f"Final Golden Leakage Rate (False Negative Rate): {leak_rate * 100:.2f}%")
    print("====================================================")

    assert leak_rate == 0.0, f"Gold standard failed! Leakage rate is {leak_rate*100:.2f}%"
