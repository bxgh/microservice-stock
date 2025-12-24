import asyncio
import akshare as ak
from datetime import datetime
from app.services.akshare_service import AkShareService

async def debug_lhb():
    service = AkShareService()
    print("--- Debugging LHB Date Selection ---")
    
    # 模拟内部日期获取逻辑
    trade_date_df = ak.tool_trade_date_hist_sina()
    trade_dates = trade_date_df['trade_date'].tolist()
    today = datetime.now().date()
    # 逻辑：找过去的或者今天的最后一个交易日
    past_trade_dates = [d for d in trade_dates if d <= today]
    
    if past_trade_dates:
        latest_date = past_trade_dates[-1].strftime("%Y%m%d")
        print(f"Latest trade date found: {latest_date}")
        
        print(f"Calling ak.stock_lhb_detail_em(start_date='{latest_date}', end_date='{latest_date}')...")
        df = ak.stock_lhb_detail_em(start_date=latest_date, end_date=latest_date)
        if df is not None:
            print(f"DataFrame shape: {df.shape}")
            if df.empty:
                print("DataFrame is EMPTY. This is likely because today's LHB is not yet out (usually 16:30+).")
                
                # 尝试前一交易日
                if len(past_trade_dates) > 1:
                    prev_date = past_trade_dates[-2].strftime("%Y%m%d")
                    print(f"Trying previous trade date: {prev_date}...")
                    df_prev = ak.stock_lhb_detail_em(start_date=prev_date, end_date=prev_date)
                    print(f"Prev DataFrame shape: {df_prev.shape}")
            else:
                print(df.head())
        else:
            print("DataFrame is None")

if __name__ == "__main__":
    # 需要 PYTHONPATH 包含当前目录
    import os
    import sys
    sys.path.append("/home/ubuntu/microservice-stock/akshare-api")
    asyncio.run(debug_lhb())
