
import akshare as ak
import pandas as pd
import json

def get_cols():
    symbol = "SH600519"
    print(f"Fetch BS for {symbol}")
    df_bs = ak.stock_balance_sheet_by_report_em(symbol=symbol)
    print(f"BS Columns: {df_bs.columns.tolist()}")
    
    print(f"Fetch IS for {symbol}")
    df_is = ak.stock_profit_sheet_by_report_em(symbol=symbol)
    print(f"IS Columns: {df_is.columns.tolist()}")
    
    print(f"Fetch CF for {symbol}")
    df_cf = ak.stock_cash_flow_sheet_by_report_em(symbol=symbol)
    print(f"CF Columns: {df_cf.columns.tolist()}")

if __name__ == "__main__":
    get_cols()
