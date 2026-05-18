# -*- coding: utf-8 -*-
import pytest
from unittest.mock import patch, MagicMock
from shared.utils.staged_analyzer import StagedAnalyzer

try:
    from unittest.mock import AsyncMock
except ImportError:
    class AsyncMock(MagicMock):
        async def __call__(self, *args, **kwargs):
            return super(AsyncMock, self).__call__(*args, **kwargs)

@pytest.fixture
def staged_analyzer():
    return StagedAnalyzer()

@pytest.mark.asyncio
@patch("shared.utils.staged_analyzer.execute_query", new_callable=AsyncMock)
async def test_find_similar_previous_policy_high(mock_db, staged_analyzer):
    """
    测试查找高度相似历史政策 (汉明距离 <= 3) (Unicode 安全版)
    """
    # 模拟数据库返回一条汉明距离非常近的历史记录
    # 假定当前 simhash 为 ffffffffffffffff (全1)
    # 历史记录哈希为 fffffffffffffffe (只差 1 位)
    # title = "2026年4月贷款市场报价利率（LPR）公告"
    title_val = "2026\u5e744\u6708\u5bf1\u6b3e\u5e02\u573a\u62a5\u4ef7\u5229\u7387\uff08LPR\uff09\u516c\u544a"
    mock_db.return_value = [
        {
            "id": 501,
            "policy_id": 1001,
            "core_segment_simhash": "fffffffffffffffe",
            "title": title_val,
            "publish_date": "2026-04-20 09:15:00"
        }
    ]
    
    similar_info = await staged_analyzer.find_similar_previous_policy(
        current_policy_id=1002,
        current_ts_code="000001.SZ",
        current_policy_type="macro_policy",
        current_publish_date="2026-05-20 09:15:00",
        current_simhash="ffffffffffffffff"
    )
    
    assert similar_info is not None
    assert similar_info["hamming_distance"] == 1
    assert similar_info["similarity_rating"] == "high"
    assert similar_info["matched_policy_id"] == 1001
    assert similar_info["matched_analysis_id"] == 501

@pytest.mark.asyncio
@patch("shared.utils.staged_analyzer.execute_query", new_callable=AsyncMock)
async def test_find_similar_previous_policy_moderate(mock_db, staged_analyzer):
    """
    测试查找中度相似历史政策 (4 <= 汉明距离 <= 8) (Unicode 安全版)
    """
    # 当前 simhash 为 ffffffffffffffff (全1)
    # 历史记录哈希为 ffffffffffffff00 (十六进制末位两个0，相当于差 8 位)
    # title = "2026年3月贷款市场报价利率（LPR）公告"
    title_val = "2026\u5e743\u6708\u5bf1\u6b3e\u5e02\u573a\u62a5\u4ef7\u5229\u7387\uff08LPR\uff09\u516c\u544a"
    mock_db.return_value = [
        {
            "id": 502,
            "policy_id": 1003,
            "core_segment_simhash": "ffffffffffffff00",
            "title": title_val,
            "publish_date": "2026-03-20 09:15:00"
        }
    ]
    
    similar_info = await staged_analyzer.find_similar_previous_policy(
        current_policy_id=1004,
        current_ts_code="000001.SZ",
        current_policy_type="macro_policy",
        current_publish_date="2026-05-20 09:15:00",
        current_simhash="ffffffffffffffff"
    )
    
    assert similar_info is not None
    assert similar_info["hamming_distance"] == 8
    assert similar_info["similarity_rating"] == "moderate"

@pytest.mark.asyncio
@patch("shared.utils.staged_analyzer.execute_query", new_callable=AsyncMock)
async def test_find_similar_previous_policy_none(mock_db, staged_analyzer):
    """
    测试无相似历史记录时返回 None
    """
    mock_db.return_value = []
    
    similar_info = await staged_analyzer.find_similar_previous_policy(
        current_policy_id=1005,
        current_ts_code="000001.SZ",
        current_policy_type="macro_policy",
        current_publish_date="2026-05-20 09:15:00",
        current_simhash="ffffffffffffffff"
    )
    
    assert similar_info is None

@pytest.mark.asyncio
@patch("shared.utils.staged_analyzer.execute_query", new_callable=AsyncMock)
@patch("shared.utils.policy_analyzer.execute_query", new_callable=AsyncMock)
@patch("shared.utils.llm_client.LLMClient.chat", new_callable=AsyncMock)
async def test_analyze_policy_similarity_injection(mock_chat, mock_policy_db, mock_staged_db, staged_analyzer):
    """
    测试相似度判定字典完美注入 analyze_policy 返回值 (Unicode 安全版)
    """
    def mock_db_side_effect(sql, params=None, is_select=False):
        if is_select:
            if "SELECT id FROM dwd_policy_analysis" in sql:
                return [{"id": 888}]
        return []

    mock_staged_db.side_effect = mock_db_side_effect
    mock_policy_db.side_effect = mock_db_side_effect

    # 模拟初筛 LLM 调用
    triage_sum = "\u666e\u901a\u5e8f\u89c2\u901a\u77e5\u3002"
    three_sens = "\u666e\u901a\u5e8f\u89c2\u901a\u77e5\u4e00\u53e5\u8bdd\u3002\u4e8c\u53e5\u8bdd\u3002\u4e09\u53e5\u8bdd\u3002"
    
    mock_chat.return_value = {
        "content": f'{{"importance_level": 2, "policy_type": "macro_policy", "requires_deep_analysis": false, "triage_confidence": 0.95, "triage_summary": "{triage_sum}", "summary_three_sentences": "{three_sens}", "core_segment_simhash": "ffffffffffffffff"}}',
        "model_name": "deepseek-chat-flash",
        "input_cache_hit_tokens": 100,
        "input_cache_miss_tokens": 0,
        "output_tokens": 30,
        "reasoning_tokens": 0,
        "cost_cny": 0.0001,
        "duration_ms": 150
    }

    # title = "国家发改委印发促进数字经济发展新规通知"
    title_cur = "\u56fd\u5bb6\u53d1\u6539\u59d4\u5370\u53d1\u4fc3\u8fdb\u6570\u5b57\u7ecf\u6d4e\u53d1\u5c55\u65b0\u89c4\u901a\u77e5"
    # content_text = "国家发改委决定进一步加强数字基础设施建设，支持数据中心与5G软硬件设施建设。"
    content_cur = "\u56fd\u5bb6\u53d1\u6539\u59d4\u51b3\u5b9a\u8fdb\u4e00\u6b65\u52a0\u5f3a\u6570\u5b57\u57fa\u784d\u8bbe\u65bd\u5efa\u8bbe\uff0c\u652f\u6301\u6570\u636e\u4e2d\u5fc3\u4e0e5G\u8f6f\u786c\u4ef6\u8bbe\u65bd\u5efa\u8bbe\u3002"

    test_row = {
        "id": 1002,
        "title": title_cur,
        "content_text": content_cur,
        "ts_code": "000001.SZ",
        "publish_date": "2026-05-20 09:15:00",
        "policy_type": "macro_policy"
    }

    # 直接 mock StagedAnalyzer 内部的 find_similar_previous_policy 方法，使其稳定返回高相似度判定！
    with patch.object(staged_analyzer, "find_similar_previous_policy", new_callable=AsyncMock) as mock_find:
        mock_find.return_value = {
            "matched_policy_id": 1001,
            "matched_analysis_id": 501,
            "matched_title": "2026\u5e744\u6708\u5bf1\u6b3e\u5e02\u573a\u62a5\u4ef7\u5229\u7387\uff08LPR\uff09\u516c\u544a",
            "matched_publish_date": "2026-04-20 09:15:00",
            "hamming_distance": 1,
            "similarity_rating": "high"
        }

        res = await staged_analyzer.analyze_policy(test_row)

    # 验证是否成功走 triage_only 且包含相似度判定信息
    assert res["importance_level"] == 2
    assert res["routing_path"] == "triage_only"
    assert "similarity_detection" in res
    
    similar_info = res["similarity_detection"]
    assert similar_info["hamming_distance"] == 1
    assert similar_info["similarity_rating"] == "high"
    assert similar_info["matched_policy_id"] == 1001
