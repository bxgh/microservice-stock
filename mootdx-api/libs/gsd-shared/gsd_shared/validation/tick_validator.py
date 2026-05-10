import logging
from datetime import datetime
from typing import Optional, List, Set, Any, Dict
import pytz

try:
    from asynch.pool import Pool as AsynchPool
except ImportError:
    AsynchPool = Any

from gsd_shared.validation.standards import TickStandards

logger = logging.getLogger(__name__)
CST = pytz.timezone('Asia/Shanghai')


class TickValidator:
    """
    分笔数据校验器 (精简版)
    
    职责:
    1. 采前/采中校验: 检查数据是否已达标 (基于 TickStandards.Loose)
    2. 采后校验: 精准审计与金丝雀校验
    """
    
    # 核心权重股 (金丝雀)
    CANARY_STOCKS = {
        '000001', '600519', '600036', '601318', '000002', 
        '300059', '000725', '600000', '000858', '600276'
    }

    def __init__(self, clickhouse_pool: Optional[AsynchPool]):
        self.ch_pool = clickhouse_pool

    async def check_quality(self, ts_code: str, trade_date: str) -> bool:
        """
        检查 ClickHouse 中数据是否存在且符合质量标准 (宽松标准)
        用于采集前的幂等性检查。
        """
        if not self.ch_pool:
            return False

        try:
            trade_date_str = datetime.strptime(
                trade_date.replace("-", ""), "%Y%m%d"
            ).strftime("%Y-%m-%d")
            
            today_str = datetime.now(CST).strftime("%Y-%m-%d")
            target_table = "tick_data_intraday" if trade_date_str == today_str else "tick_data"
            
            async with self.ch_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(f"""
                        SELECT 
                            count() as tick_count,
                            min(tick_time) as min_time,
                            max(tick_time) as max_time
                        FROM {target_table} 
                        WHERE ts_code = %(ts_code)s 
                          AND trade_date = %(trade_date)s
                    """, {"ts_code": ts_code, "trade_date": trade_date_str})
                    row = await cursor.fetchone()
                    
                    if not row or row[0] == 0:
                        return False
                    
                    tick_count, min_time, max_time = row
                    
                    # 使用标准化的宽松标准
                    if tick_count < TickStandards.Loose.MIN_COUNT:
                        return False
                    
                    if min_time and max_time:
                        if str(min_time) > TickStandards.Loose.MIN_TIME or str(max_time) < TickStandards.Loose.MAX_TIME:
                            return False
                    
                    logger.debug(f"✓ {stock_code} 数据已达标(宽松): {tick_count} ticks")
                    return True
        except Exception as e:
            logger.error(f"检查数据质量失败 {stock_code}: {e}")
            return False

    async def check_intraday_coverage(
        self, 
        stock_codes: List[str], 
        trade_date: str,
        session: str = 'close'
    ) -> tuple[int, int, List[str]]:
        """
        检查盘中分笔表的覆盖率
        """
        if not self.ch_pool or not stock_codes:
            return len(stock_codes), 0, stock_codes
        
        try:
            if len(trade_date) == 8:
                trade_date_str = datetime.strptime(trade_date, "%Y%m%d").strftime("%Y-%m-%d")
            else:
                trade_date_str = trade_date
            
            # 构建时间过滤条件
            time_filter = "tick_time <= '11:30:00'" if session == 'noon' else "1=1"
            
            # 简化逻辑：只看是否有数据覆盖 09:30 之前且数量达标
            min_count = 110 if session == 'noon' else 230
            
            having_sql = "count() >= %(min_count)s AND min(tick_time) <= '09:30:00'"
            params = {"trade_date": trade_date_str, "min_count": min_count}
            
            if session == 'noon':
                having_sql += " AND max(tick_time) >= %(min_time)s"
                params["min_time"] = TickStandards.Precise.SNAPSHOT_MIN_TIME_NOON
            elif session == 'close':
                having_sql += " AND max(tick_time) >= %(min_time)s"
                params["min_time"] = TickStandards.Precise.SNAPSHOT_MIN_TIME_CLOSE
            
            async with self.ch_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(f"""
                        SELECT DISTINCT stock_code 
                        FROM tick_data_intraday 
                        WHERE trade_date = %(trade_date)s AND {time_filter}
                        GROUP BY stock_code
                        HAVING {having_sql}
                    """, params)
                    rows = await cursor.fetchall()
                    actual_codes = {row[0] for row in rows}
            
            expected_set = set(stock_codes)
            missing_codes = list(expected_set - actual_codes)
            
            logger.info(f"📊 盘中分笔覆盖率检查 ({session}): {len(actual_codes)}/{len(expected_set)}")
            
            return len(expected_set), len(actual_codes), missing_codes
            
        except Exception as e:
            logger.error(f"❌ 检查盘中分笔覆盖率失败: {e}")
            return len(stock_codes), 0, stock_codes

    async def validate_stock(self, ts_code: str, trade_date: str, session: str = 'close') -> Dict[str, Any]:
        """
        个股精准审计校验 (基于快照优先策略)
        """
        result = {
            "code": ts_code,
            "status": "PASS",
            "reasons": [],
            "action": "NONE",
            "source": "none"
        }

        if not self.ch_pool:
            result.update({"status": "FAIL", "reasons": ["No DB Connection"], "action": "REPAIR"})
            return result

        try:
            trade_date_str = datetime.strptime(trade_date.replace("-", ""), "%Y%m%d").strftime("%Y-%m-%d")
            today_str = datetime.now(CST).strftime("%Y-%m-%d")
            
            target_table = "tick_data_intraday" if trade_date_str == today_str else "tick_data"
            
            # 1. 获取 Tick 聚合数据
            async with self.ch_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(f"""
                        SELECT 
                            count() as tick_count,
                            sum(volume) as total_volume,
                            argMax(price, tick_time) as last_price,
                            max(tick_time) as last_tick_time
                        FROM {target_table}
                        WHERE ts_code = %(code)s AND trade_date = %(date)s
                    """, {"code": ts_code, "date": trade_date_str})
                    row = await cursor.fetchone()

            if not row or row[0] == 0:
                result.update({"status": "FAIL", "reasons": ["Missing: No Data"], "action": "REPAIR"})
                return result

            tick_count, tick_vol, tick_price, last_tick_t = row
            
            # 2. 尝试获取快照作为基准
            ref_data = await self._fetch_snapshot_ref(ts_code, trade_date_str, session)
            source = "snapshot"
            
            if not ref_data:
                # 降级使用 K 线
                ref_data = await self._fetch_kline_ref(ts_code, trade_date_str)
                source = "kline"
            
            result["source"] = source
            
            if not ref_data:
                # 无任何参考基准，无法进行对账
                logger.warning(f"⚠️ {stock_code} 无对账基准记录")
                return result

            # 3. 精准对账
            reasons = []
            
            # 价格对账 (绝对误差 <= 0.1)
            price_diff = abs(float(tick_price) - float(ref_data['close']))
            if price_diff > TickStandards.Precise.PRICE_TOLERANCE:
                reasons.append(f"Price Mismatch: Tick={tick_price} vs Ref={ref_data['close']} (Diff={price_diff:.4f})")
            
            # 成交量对账 (相对误差 <= 0.5%)
            ref_vol = float(ref_data['volume'])
            if ref_vol > 0:
                vol_diff_rate = abs(float(tick_vol) - ref_vol) / ref_vol
                if vol_diff_rate > TickStandards.Precise.VOLUME_TOLERANCE:
                    reasons.append(f"Volume Mismatch: Tick={tick_vol} vs Ref={ref_vol} (Diff={vol_diff_rate:.2%})")
            elif float(tick_vol) > 0:
                reasons.append(f"Volume Mismatch: Tick={tick_vol} vs Ref=0")

            if reasons:
                result.update({
                    "status": "FAIL",
                    "reasons": reasons,
                    "action": "REPAIR"
                })
            
            return result

        except Exception as e:
            logger.error(f"Validation failed for {stock_code}: {e}")
            result.update({"status": "FAIL", "reasons": [str(e)], "action": "REPAIR"})
            return result

    async def _fetch_snapshot_ref(self, code: str, date: str, session: str) -> Optional[dict]:
        """获取快照对账基准"""
        min_time = TickStandards.Precise.SNAPSHOT_MIN_TIME_NOON if session == "noon" else TickStandards.Precise.SNAPSHOT_MIN_TIME_CLOSE
        
        try:
            async with self.ch_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 获取符合时间要求的最后一条快照
                    await cursor.execute("""
                        SELECT total_volume, current_price, snapshot_time
                        FROM stock_data.snapshot_data_distributed
                        WHERE ts_code = %(code)s 
                          AND trade_date = %(date)s
                          AND formatDateTime(snapshot_time, '%%H:%%M:%%S') >= %(min_time)s
                        ORDER BY snapshot_time DESC
                        LIMIT 1
                    """, {"code": code, "date": date, "min_time": min_time})
                    row = await cursor.fetchone()
                    if row:
                        return {"volume": row[0], "close": row[1], "time": row[2]}
            return None
        except Exception as e:
            logger.debug(f"Fetch snapshot ref failed {code}: {e}")
            return None

    async def _fetch_kline_ref(self, code: str, date: str) -> Optional[dict]:
        """获取 K 线对账基准"""
        try:
            async with self.ch_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("""
                        SELECT volume, close_price
                        FROM stock_data.stock_kline_daily
                        WHERE ts_code = %(code)s AND trade_date = %(date)s
                    """, {"code": code, "date": date})
                    row = await cursor.fetchone()
                    if row:
                        return {"volume": row[0], "close": row[1]}
            return None
        except Exception as e:
            logger.debug(f"Fetch kline ref failed {code}: {e}")
            return None

    def validate_canary(self, ts_code: str, data: list, trade_date: Optional[str] = None) -> None:
        """金丝雀校验"""
        if data:
            return
        if ts_code in self.CANARY_STOCKS:
             raise ValueError(f"CRITICAL: Empty data for canary stock {ts_code}")
