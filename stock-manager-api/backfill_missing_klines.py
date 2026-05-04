import asyncio
import csv
import os
import sys
from datetime import datetime

# 确保可以导入 app 模块
sys.path.append(os.getcwd())

from app.services.market_data_service import MarketDataService
from app.utils.database import db

async def backfill_missing():
    print("🚀 开始补全断档数据...")
    
    # 读取审计报告
    report_path = "/app/audit_reports/report_B_missing_dates.csv"
    if not os.path.exists(report_path):
        print(f"❌ 找不到报告文件: {report_path}")
        return

    missing_items = []
    with open(report_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            missing_items.append(row)

    if not missing_items:
        print("✅ 没有需要补全的断档数据。")
        return

    print(f"统计: 共有 {len(missing_items)} 条缺失记录需要补全。")
    
    service = MarketDataService()
    await db.connect()
    
    success_count = 0
    fail_count = 0
    
    # 为了效率，我们可以按股票分组，尽量一次同步一段日期
    # 但由于缺失可能是不连续的，按 (ts_code, date) 逐条补全最稳妥
    # 或者先按 ts_code 分组，找到每个 code 的日期范围
    stocks_gaps = {}
    for item in missing_items:
        code = item['ts_code']
        m_date = item['missing_date']
        if code not in stocks_gaps:
            stocks_gaps[code] = []
        stocks_gaps[code].append(m_date)
    
    for code, dates in stocks_gaps.items():
        print(f"正在补全股票 {code} 的 {len(dates)} 天数据...")
        for m_date in sorted(dates):
            try:
                # 调用同步接口 (由于是补全，我们指定具体的 trade_date)
                # sync_stock_daily 会处理 Tushare 和 BaoStock 的降级
                res = await service.sync_stock_daily(ts_code=code, trade_date=m_date)
                if res != 0:
                    success_count += 1
                else:
                    print(f"  ⚠️ {code} 在 {m_date} 未获取到数据")
                    fail_count += 1
            except Exception as e:
                print(f"  ❌ {code} 在 {m_date} 同步失败: {e}")
                fail_count += 1
            
            # 避免请求过快
            await asyncio.sleep(0.5)

    await db.disconnect()
    print(f"\n✅ 补全完成！成功: {success_count}, 失败: {fail_count}")

if __name__ == "__main__":
    asyncio.run(backfill_missing())
