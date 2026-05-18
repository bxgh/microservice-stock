# -*- coding: utf-8 -*-
import pytest
from unittest.mock import patch, MagicMock

try:
    from unittest.mock import AsyncMock
except ImportError:
    class AsyncMock(MagicMock):
        async def __call__(self, *args, **kwargs):
            return super(AsyncMock, self).__call__(*args, **kwargs)

from shared.utils.staged_analyzer import StagedAnalyzer


@pytest.fixture
def staged_analyzer():
    return StagedAnalyzer()


@pytest.mark.asyncio
@patch("shared.utils.staged_analyzer.execute_query", new_callable=AsyncMock)
@patch("shared.utils.policy_analyzer.execute_query", new_callable=AsyncMock)
@patch("shared.utils.llm_client.LLMClient.chat", new_callable=AsyncMock)
async def test_triage_only_path(mock_chat, mock_policy_db, mock_staged_db, staged_analyzer):
    """测试初筛直接阻断路径"""
    def mock_db_side_effect(sql, params=None, is_select=False):
        if is_select:
            if "SELECT id FROM dwd_policy_analysis" in sql:
                return [{"id": 888}]
            if "publish_date <" in sql:
                return []
        return []

    mock_staged_db.side_effect = mock_db_side_effect
    mock_policy_db.side_effect = mock_db_side_effect

    mock_chat.return_value = {
        "content": '{"importance_level": 2, "policy_type": "industry", "requires_deep_analysis": false, "triage_confidence": 0.95, "triage_summary": "普通行业通知。"}',
        "model_name": "deepseek-chat-flash",
        "input_cache_hit_tokens": 100,
        "input_cache_miss_tokens": 0,
        "output_tokens": 30,
        "reasoning_tokens": 0,
        "cost_cny": 0.0001,
        "duration_ms": 150
    }

    test_row = {
        "id": 101,
        "title": "关于开展2026年度春季农业生产安全检查的通知",
        "content_text": "为保障春季农业生产，各级部门应...",
        "ts_code": "000001.SZ",
        "publish_date": "2026-03-01 10:00:00"
    }

    res = await staged_analyzer.analyze_policy(test_row)

    assert res["importance_level"] == 2
    assert res["routing_path"] == "triage_only"
    assert "普通行业通知" in res["summary"]


@pytest.mark.asyncio
@patch("shared.utils.staged_analyzer.execute_query", new_callable=AsyncMock)
@patch("shared.utils.policy_analyzer.execute_query", new_callable=AsyncMock)
@patch("shared.utils.llm_client.LLMClient.chat", new_callable=AsyncMock)
async def test_triage_and_deep_path(mock_chat, mock_policy_db, mock_staged_db, staged_analyzer):
    """测试初筛升级为单期深度分析路径"""
    def mock_db_side_effect(sql, params=None, is_select=False):
        if is_select:
            if "SELECT id FROM dwd_policy_analysis" in sql:
                return [{"id": 888}]
            if "publish_date <" in sql:
                return []
        return []

    mock_staged_db.side_effect = mock_db_side_effect
    mock_policy_db.side_effect = mock_db_side_effect

    def chat_side_effect(system_prompt, user_prompt, mode, temperature=0.1):
        if mode == "flash":
            return {
                "content": '{"importance_level": 4, "policy_type": "regulation_release", "requires_deep_analysis": true, "triage_confidence": 0.90, "triage_summary": "重要规范出台。"}',
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
                "content": '{"summary_three_sentences": "测试深度分析；结构化出具；", "importance_level": 4, "importance_reason": "影响深远", "sectors": []}',
                "model_name": "deepseek-chat",
                "input_cache_hit_tokens": 200,
                "input_cache_miss_tokens": 50,
                "output_tokens": 100,
                "reasoning_tokens": 0,
                "cost_cny": 0.0003,
                "duration_ms": 300
            }

    mock_chat.side_effect = chat_side_effect

    test_row = {
        "id": 102,
        "title": "证监会关于加强资本市场法治建设的若干意见",
        "content_text": "坚决打击内幕交易...",
        "ts_code": "000001.SZ",
        "publish_date": "2026-03-01 10:00:00"
    }

    res = await staged_analyzer.analyze_policy(test_row)

    assert res["importance_level"] == 4
    assert res["routing_path"] == "triage_and_deep"
    assert "测试深度分析" in res["summary"]


@pytest.mark.asyncio
@patch("shared.utils.staged_analyzer.execute_query", new_callable=AsyncMock)
@patch("shared.utils.policy_analyzer.execute_query", new_callable=AsyncMock)
@patch("shared.utils.llm_client.LLMClient.chat", new_callable=AsyncMock)
async def test_triage_and_voting_path(mock_chat, mock_policy_db, mock_staged_db, staged_analyzer):
    """测试初筛升级为 5 星多数投票自一致性路径"""
    def mock_db_side_effect(sql, params=None, is_select=False):
        if is_select:
            if "SELECT id FROM dwd_policy_analysis" in sql:
                return [{"id": 888}]
            if "publish_date <" in sql:
                return []
        return []

    mock_staged_db.side_effect = mock_db_side_effect
    mock_policy_db.side_effect = mock_db_side_effect

    call_count = {"deep": 0}

    def chat_side_effect(system_prompt, user_prompt, mode, temperature=0.1):
        if mode == "flash":
            return {
                "content": '{"importance_level": 5, "policy_type": "executive_meeting", "requires_deep_analysis": true, "triage_confidence": 0.99, "triage_summary": "超重磅会议。"}',
                "model_name": "deepseek-chat-flash",
                "input_cache_hit_tokens": 100,
                "input_cache_miss_tokens": 20,
                "output_tokens": 30,
                "reasoning_tokens": 0,
                "cost_cny": 0.0001,
                "duration_ms": 200
            }
        else:
            call_count["deep"] += 1
            idx = call_count["deep"]
            if idx == 1:
                content = '{"summary_three_sentences": "投票分支1", "importance_level": 5, "importance_reason": "核心1", "sectors": [{"sector_name": "银行", "sector_code_sw": "801780", "impact_direction": "positive", "rationale": "r1"}], "intensity_change": "significant_increase"}'
            elif idx == 2:
                content = '{"summary_three_sentences": "投票分支2", "importance_level": 5, "importance_reason": "核心2", "sectors": [{"sector_name": "非银金融", "sector_code_sw": "801790", "impact_direction": "positive", "rationale": "r2"}], "intensity_change": "moderate_increase"}'
            else:
                content = '{"summary_three_sentences": "投票分支3", "importance_level": 5, "importance_reason": "核心3", "sectors": [{"sector_name": "银行", "sector_code_sw": "801780", "impact_direction": "positive", "rationale": "r3"}], "intensity_change": "significant_increase"}'
            
            return {
                "content": content,
                "model_name": "deepseek-reasoner",
                "input_cache_hit_tokens": 200,
                "input_cache_miss_tokens": 50,
                "output_tokens": 100,
                "reasoning_tokens": 500,
                "cost_cny": 0.001,
                "duration_ms": 1300
            }

    mock_chat.side_effect = chat_side_effect

    test_row = {
        "id": 103,
        "title": "中共中央 国务院印发重磅宏观政策",
        "content_text": "全面深化改革...",
        "ts_code": "000001.SZ",
        "publish_date": "2026-03-01 10:00:00"
    }

    res = await staged_analyzer.analyze_policy(test_row)

    assert res["importance_level"] == 5
    assert res["routing_path"] == "triage_and_voting"
    assert res["intensity_change"] == "significant_increase"
    assert call_count["deep"] == 3
