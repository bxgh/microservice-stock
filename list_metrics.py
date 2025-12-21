#!/usr/bin/env python3
"""查看所有可用的财务指标字段"""
import akshare as ak

symbol = "600519"
df = ak.stock_financial_abstract_ths(symbol=symbol)

print("所有可用的 metric_name:")
print("=" * 60)
unique_metrics = df['metric_name'].unique()
for i, metric in enumerate(sorted(unique_metrics), 1):
    print(f"{i:3d}. {metric}")
    
print(f"\n共 {len(unique_metrics)} 个指标")
