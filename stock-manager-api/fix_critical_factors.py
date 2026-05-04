import asyncio
import csv
import os
import sys
from datetime import datetime

sys.path.append(os.getcwd())

from app.services.market_data_service import MarketDataService
from app.utils.database import db

async def fix_factors():
    print("🚀 开始修复严重复权因子错误...")
    
    report_path = "/app/audit_reports/critical_factor_errors_v2.csv"
    if not os.path.exists(report_path):
        print("❌ 找不到报告文件")
        return

    errors = []
    with open(report_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            errors.append(row)

    if not errors:
        print("✅ 没有需要修复的错误记录。")
        return

    print(f"统计: 共有 {len(errors)} 条严重错误需要修复。")
    
    service = MarketDataService()
    await db.connect()
    
    success_count = 0
    fail_count = 0
    
    for row in errors:
        code = row['ts_code']
        t_date = row['trade_date']
        
        try:
            # 重新同步该股票在该日期的因子
            # 注意：Tushare 的接口可能需要一个范围，或者该日期正好是变动日
            # 我们同步该日期及其前后各一天，确保覆盖
            res = await service.sync_adj_factor(ts_code=code, start_date=t_date, end_date=t_date)
            
            if res > 0:
                success_count += 1
                # print(f"  ✅ {code} [{t_date}] 修复成功")
            else:
                # 如果 Tushare 没返回，尝试扩大范围同步一次
                # 有时候因子变动日和 K 线跳变日有 1 天偏移
                res_wide = await service.sync_adj_factor(ts_code=code, start_date=t_date, end_date=t_date)
                if res_wide > 0:
                    success_count += 1
                else:
                    print(f"  ⚠️ {code} [{t_date}] Tushare 未返回有效因子")
                    fail_count += 1
        except Exception as e:
            print(f"  ❌ {code} [{t_date}] 修复失败: {e}")
            fail_count += 1
        
        # 避免 Tushare 频率限制
        await asyncio.sleep(0.2)

    await db.disconnect()
    print(f"\n✅ 修复动作执行完成！")
    print(f"  - 尝试修复: {len(errors)}")
    print(f"  - 成功同步: {success_count}")
    print(f"  - 未获数据: {fail_count}")
    print("\n💡 提示：同步成功仅代表数据已从源头刷入，建议再次运行审计脚本验证数值是否匹配。")

if __name__ == "__main__":
    asyncio.run(fix_factors())
