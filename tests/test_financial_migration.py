import sys
import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# 确保加载 scf-collector/shared 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scf-collector')))

from shared.collectors.tushare_cl import TushareCollector
from shared.db.dao import StockDAO
from scripts.tushare_financial_backfill import deduplicate_records

@pytest.mark.asyncio
async def test_tushare_collector_financial_fetch():
    """
    [E13-S4-T4] 验证 TushareCollector 财务数据拉取方法的封装与异步执行
    """
    collector = TushareCollector()
    collector.pro = MagicMock()
    
    import pandas as pd
    mock_df = pd.DataFrame([{"ts_code": "600519.SH", "end_date": "20260331", "ann_date": "20260415", "report_type": "1"}])
    
    collector.pro.balancesheet = MagicMock(return_value=mock_df)
    collector.pro.income = MagicMock(return_value=mock_df)
    collector.pro.cashflow = MagicMock(return_value=mock_df)
    collector.pro.fina_indicator = MagicMock(return_value=mock_df)
    
    res_bs = await collector.fetch_balancesheet("600519.SH")
    res_inc = await collector.fetch_income("600519.SH")
    res_cf = await collector.fetch_cashflow("600519.SH")
    res_ind = await collector.fetch_fina_indicator("600519.SH")
    
    assert len(res_bs) == 1
    assert res_bs[0]["ts_code"] == "600519.SH"
    assert len(res_inc) == 1
    assert len(res_cf) == 1
    assert len(res_ind) == 1

@pytest.mark.asyncio
async def test_stock_dao_financial_save():
    """
    [E13-S4-T4] 验证 StockDAO 的别名对齐、日期转换与百分比小数标准化（除以100.0）
    """
    bs_raw = [{
        "ts_code": "600519.SH",
        "ann_date": "20260415",
        "f_ann_date": "20260415",
        "end_date": "20260331",
        "report_type": "1",
        "total_assets": 1000000.0,
        "total_liab": 400000.0,
        "st_borr": 10000.0,
        "lt_borr": 50000.0
    }]
    
    ind_raw = [{
        "ts_code": "600519.SH",
        "ann_date": "20260415",
        "end_date": "20260331",
        "roe": 15.5,                 # 百分比形式，入库应除以 100.0
        "grossprofit_margin": 91.2,  # 百分比形式，入库应除以 100.0
        "current_ratio": 1.8         # 倍数形式，入库保持原值
    }]

    with patch('shared.db.dao.execute_query', AsyncMock(return_value=1)) as mock_exec:
        # 1. 测试资产负债表保存
        bs_count = await StockDAO.save_balancesheet(bs_raw)
        assert bs_count == 1
        
        # 验证 SQL 调用与字段对齐
        call_args = mock_exec.call_args_list[0][0]
        params = call_args[1]
        assert params["total_liabilities"] == 400000.0
        assert params["short_term_borrow"] == 10000.0
        assert params["long_term_borrow"] == 50000.0
        assert params["ann_date"] == "2026-04-15"
        assert params["end_date"] == "2026-03-31"

    with patch('shared.db.dao.execute_query', AsyncMock(return_value=1)) as mock_exec:
        # 2. 测试财务指标百分比换算保存
        ind_count = await StockDAO.save_fina_indicator(ind_raw)
        assert ind_count == 1
        
        call_args = mock_exec.call_args_list[0][0]
        params = call_args[1]
        assert params["roe"] == 0.155             # 验证 ROE 已除以 100
        assert params["grossprofit_margin"] == 0.912 # 验证毛利率已除以 100
        assert params["current_ratio"] == 1.8       # 验证流动比率保持原样
        assert params["ann_date"] == "2026-04-15"

def test_deduplicate_records_business_logic():
    """
    [E13-S4-T4] 验证 Python 业务层对上市公司重复/更正公告的预排重清洗逻辑
    """
    raw_data = [
        # 同一报告期，较早公告
        {"end_date": "20260331", "ann_date": "20260415", "f_ann_date": "20260415", "report_type": "1", "val": 10},
        # 同一报告期，较晚更正公告 (应该保留这条)
        {"end_date": "20260331", "ann_date": "20260420", "f_ann_date": "20260420", "report_type": "1", "val": 20},
        # 另一报告期记录
        {"end_date": "20251231", "ann_date": "20260310", "f_ann_date": "20260310", "report_type": "1", "val": 30}
    ]
    
    clean_data = deduplicate_records(raw_data, has_report_type=True)
    
    # 期望保留 2 条记录（20260331 的更正版 + 20251231 的普通版）
    assert len(clean_data) == 2
    
    # 校验更正版 val 应该是 20
    matched_331 = [item for item in clean_data if item["end_date"] == "20260331"]
    assert len(matched_331) == 1
    assert matched_331[0]["val"] == 20
