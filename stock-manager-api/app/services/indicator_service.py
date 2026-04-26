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
                    MAX(CASE WHEN ts_code = '000985.CSI' THEN close   END) AS idx_winda_close,
                    MAX(CASE WHEN ts_code = '000985.CSI' THEN pct_chg END) AS idx_winda_pct,
                    'v1' AS compute_version
                FROM ods_index_daily
                WHERE trade_date = %s
                AND ts_code IN (
                    '000001.SH','399001.SZ','399006.SZ','000688.SH','899050.BJ',
                    '000300.SH','000905.SH','000852.SH','932000.CSI','000985.CSI'
                )
            """
            await db.execute(insert_sql, (target_date, target_date))

            # 3. 计算全 A 总成交额 (仅统计个股，排除指数)
            update_turnover_sql = """
                UPDATE ads_l1_market_overview o
                SET turnover_total = (
                    SELECT SUM(k.amount) * 1000 FROM stock_kline_daily k
                    JOIN stock_basic_info s ON k.code = s.ts_code
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
                  )
                WHERE o.trade_date = %s
            """
            await db.execute(update_ma_sql, (target_date, target_date, target_date))

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
                    o.low_60d_count = b.low_60d_count
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
