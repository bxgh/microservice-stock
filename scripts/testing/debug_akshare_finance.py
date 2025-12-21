#!/usr/bin/env python3
"""调试 AkShare 财务摘要接口"""
import akshare as ak

print("测试 AkShare 财务摘要接口...")
print("=" * 60)

# 测试贵州茅台
symbol = "600519"
print(f"\n股票代码: {symbol}")

try:
    df = ak.stock_financial_abstract_ths(symbol=symbol)
    
    if df is None or df.empty:
        print("返回数据为空")
    else:
        print(f"\n返回数据形状: {df.shape}")
        print(f"\n列名: {df.columns.tolist()}")
        print(f"\n前3行数据:")
        print(df.head(3))
        
        print(f"\n第一行数据详情:")
        if len(df) > 0:
            latest = df.iloc[0]
            for col in df.columns:
                print(f"  {col}: {latest[col]}")
                
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
