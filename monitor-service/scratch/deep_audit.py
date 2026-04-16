import asyncio
import sys
sys.path.append("/home/ubuntu/microservice-stock/monitor-service")
from app.utils.database import db

async def deep_audit():
    await db.connect()
    try:
        print("=" * 70)
        print("深度数据审计报告")
        print("=" * 70)

        # 1. raw_capital_flow_summary - 北向资金汇总
        print("\n[1] raw_capital_flow_summary (北向资金汇总)")
        r = await db.execute("SELECT MIN(trade_date), MAX(trade_date), COUNT(*) FROM raw_capital_flow_summary")
        print(f"  范围: {r[0][0]} ~ {r[0][1]}, 共 {r[0][2]} 条")
        r2 = await db.execute("SELECT trade_date, north_net_inflow FROM raw_capital_flow_summary ORDER BY trade_date DESC LIMIT 3")
        for row in r2:
            print(f"  最新: {row[0]} -> 净流入={row[1]}")

        # 2. stock_north_funds_daily - 北向个股持股
        print("\n[2] stock_north_funds_daily (北向个股持股)")
        r = await db.execute("SELECT MIN(trade_date), MAX(trade_date), COUNT(*), COUNT(DISTINCT trade_date) FROM stock_north_funds_daily")
        print(f"  范围: {r[0][0]} ~ {r[0][1]}, 共 {r[0][2]} 条, {r[0][3]} 个交易日")

        # 3. stock_lhb_daily - 龙虎榜
        print("\n[3] stock_lhb_daily (龙虎榜)")
        r = await db.execute("SELECT MIN(trade_date), MAX(trade_date), COUNT(*), COUNT(DISTINCT trade_date) FROM stock_lhb_daily")
        print(f"  范围: {r[0][0]} ~ {r[0][1]}, 共 {r[0][2]} 条, {r[0][3]} 个交易日")
        # Check schema
        cols = await db.execute("DESCRIBE stock_lhb_daily")
        print(f"  字段: {[c[0] for c in cols]}")

        # 4. raw_sector_daily - 行业/ETF日线
        print("\n[4] raw_sector_daily (行业/ETF日线)")
        r = await db.execute("SELECT MIN(trade_date), MAX(trade_date), COUNT(*), COUNT(DISTINCT ts_code) FROM raw_sector_daily")
        print(f"  范围: {r[0][0]} ~ {r[0][1]}, 共 {r[0][2]} 条, {r[0][3]} 个代码")
        r2 = await db.execute("SELECT ts_code, COUNT(*) as cnt FROM raw_sector_daily GROUP BY ts_code ORDER BY cnt DESC LIMIT 10")
        print(f"  Top10代码:")
        for row in r2:
            print(f"    {row[0]}: {row[1]} 条")

        # 5. market_margin_summary - 两融汇总
        print("\n[5] market_margin_summary (两融汇总)")
        r = await db.execute("SELECT MIN(trade_date), MAX(trade_date), COUNT(*) FROM market_margin_summary")
        print(f"  范围: {r[0][0]} ~ {r[0][1]}, 共 {r[0][2]} 条")
        cols = await db.execute("DESCRIBE market_margin_summary")
        print(f"  字段: {[c[0] for c in cols]}")
        r2 = await db.execute("SELECT * FROM market_margin_summary ORDER BY trade_date DESC LIMIT 2")
        for row in r2:
            print(f"  最新记录: {row}")

        # 6. raw_market_stats - 大盘统计
        print("\n[6] raw_market_stats (大盘统计)")
        r = await db.execute("SELECT COUNT(*) FROM raw_market_stats")
        print(f"  记录数: {r[0][0]}")
        cols = await db.execute("DESCRIBE raw_market_stats")
        print(f"  字段: {[c[0] for c in cols]}")

        # 7. stock_sentiment_daily - 市场情绪
        print("\n[7] stock_sentiment_daily (市场情绪)")
        r = await db.execute("SELECT COUNT(*) FROM stock_sentiment_daily")
        print(f"  记录数: {r[0][0]}")
        cols = await db.execute("DESCRIBE stock_sentiment_daily")
        print(f"  字段: {[c[0] for c in cols]}")
        if r[0][0] > 0:
            r2 = await db.execute("SELECT * FROM stock_sentiment_daily LIMIT 1")
            print(f"  样本: {r2[0]}")

        # 8. wencai_fund_holdings - 基金持仓
        print("\n[8] wencai_fund_holdings (基金持仓)")
        r = await db.execute("SELECT COUNT(*) FROM wencai_fund_holdings")
        print(f"  记录数: {r[0][0]}")
        cols = await db.execute("DESCRIBE wencai_fund_holdings")
        print(f"  字段: {[c[0] for c in cols]}")

        # 9. stock_block_trade - 大宗交易
        print("\n[9] stock_block_trade (大宗交易)")
        r = await db.execute("SELECT MIN(trade_date), MAX(trade_date), COUNT(*) FROM stock_block_trade")
        print(f"  范围: {r[0][0]} ~ {r[0][1]}, 共 {r[0][2]} 条")

        # 10. daily_basic - 每日基础数据
        print("\n[10] daily_basic (每日基础数据)")
        r = await db.execute("SELECT MIN(trade_date), MAX(trade_date), COUNT(*) FROM daily_basic")
        print(f"  范围: {r[0][0]} ~ {r[0][1]}, 共 {r[0][2]} 条")
        cols = await db.execute("DESCRIBE daily_basic")
        col_names = [c[0] for c in cols]
        print(f"  字段: {col_names}")

        # 11. Check for tables we might need
        print("\n[11] 其他相关表检查")
        for tbl in ['stock_shareholder_count', 'stock_restricted_release', 'stock_industry_sw']:
            try:
                r = await db.execute(f"SELECT COUNT(*) FROM {tbl}")
                print(f"  {tbl}: {r[0][0]} 条")
            except Exception as e:
                print(f"  {tbl}: 不存在或无法访问")

    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(deep_audit())
