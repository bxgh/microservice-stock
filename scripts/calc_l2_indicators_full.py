import asyncio
import aiomysql
import logging
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("calc_l2_full")

DB_CONFIG = {
    'host': os.getenv("DB_HOST", "localhost"),
    'port': int(os.getenv("DB_PORT", 3306)),
    'user': os.getenv("DB_USER", "root"),
    'password': os.getenv("DB_PASSWORD", ""),
    'db': os.getenv("DB_NAME", "stock_data"),
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
        ) b ON o.industry_code = SUBSTRING_INDEX(b.industry_code, '.', 1)
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
        ) t ON o.industry_code = SUBSTRING_INDEX(t.industry_code, '.', 1)
        INNER JOIN stock_basic_info sb ON SUBSTRING_INDEX(t.top_code, '.', 1) = SUBSTRING_INDEX(sb.ts_code, '.', 1)
        SET 
            o.top_stock_code = t.top_code,
            o.top_stock_name = sb.name,
            o.top_stock_pct  = t.top_pct
        WHERE o.trade_date = %s
        """
        await cur.execute(sql_leader, (target_date, target_date))
        
        # 1.4 排名与多日累计
        await cur.execute("SELECT industry_code, pct_chg FROM ads_l2_industry_daily WHERE trade_date = %s ORDER BY pct_chg DESC", (target_date,))
        rows = await cur.fetchall()
        
        # 获取前5日和前20日的日期
        await cur.execute("SELECT DISTINCT trade_date FROM ods_sw_index_daily WHERE trade_date < %s ORDER BY trade_date DESC LIMIT 20", (target_date,))
        past_dates = await cur.fetchall()
        date_5d = past_dates[4][0] if len(past_dates) >= 5 else None
        date_20d = past_dates[19][0] if len(past_dates) >= 20 else None
        
        # 加载历史排名
        rank_5d_map = {}
        if date_5d:
            await cur.execute("SELECT industry_code, rank_today FROM ads_l2_industry_daily WHERE trade_date = %s", (date_5d,))
            for code, rk in await cur.fetchall():
                rank_5d_map[code] = rk
                
        rank_20d_map = {}
        if date_20d:
            await cur.execute("SELECT industry_code, rank_today FROM ads_l2_industry_daily WHERE trade_date = %s", (date_20d,))
            for code, rk in await cur.fetchall():
                rank_20d_map[code] = rk
                
        for i, (code, pct) in enumerate(rows):
            rank_today = i + 1
            rank_5d = rank_5d_map.get(code, None)
            rank_20d = rank_20d_map.get(code, None)
            diff_5d = rank_today - rank_5d if rank_5d is not None else None
            diff_20d = rank_today - rank_20d if rank_20d is not None else None
            
            await cur.execute(
                "UPDATE ads_l2_industry_daily SET rank_today = %s, rank_5d = %s, rank_20d = %s, rank_diff_5d = %s, rank_diff_20d = %s WHERE trade_date = %s AND industry_code = %s", 
                (rank_today, rank_5d, rank_20d, diff_5d, diff_20d, target_date, code)
            )
            
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
        
        # 计算 5/20 日累积差值 (适配 MySQL 5.7)
        await cur.execute("SELECT factor_code, long_index, short_index, factor_name FROM dim_style_factor WHERE is_active = 1")
        factors = await cur.fetchall()
        
        await cur.execute("SELECT DISTINCT trade_date FROM ods_index_daily WHERE trade_date <= %s ORDER BY trade_date DESC LIMIT 20", (target_date,))
        dates = [d[0] for d in await cur.fetchall()]
        
        for f_code, l_idx, s_idx, f_name in factors:
            spread_today = spread_5d = spread_20d = None
            
            # 查该因子所需的所有相关日期的指数数据
            if not dates:
                continue
            
            # 使用 IN 查询
            date_str = "('" + "','".join(d.strftime("%Y-%m-%d") if isinstance(d, datetime.date) else str(d) for d in dates) + "')"
            
            # 取多头
            await cur.execute(f"SELECT trade_date, pct_chg FROM ods_index_daily WHERE ts_code = %s AND trade_date IN {date_str}", (l_idx,))
            l_dict = {d.strftime("%Y-%m-%d") if isinstance(d, datetime.date) else str(d): pct for d, pct in await cur.fetchall()}
            
            # 取空头
            await cur.execute(f"SELECT trade_date, pct_chg FROM ods_index_daily WHERE ts_code = %s AND trade_date IN {date_str}", (s_idx,))
            s_dict = {d.strftime("%Y-%m-%d") if isinstance(d, datetime.date) else str(d): pct for d, pct in await cur.fetchall()}
            
            td_str = str(target_date)
            if td_str in l_dict and td_str in s_dict:
                long_pct = l_dict[td_str]
                short_pct = s_dict[td_str]
                spread_today = float(long_pct - short_pct)
                
                # 计算 5d
                dates_5d = dates[:5]
                s_5d = 0.0
                for d in dates_5d:
                    d_str = d.strftime("%Y-%m-%d") if isinstance(d, datetime.date) else str(d)
                    if d_str in l_dict and d_str in s_dict:
                        s_5d += float(l_dict[d_str] - s_dict[d_str])
                spread_5d = s_5d
                
                # 计算 20d
                s_20d = 0.0
                for d in dates:
                    d_str = d.strftime("%Y-%m-%d") if isinstance(d, datetime.date) else str(d)
                    if d_str in l_dict and d_str in s_dict:
                        s_20d += float(l_dict[d_str] - s_dict[d_str])
                spread_20d = s_20d
                
                direction = 'balanced'
                if spread_today > 0.005: direction = 'long_dominant'
                elif spread_today < -0.005: direction = 'short_dominant'
                
                await cur.execute(
                    """INSERT INTO ads_l2_style_factor 
                    (trade_date, factor_code, factor_name, long_pct, short_pct, spread_today, spread_5d, spread_20d, direction)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (target_date, f_code, f_name, long_pct, short_pct, spread_today, spread_5d, spread_20d, direction)
                )
        
    conn.close()
    logger.info("L2 完整指标计算成功结束")

if __name__ == "__main__":
    import sys
    date = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(calc_full_indicators(date))
