import asyncio
from typing import Dict, Any, List, Optional
from app.utils.database import db
from app.utils.logger import get_logger

logger = get_logger("stock-manager.indicator")


class IndicatorService:
    def __init__(self):
        pass

    async def calculate_l1_market_overview(self, target_date: str):
        """计算 L1 市场全景指标

        按照 E2_indicators.md 中的 SQL 逻辑分步执行。
        """
        try:
            logger.info(f"开始计算 L1 全景指标: {target_date}")

            # 1. 清理数据 (幂等性)
            await db.execute("DELETE FROM ads_l1_market_overview WHERE trade_date = %s", (target_date,))

            # 2. 插入指数数据
            insert_sql = """
                INSERT INTO ads_l1_market_overview (
                    trade_date,
                    idx_sh_close,    idx_sh_pct,
                    idx_sz_close,    idx_sz_pct,
                    idx_cyb_close,   idx_cyb_pct,
                    idx_kc50_close,  idx_kc50_pct,
                    idx_bz50_close,  idx_bz50_pct,
                    idx_hs300_close, idx_hs300_pct,
                    idx_zz500_close, idx_zz500_pct,
                    idx_zz1000_close,idx_zz1000_pct,
                    idx_zz2000_close,idx_zz2000_pct,
                    idx_winda_close, idx_winda_pct,
                    compute_version
                )
                SELECT
                    %s AS trade_date,
                    MAX(CASE WHEN ts_code = '000001.SH'  THEN close   END) AS idx_sh_close,
                    MAX(CASE WHEN ts_code = '000001.SH'  THEN pct_chg END) AS idx_sh_pct,
                    MAX(CASE WHEN ts_code = '399001.SZ'  THEN close   END) AS idx_sz_close,
                    MAX(CASE WHEN ts_code = '399001.SZ'  THEN pct_chg END) AS idx_sz_pct,
                    MAX(CASE WHEN ts_code = '399006.SZ'  THEN close   END) AS idx_cyb_close,
                    MAX(CASE WHEN ts_code = '399006.SZ'  THEN pct_chg END) AS idx_cyb_pct,
                    MAX(CASE WHEN ts_code = '000688.SH'  THEN close   END) AS idx_kc50_close,
                    MAX(CASE WHEN ts_code = '000688.SH'  THEN pct_chg END) AS idx_kc50_pct,
                    MAX(CASE WHEN ts_code = '899050.BJ'  THEN close   END) AS idx_bz50_close,
                    MAX(CASE WHEN ts_code = '899050.BJ'  THEN pct_chg END) AS idx_bz50_pct,
                    MAX(CASE WHEN ts_code = '000300.SH'  THEN close   END) AS idx_hs300_close,
                    MAX(CASE WHEN ts_code = '000300.SH'  THEN pct_chg END) AS idx_hs300_pct,
                    MAX(CASE WHEN ts_code = '000905.SH'  THEN close   END) AS idx_zz500_close,
                    MAX(CASE WHEN ts_code = '000905.SH'  THEN pct_chg END) AS idx_zz500_pct,
                    MAX(CASE WHEN ts_code = '000852.SH'  THEN close   END) AS idx_zz1000_close,
                    MAX(CASE WHEN ts_code = '000852.SH'  THEN pct_chg END) AS idx_zz1000_pct,
                    MAX(CASE WHEN ts_code = '932000.CSI' THEN close   END) AS idx_zz2000_close,
                    MAX(CASE WHEN ts_code = '932000.CSI' THEN pct_chg END) AS idx_zz2000_pct,
                    MAX(CASE WHEN ts_code = '000985.SH'  THEN close   END) AS idx_winda_close,
                    MAX(CASE WHEN ts_code = '000985.SH'  THEN pct_chg END) AS idx_winda_pct,
                    'v1' AS compute_version
                FROM ods_index_daily
                WHERE trade_date = %s
                AND ts_code IN (
                    '000001.SH','399001.SZ','399006.SZ','000688.SH','899050.BJ',
                    '000300.SH','000905.SH','000852.SH','932000.CSI','000985.SH'
                )
            """
            await db.execute(insert_sql, (target_date, target_date))

            # 3. 计算全 A 总成交额 (仅统计个股，排除指数)
            update_turnover_sql = """
                UPDATE ads_l1_market_overview o
                SET turnover_total = (
                    SELECT SUM(k.amount) FROM stock_kline_daily k
                    JOIN stock_basic_info s ON k.ts_code = s.ts_code
                    WHERE k.trade_date = %s
                )
                WHERE trade_date = %s
            """
            await db.execute(update_turnover_sql, (target_date, target_date))

            # 4. 计算成交额 MA5/MA20 (兼容 MySQL 5.7)
            update_ma_sql = """
                UPDATE ads_l1_market_overview o
                SET
                  turnover_ma5 = (
                      SELECT AVG(turnover_total) FROM (
                          SELECT turnover_total FROM ads_l1_market_overview
                          WHERE trade_date <= %s ORDER BY trade_date DESC LIMIT 5
                      ) t5
                  ),
                  turnover_ma20 = (
                      SELECT AVG(turnover_total) FROM (
                          SELECT turnover_total FROM ads_l1_market_overview
                          WHERE trade_date <= %s ORDER BY trade_date DESC LIMIT 20
                      ) t20
                  ),
                  turnover_pct_vs_ma20 = (turnover_total / (
                      SELECT AVG(turnover_total) FROM (
                          SELECT turnover_total FROM ads_l1_market_overview
                          WHERE trade_date <= %s ORDER BY trade_date DESC LIMIT 20
                      ) t20_pct
                  )) - 1
                WHERE o.trade_date = %s
            """
            await db.execute(update_ma_sql, (target_date, target_date, target_date, target_date))

            # 5. 计算分位数 (避开 MySQL 1093 错误: 无法在 UPDATE 中直接子查询同一张表)
            # 先查出当日成交额
            res_val = await db.execute("SELECT turnover_total FROM ads_l1_market_overview WHERE trade_date = %s", (target_date,))
            curr_turnover = res_val[0][0] if res_val and res_val[0][0] else 0

            if curr_turnover:
                update_pctile_sql = """
                    UPDATE ads_l1_market_overview o
                    SET turnover_pctile_1y = (
                        SELECT COUNT(*) / 250.0 FROM (
                            SELECT turnover_total as daily_sum FROM ads_l1_market_overview
                            WHERE trade_date <= %s ORDER BY trade_date DESC LIMIT 250
                        ) tmp_hist
                        WHERE daily_sum < %s
                    )
                    WHERE trade_date = %s
                """
                await db.execute(update_pctile_sql, (target_date, curr_turnover, target_date))

            # 6. 同步涨跌家数与广度 (从 ODS 同步)
            update_breadth_sql = """
                UPDATE ads_l1_market_overview o
                JOIN ods_market_breadth_daily b ON o.trade_date = b.trade_date
                SET o.up_count = b.up_count,
                    o.down_count = b.down_count,
                    o.flat_count = b.flat_count,
                    o.market_breadth = IF(b.total_count > 0, b.up_count / b.total_count, 0),
                    o.up_down_ratio = IF(b.down_count > 0, b.up_count / b.down_count, 0),
                    o.high_60d_count = b.high_60d_count,
                    o.low_60d_count = b.low_60d_count,
                    o.high_250d_count = b.high_250d_count,
                    o.low_250d_count = b.low_250d_count
                WHERE o.trade_date = %s
            """
            await db.execute(update_breadth_sql, (target_date,))

            # 7. 同步涨跌停池统计
            update_pool_sql = """
                UPDATE ads_l1_market_overview o
                INNER JOIN (
                    SELECT
                        trade_date,
                        SUM(CASE WHEN pool_type = 'zt'   THEN 1 ELSE 0 END) AS zt,
                        SUM(CASE WHEN pool_type = 'dt'   THEN 1 ELSE 0 END) AS dt,
                        SUM(CASE WHEN pool_type = 'zb'   THEN 1 ELSE 0 END) AS zb,
                        SUM(CASE WHEN pool_type = 'lian' THEN 1 ELSE 0 END) AS lian,
                        MAX(CASE WHEN pool_type IN ('zt','lian') THEN board_height ELSE 0 END) AS max_h
                    FROM ods_event_limit_pool
                    WHERE trade_date = %s
                    GROUP BY trade_date
                ) p ON o.trade_date = p.trade_date
                SET
                    o.limit_up_count   = p.zt,
                    o.limit_down_count = p.dt,
                    o.blast_count      = p.zb,
                    o.lian_count       = p.lian,
                    o.max_board_height = p.max_h
                WHERE o.trade_date = %s
            """
            await db.execute(update_pool_sql, (target_date, target_date))

            # 8. 市场状态分类 (Market Regime)
            update_regime_sql = """
                UPDATE ads_l1_market_overview
                SET market_regime = CASE
                    WHEN turnover_pctile_1y < 0.20 THEN 'low_vol'
                    WHEN up_down_ratio > 3 AND limit_up_count > 60 THEN 'broad_up'
                    WHEN up_down_ratio < 0.33 AND limit_down_count > 30 THEN 'broad_down'
                    ELSE 'structural'
                END
                WHERE trade_date = %s
            """
            await db.execute(update_regime_sql, (target_date,))

            logger.info(f"L1 全景指标计算完成: {target_date}")
            return True
        except Exception as e:
            logger.error(f"计算 L1 全景指标失败: {target_date}, {e}")
            raise

    async def calculate_l2_indicators_full(self, target_date: str = None):
        """执行完整 L2 指标计算 (行业旋转、概念热点、风格因子)

        从 scripts/calc_l2_indicators_full.py 迁移并优化。
        """
        try:
            if not target_date:
                import datetime
                target_date = datetime.date.today().strftime("%Y-%m-%d")

            logger.info(f"开始执行 L2 完整指标计算: {target_date}")

            # 增加 GROUP_CONCAT 长度限制
            await db.execute("SET SESSION group_concat_max_len = 1000000")

            # 1. 行业维度 (ads_l2_industry_daily)
            logger.info(">>> 1. 计算行业维度指标")
            await db.execute("DELETE FROM ads_l2_industry_daily WHERE trade_date = %s", (target_date,))

            # 1.1 基础行情
            insert_industry_sql = """
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
            await db.execute(insert_industry_sql, (target_date,))

            # 1.2 行业内部广度
            sql_breadth = """
            UPDATE ads_l2_industry_daily o
            INNER JOIN (
                SELECT
                    sw.l1_code AS industry_code,
                    SUM(CASE WHEN k.pct_chg > 0  THEN 1 ELSE 0 END) AS up_count,
                    SUM(CASE WHEN k.pct_chg < 0  THEN 1 ELSE 0 END) AS down_count,
                    SUM(CASE WHEN k.pct_chg >= 0.099 THEN 1 ELSE 0 END) AS limit_up_count,
                    COUNT(*) AS total_count
                FROM v_stock_kline_forward_adj k
                INNER JOIN stock_industry_sw sw ON k.ts_code = sw.code
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
            await db.execute(sql_breadth, (target_date, target_date))

            # 1.3 领涨股
            sql_leader = """
            UPDATE ads_l2_industry_daily o
            INNER JOIN (
                SELECT
                    sw.l1_code AS industry_code,
                    SUBSTRING_INDEX(GROUP_CONCAT(k.ts_code ORDER BY k.pct_chg DESC), ',', 1) AS top_code,
                    MAX(k.pct_chg) AS top_pct
                FROM v_stock_kline_forward_adj k
                INNER JOIN stock_industry_sw sw ON k.ts_code = sw.code
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
            await db.execute(sql_leader, (target_date, target_date))

            # 1.4 排名变化 (5日/20日)
            rows = await db.execute("SELECT industry_code, pct_chg FROM ads_l2_industry_daily WHERE trade_date = %s ORDER BY pct_chg DESC", (target_date,))

            past_dates_rows = await db.execute("SELECT DISTINCT trade_date FROM ads_l2_industry_daily WHERE trade_date < %s ORDER BY trade_date DESC LIMIT 20", (target_date,))
            past_dates = [r[0] for r in past_dates_rows]
            date_5d = past_dates[4] if len(past_dates) >= 5 else (
                past_dates[-1] if past_dates else None)
            date_20d = past_dates[19] if len(past_dates) >= 20 else (
                past_dates[-1] if past_dates else None)

            rank_5d_map = {}
            if date_5d:
                res_5d = await db.execute("SELECT industry_code, rank_today FROM ads_l2_industry_daily WHERE trade_date = %s", (date_5d,))
                rank_5d_map = {r[0]: r[1] for r in res_5d}

            rank_20d_map = {}
            if date_20d:
                res_20d = await db.execute("SELECT industry_code, rank_today FROM ads_l2_industry_daily WHERE trade_date = %s", (date_20d,))
                rank_20d_map = {r[0]: r[1] for r in res_20d}

            for i, r in enumerate(rows):
                code = r[0]
                rank_curr = i + 1
                r5 = rank_5d_map.get(code)
                r20 = rank_20d_map.get(code)
                diff5 = rank_curr - r5 if r5 else None
                diff20 = rank_curr - r20 if r20 else None

                await db.execute(
                    "UPDATE ads_l2_industry_daily SET rank_today = %s, rank_5d = %s, rank_20d = %s, rank_diff_5d = %s, rank_diff_20d = %s WHERE trade_date = %s AND industry_code = %s",
                    (rank_curr, r5, r20, diff5, diff20, target_date, code)
                )

            # 2. 概念维度 (ads_l2_concept_daily)
            logger.info(">>> 2. 计算概念维度指标")
            await db.execute("DELETE FROM ads_l2_concept_daily WHERE trade_date = %s", (target_date,))
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
            await db.execute(sql_concept, (target_date,))

            # 3. 风格因子 (ads_l2_style_factor)
            logger.info(">>> 3. 计算风格因子利差指标")
            await db.execute("DELETE FROM ads_l2_style_factor WHERE trade_date = %s", (target_date,))

            factors = await db.execute("SELECT factor_code, long_index, short_index, factor_name FROM dim_style_factor WHERE is_active = 1")

            date_rows = await db.execute("SELECT DISTINCT trade_date FROM ods_index_daily WHERE trade_date <= %s ORDER BY trade_date DESC LIMIT 20", (target_date,))
            dates = [r[0] for r in date_rows]

            if dates:
                date_str_list = [d.strftime(
                    "%Y-%m-%d") if hasattr(d, 'strftime') else str(d) for d in dates]

                for f_code, l_idx, s_idx, f_name in factors:
                    l_res = await db.execute("SELECT trade_date, pct_chg FROM ods_index_daily WHERE ts_code = %s AND trade_date IN %s", (l_idx, tuple(date_str_list)))
                    l_dict = {str(r[0]): float(r[1]) for r in l_res}

                    s_res = await db.execute("SELECT trade_date, pct_chg FROM ods_index_daily WHERE ts_code = %s AND trade_date IN %s", (s_idx, tuple(date_str_list)))
                    s_dict = {str(r[0]): float(r[1]) for r in s_res}

                    td_str = str(target_date)
                    if td_str in l_dict and td_str in s_dict:
                        long_pct = l_dict[td_str]
                        short_pct = s_dict[td_str]
                        spread_today = long_pct - short_pct

                        s_5d = sum(l_dict.get(d) - s_dict.get(d)
                                   for d in date_str_list[:5] if d in l_dict and d in s_dict)
                        s_20d = sum(l_dict.get(d) - s_dict.get(d)
                                    for d in date_str_list if d in l_dict and d in s_dict)

                        direction = 'balanced'
                        if spread_today > 0.005:
                            direction = 'long_dominant'
                        elif spread_today < -0.005:
                            direction = 'short_dominant'

                        await db.execute(
                            """INSERT INTO ads_l2_style_factor
                            (trade_date, factor_code, factor_name, long_pct, short_pct, spread_today, spread_5d, spread_20d, direction)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                            (target_date, f_code, f_name, long_pct, short_pct, spread_today, s_5d, s_20d, direction)
                        )

            logger.info(f"L2 完整指标计算完成: {target_date}")
            return True

        except Exception as e:
            logger.error(f"L2 完整指标计算失败: {target_date}, {e}", exc_info=True)
            raise
