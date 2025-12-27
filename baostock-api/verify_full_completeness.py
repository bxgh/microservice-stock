import asyncio
import datetime
from app.utils.database import db
import baostock as bs

async def verify_all_stocks_completeness():
    """全面验证所有股票数据完整性"""
    print("=" * 80)
    print("开始验证全部股票数据完整性...")
    print("=" * 80)
    
    await db.connect()
    bs.login()
    
    try:
        # 1. 获取数据库中所有股票代码
        codes_res = await db.execute("SELECT DISTINCT code FROM stock_kline_daily ORDER BY code")
        all_codes = [r[0] for r in codes_res]
        total_stocks = len(all_codes)
        print(f"\n数据库中共有 {total_stocks} 只股票")
        
        # 2. 验证统计
        issues = []
        verified_count = 0
        complete_count = 0
        incomplete_count = 0
        missing_recent_count = 0
        missing_historical_count = 0
        
        print("\n开始逐只验证...")
        print("-" * 80)
        
        for idx, code in enumerate(all_codes, 1):
            # 查询该股票的IPO日期
            rs = bs.query_stock_basic(code=code)
            ipo_date = None
            if rs.error_code == "0":
                row = rs.get_row_data()
                if row and len(row) > 2:
                    ipo_date_str = row[2]  # ipoDate
                    if ipo_date_str:
                        ipo_date = datetime.datetime.strptime(ipo_date_str, "%Y-%m-%d").date()
            
            # 查询数据库中该股票的数据范围
            range_res = await db.execute(
                "SELECT MIN(trade_date), MAX(trade_date), COUNT(*) FROM stock_kline_daily WHERE code=%s",
                (code,)
            )
            
            if not range_res or not range_res[0][0]:
                issues.append(f"{code}: 数据库中无数据")
                incomplete_count += 1
                continue
            
            db_min_date = range_res[0][0]
            db_max_date = range_res[0][1]
            record_count = range_res[0][2]
            
            today = datetime.date.today()
            
            # 检查1: 是否包含IPO日期
            historical_ok = True
            if ipo_date:
                # IPO日期应该在数据范围内（允许几天误差）
                if db_min_date > ipo_date + datetime.timedelta(days=10):
                    issues.append(f"{code}: 缺少历史数据 (IPO:{ipo_date}, DB最早:{db_min_date})")
                    historical_ok = False
                    missing_historical_count += 1
            
            # 检查2: 是否更新到最近
            recent_ok = True
            days_lag = (today - db_max_date).days
            # 允许最多5天延迟（考虑周末和节假日）
            if days_lag > 5:
                issues.append(f"{code}: 数据未更新到最新 (最新:{db_max_date}, 延迟:{days_lag}天)")
                recent_ok = False
                missing_recent_count += 1
            
            # 检查3: 数据量合理性（粗略估算：每年约240个交易日）
            if ipo_date:
                expected_years = (today - ipo_date).days / 365
                expected_records = int(expected_years * 240 * 0.7)  # 70%作为保守下限
                if record_count < expected_records:
                    issues.append(f"{code}: 数据量异常偏少 (实际:{record_count}, 预期>={expected_records})")
            
            if historical_ok and recent_ok:
                complete_count += 1
            else:
                incomplete_count += 1
            
            verified_count += 1
            
            # 每100只打印进度
            if verified_count % 100 == 0 or verified_count == total_stocks:
                print(f"验证进度: {verified_count}/{total_stocks} ({verified_count/total_stocks*100:.1f}%)")
        
        # 3. 输出验证报告
        print("\n" + "=" * 80)
        print("验证报告")
        print("=" * 80)
        print(f"总股票数: {total_stocks}")
        print(f"完整股票数: {complete_count} ({complete_count/total_stocks*100:.1f}%)")
        print(f"不完整股票数: {incomplete_count} ({incomplete_count/total_stocks*100:.1f}%)")
        print(f"  - 缺少历史数据: {missing_historical_count}")
        print(f"  - 缺少最新数据: {missing_recent_count}")
        
        if issues:
            print(f"\n发现 {len(issues)} 个问题:")
            print("-" * 80)
            for issue in issues[:50]:  # 只显示前50个问题
                print(f"  {issue}")
            if len(issues) > 50:
                print(f"  ... 还有 {len(issues)-50} 个问题未显示")
        else:
            print("\n✓ 所有股票数据均完整!")
        
        print("=" * 80)
        
    except Exception as e:
        print(f"验证过程出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        bs.logout()
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(verify_all_stocks_completeness())
