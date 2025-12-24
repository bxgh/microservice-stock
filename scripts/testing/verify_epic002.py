import requests
import json
import pandas as pd

BASE_AK = "http://localhost:8003/api/v1"
BASE_BS = "http://localhost:8001/api/v1"

def test_akshare_finance_indicators(code="600519"):
    print(f"--- Testing AkShare Finance Indicators for {code} ---")
    url = f"{BASE_AK}/finance/indicators/{code}"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        # 核心字段校验
        p0_fields = [
            'total_assets', 'total_liabilities', 'monetary_funds', 
            'net_profit', 'operating_income', 'ebitda', 'fcf'
        ]
        
        print(f"Report Date: {data.get('report_date')}")
        for field in p0_fields:
            val = data.get(field)
            status = "✅" if val is not None else "❌"
            print(f"{field:20}: {val:>15} {status}")
            
        assert data.get('ebitda') is not None, "EBITDA should not be None"
        assert data.get('fcf') is not None, "FCF should not be None"
        print("AkShare EPIC-002 Test: PASS\n")
    except Exception as e:
        print(f"AkShare EPIC-002 Test: FAIL - {e}\n")

def test_baostock_valuation_statistics(code="sh.600519"):
    print(f"--- Testing BaoStock Valuation Statistics for {code} ---")
    url = f"{BASE_BS}/valuation/{code}/history?start_date=2023-01-01"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        stats = data.get("statistics", {})
        pe_stats = stats.get("pe", {})
        
        print(f"History Count: {len(data.get('history', []))}")
        print("PE Statistics:")
        for k, v in pe_stats.items():
            print(f"  {k:10}: {v}")
            
        assert pe_stats.get("mean") is not None, "Mean PE should not be None"
        assert pe_stats.get("p90") is not None, "P90 PE should not be None"
        assert pe_stats.get("percentile") is not None, "Current percentile should not be None"
        print("BaoStock EPIC-002 Test: PASS\n")
    except Exception as e:
        print(f"BaoStock EPIC-002 Test: FAIL - {e}\n")

if __name__ == "__main__":
    test_akshare_finance_indicators("600519")
    test_baostock_valuation_statistics("sh.600519")
