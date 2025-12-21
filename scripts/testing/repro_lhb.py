import akshare as ak
import pandas as pd
from datetime import datetime

def test_lhb(date_str=None):
    print(f"\n--- 测试龙虎榜: date={date_str} ---")
    try:
        if date_str:
            sd = date_str.replace("-", "")
            # 注意: 查阅 AkShare 文档，有的接口参数是 date, 有的是 start_date/end_date
            # 对于 stock_lhb_detail_em，参数确实是 start_date 和 end_date
            df = ak.stock_lhb_detail_em(start_date=sd, end_date=sd)
        else:
            df = ak.stock_lhb_detail_em()
            
        if df is None or df.empty:
            print("结果为空")
        else:
            print(f"获取到 {len(df)} 条数据")
            print("前5条日期:", df['上榜日'].unique() if '上榜日' in df.columns else "无日期列")
            print(df.head())
    except Exception as e:
        print(f"发生错误: {e}")

if __name__ == "__main__":
    # 1. 测试默认行为 (验证是否返回 2023 年数据)
    test_lhb()
    
    # 2. 测试指定今天或最近一个交易日 (验证 500 错误)
    # 假设今天是 2024-12-20 前后
    test_lhb("2024-12-20")
