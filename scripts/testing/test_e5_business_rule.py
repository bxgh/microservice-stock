import asyncio
import os
import sys
from dotenv import load_dotenv

# 添加项目根目录到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.utils.database import db
from app.services.dimension_service import dimension_service
from app.services.business_rule_validator import business_rule_validator

load_dotenv()

async def run_e5_regression_test():
    print("=========================================")
    print("  E5: 业务规则校验回归测试 (Regression Test)")
    print("=========================================")
    await db.connect()
    try:
        # 使用一个已知的交易日进行测试
        target_date = '2026-04-30'
        print(f"[*] 测试目标日期: {target_date}")
        
        print("[1/4] 测试: 同步股票状态 (sync_stock_status)...")
        await dimension_service.sync_stock_status(target_date)
        print("  -> 状态同步完成")
        
        print("[2/4] 测试: 生成涨跌幅限制 (generate_daily_price_limits)...")
        await dimension_service.generate_daily_price_limits(target_date)
        print("  -> 涨跌幅限制生成完成")
        
        print("[3/4] 测试: 校验涨跌幅 (validate_price_limit)...")
        await business_rule_validator.validate_price_limit(target_date)
        print("  -> 涨跌幅校验完成")
        
        print("[4/4] 验证数据库结果...")
        async with db.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute('SELECT count(*) FROM dim_stock_status WHERE trade_date=%s', (target_date,))
                status_count = (await cur.fetchone())[0]
                
                await cur.execute('SELECT count(*) FROM dim_price_limit WHERE trade_date=%s', (target_date,))
                limit_count = (await cur.fetchone())[0]
                
                await cur.execute('SELECT count(*) FROM dq_findings WHERE trade_date=%s AND rule_id="PRICE_LIMIT_CHECK"', (target_date,))
                finding_count = (await cur.fetchone())[0]
                
                print(f"  -> dim_stock_status 记录数: {status_count}")
                print(f"  -> dim_price_limit 记录数: {limit_count}")
                print(f"  -> dq_findings (PRICE_LIMIT_CHECK) 预警数: {finding_count}")
                
                if status_count > 0 and limit_count > 0:
                    print("\n[SUCCESS] E5 业务规则校验模块回归测试通过！")
                else:
                    print("\n[FAILED] E5 业务规则校验模块回归测试失败：未生成维度数据！")
                    sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 测试过程中发生异常: {e}")
        sys.exit(1)
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(run_e5_regression_test())
