import akshare as ak

# Fetch BJ stocks
print("--- BJ Stocks ---")
try:
    bj_stocks = ak.stock_beijing_report_em()
    print(f"BJ count: {len(bj_stocks)}")
except Exception as e:
    print(f"BJ failed: {e}")

# Fetch ETFs
print("\n--- ETFs ---")
try:
    etf_list = ak.fund_etf_category_sina(symbol="ETF基金")
    print(f"ETF count: {len(etf_list)}")
except Exception as e:
    print(f"ETF failed: {e}")

# Fetch Index
print("\n--- Indices ---")
try:
    index_list = ak.stock_zh_index_spot_em()
    print(f"Index count: {len(index_list)}")
except Exception as e:
    print(f"Index failed: {e}")
