import asyncio
import aiomysql
import logging
import datetime
import os

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("calc_l2_full")

DB_CONFIG = {
    'host': 'sh-cdb-h7flpxu4.sql.tencentcdb.com',
    'port': 26300,
    'user': 'root',
    'password': 'alwaysup@888',
    'db': 'alwaysup',
    'autocommit': True
}

async def calc_full_indicators(target_date: str = None):
    if not target_date:
        target_date = datetime.date.today().strftime("%Y-%m-%d")
        
    logger.info(f"开始计算 {target_date} 的完整 L2 指标 (最终修正版)...")
    
    conn = await aiomysql.connect(**DB_CONFIG)
    async with conn.cursor() as cur:
        # 增加 GROUP_CONCAT 长度限制
        await cur.execute("SET SESSION group_concat_max_len = 1000000")
        
        # 1. ads_l2_industry_daily
        logger.info("同步 ads_l2_industry_daily...")
        await cur.execute("DELETE FROM ads_l2_industry_daily WHERE trade_date = %s", (target_date,))
        
        # 1.1 基础行情与财务指标
        sql_base = """
        INSERT INTO ads_l2_industry_daily (
            trade_date, industry_code, industry_name,
            close, pct_chg, amount, turnover_rate,
            pe_ttm, pb, dv_ratio, compute_version
        )
        SELECT
            trade_date, ts_code, name,
            close, pct_chg, amount, 0.0,
            pe_ttm, pb, dv_ratio, 'v1'
        FROM ods_sw_index_daily
        WHERE trade_date = %s AND level = 'l1'
        """
        await cur.execute(sql_base, (target_date,))
        
        # 1.2 广度
        sql_breadth = """
        UPDATE ads_l2_industry_daily o
        INNER JOIN (
            SELECT
                sw.l1_code AS industry_code,
                SUM(CASE WHEN k.pct_chg > 0  THEN 1 ELSE 0 END) AS up_count,
                SUM(CASE WHEN k.pct_chg < 0  THEN 1 ELSE 0 END) AS down_count,
                SUM(CASE WHEN k.pct_chg >= 0.099 THEN 1 ELSE 0 END) AS limit_up_count,
                COUNT(*) AS total_count
            FROM stock_kline_daily k
            INNER JOIN stock_industry_sw sw ON k.code = sw.code
            WHERE k.trade_date = %s
            GROUP BY sw.l1_code
        ) b ON o.industry_code = b.industry_code
        SET
            o.up_count         = b.up_count,
            o.down_count       = b.down_count,
            o.limit_up_count   = b.limit_up_count,
            o.total_count      = b.total_count,
            o.internal_breadth = CAST(b.up_count AS DECIMAL(10,6)) / b.total_count
        WHERE o.trade_date = %s
        """
        await cur.execute(sql_breadth, (target_date, target_date))
        
        # 1.3 领涨股
        sql_leader = """
        UPDATE ads_l2_industry_daily o
        INNER JOIN (
            SELECT 
                sw.l1_code AS industry_code,
                SUBSTRING_INDEX(GROUP_CONCAT(k.code ORDER BY k.pct_chg DESC), ',', 1) AS top_code,
                MAX(k.pct_chg) AS top_pct
            FROM stock_kline_daily k
            INNER JOIN stock_industry_sw sw ON k.code = sw.code
            WHERE k.trade_date = %s
            GROUP BY sw.l1_code
        ) t ON o.industry_code = t.industry_code
        INNER JOIN stock_basic_info sb ON t.top_code = sb.ts_code
        SET 
            o.top_stock_code = t.top_code,
            o.top_stock_name = sb.name,
            o.top_stock_pct  = t.top_pct
        WHERE o.trade_date = %s
        """
        await cur.execute(sql_leader, (target_date, target_date))
        
        # 1.4 排名
        await cur.execute("SELECT industry_code, pct_chg FROM ads_l2_industry_daily WHERE trade_date = %s ORDER BY pct_chg DESC", (target_date,))
        rows = await cur.fetchall()
        for i, (code, pct) in enumerate(rows):
            await cur.execute("UPDATE ads_l2_industry_daily SET rank_today = %s WHERE trade_date = %s AND industry_code = %s", (i + 1, target_date, code))
            
        # 2. ads_l2_concept_daily
        logger.info("同步 ads_l2_concept_daily...")
        await cur.execute("DELETE FROM ads_l2_concept_daily WHERE trade_date = %s", (target_date,))
        sql_concept = """
        INSERT INTO ads_l2_concept_daily (
            trade_date, concept_code, concept_name,
            pct_chg, amount, turnover_rate,
            up_count, down_count, constituent_count, compute_version
        )
        SELECT
            trade_date, concept_code, concept_name,
            pct_chg, amount, 0.0,
            up_count, down_count, constituent_count, 'v1'
        FROM ods_concept_kline_daily
        WHERE trade_date = %s
        """
        await cur.execute(sql_concept, (target_date,))
        
        # 3. ads_l2_style_factor
        logger.info("同步 ads_l2_style_factor...")
        await cur.execute("DELETE FROM ads_l2_style_factor WHERE trade_date = %s", (target_date,))
        sql_style = """
        INSERT INTO ads_l2_style_factor (
            trade_date, factor_code, factor_name,
            long_pct, short_pct, spread_today, direction
        )
        SELECT
            %s, f.factor_code, f.factor_name,
            l.pct_chg, s.pct_chg,
            l.pct_chg - s.pct_chg,
            CASE WHEN (l.pct_chg - s.pct_chg) > 0.005 THEN 'long_dominant'
                 WHEN (l.pct_chg - s.pct_chg) < -0.005 THEN 'short_dominant'
                 ELSE 'balanced' END
        FROM dim_style_factor f
        INNER JOIN ods_index_daily l ON f.long_index = l.ts_code AND l.trade_date = %s
        INNER JOIN ods_index_daily s ON f.short_index = s.ts_code AND s.trade_date = %s
        WHERE f.is_active = 1
        """
        await cur.execute(sql_style, (target_date, target_date, target_date))
        
    conn.close()
    logger.info("L2 完整指标计算成功结束")

if __name__ == "__main__":
    import sys
    date = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(calc_full_indicators(date))
