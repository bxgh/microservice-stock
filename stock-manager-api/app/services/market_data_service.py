import asyncio
import httpx
import bisect
import itertools
import datetime
from datetime import date
from typing import List, Dict, Any, Optional
from app.utils.database import db
from app.utils.code_utils import normalize_ts_code
from app.utils.data_validator import DataValidator
from app.utils.logger import get_logger
from app.config import settings

logger = get_logger("stock-manager.market_data")


class MarketDataService:
    def __init__(self):
        self.tushare_url = settings.TUSHARE_API_URL
        self.akshare_url = settings.AKSHARE_API_URL

    async def sync_index_basic(self, market: str = ''):
        """从 Tushare 同步指数基础信息到 index_basic"""
        try:
            url = f"{self.tushare_url}/api/v1/index/basic"
            params = {"market": market}
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json().get("data", [])

            if not data:
                logger.warning("未获取到指数基础信息")
                return 0

            query = """
                INSERT INTO index_basic (
                    ts_code, name, fullname, market, publisher,
                    index_type, category, base_date, base_point,
                    list_date, weight_rule, description, exp_date
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s
                ) ON DUPLICATE KEY UPDATE
                name=VALUES(name), fullname=VALUES(fullname), market=VALUES(market),
                publisher=VALUES(publisher), index_type=VALUES(index_type),
                category=VALUES(category), base_date=VALUES(base_date),
                base_point=VALUES(base_point), list_date=VALUES(list_date),
                weight_rule=VALUES(weight_rule), description=VALUES(description),
                exp_date=VALUES(exp_date)
            """
            args = []
            for i in data:
                args.append(
                    (i.get("ts_code"),
                     i.get("name"),
                        i.get("fullname"),
                        i.get("market"),
                        i.get("publisher"),
                        i.get("index_type"),
                        i.get("category"),
                        i.get("base_date"),
                        i.get("base_point"),
                        i.get("list_date"),
                        i.get("weight_rule"),
                        i.get("desc"),
                        i.get("exp_date")))

            await db.execute_many(query, args)
            logger.info(f"成功同步指数基础信息: {len(args)} 条")
            return len(args)
        except Exception as e:
            logger.error(f"同步指数基础信息失败: {e}")
            raise

    async def sync_stock_daily(
            self,
            ts_code: str = '',
            trade_date: str = '',
            start_date: str = '',
            end_date: str = ''):
        """同步股票日线行情 (优先 Tushare, 失败则降级至 BaoStock)"""
        if ts_code:
            ts_code = normalize_ts_code(ts_code)
        try:
            # 1. 优先尝试从 Tushare 获取
            logger.info(f"正在通过 Tushare 同步股票日线: {ts_code or trade_date}")
            url = f"{self.tushare_url}/api/v1/stock/daily"
            params = {
                "ts_code": ts_code,
                "trade_date": trade_date.replace("-", ""),
                "start_date": start_date.replace("-", ""),
                "end_date": end_date.replace("-", "")
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json().get("data", [])

            if data:
                # 写入数据库逻辑...
                await self._save_stock_daily_to_db(data)
                logger.info(f"Tushare 同步股票日线完成: {len(data)} 条")

                # P0: 只要有 K 线写入，就必须同步填充当天的复权因子缓存
                # 否则视图 JOIN 会因为缺日期导致当天复权行情为空
                if data:
                    unique_codes = list(
                        set([i.get("ts_code") for i in data if i.get("ts_code")]))
                    dates = [i.get("trade_date")
                             for i in data if i.get("trade_date")]
                    if unique_codes and dates:
                        s_date = f"{min(dates)[:4]}-{min(dates)[4:6]}-{min(dates)[6:8]}"
                        e_date = f"{max(dates)[:4]}-{max(dates)[4:6]}-{max(dates)[6:8]}"
                        await self._refresh_factor_cache(unique_codes, s_date, e_date)

                return len(data)
            else:
                logger.warning(
                    f"Tushare 未返回数据: {
                        ts_code or trade_date}, 准备降级至 BaoStock")
                return await self._sync_stock_daily_baostock_fallback(trade_date)

        except Exception as e:
            logger.error(f"Tushare 同步异常: {e}, 触发 BaoStock 降级机制")
            return await self._sync_stock_daily_baostock_fallback(trade_date)

    async def _save_stock_daily_to_db(self, data: List[Dict[str, Any]]):
        """统一将 Tushare 格式的日线保存到数据库"""
        query = """
            INSERT IGNORE INTO stock_kline_daily (
                ts_code, trade_date, open, high, low, close,
                pre_close, pct_chg, volume, amount
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        args = []
        # 转换日期格式以便校验
        transformed_data = []
        for i in data:
            d = i.get("trade_date")
            dt_str = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
            # 预处理金额和涨跌幅，方便校验
            pct_chg = float(i.get("pct_chg", 0)) / \
                100.0 if i.get("pct_chg") is not None else None
            amount = float(i.get("amount", 0)) * \
                1000.0 if i.get("amount") is not None else None

            transformed_item = {
                **i,
                "trade_date": dt_str,
                "pct_chg": pct_chg,
                "amount": amount,
                "volume": i.get("vol")  # 统一字段名
            }
            transformed_data.append(transformed_item)

        # 执行校验
        passed, rejected = DataValidator.validate_kline_batch(
            transformed_data, "stock_kline_daily")

        if rejected:
            logger.warning(f"发现 {len(rejected)} 条脏数据，已拦截并记录至 staging_rejected")
            await self._log_rejected_data(rejected)

        if not passed:
            return

        for i in passed:
            args.append(
                (i.get("ts_code"),
                 i.get("trade_date"),
                    i.get("open"),
                    i.get("high"),
                    i.get("low"),
                    i.get("close"),
                    i.get("pre_close"),
                    i.get("pct_chg"),
                    i.get("volume"),
                    i.get("amount")))
        await db.execute_many(query, args)

    async def _log_rejected_data(self, rejected: List[Dict[str, Any]]):
        """记录被拒绝的数据到审计表"""
        try:
            query = """
                INSERT INTO staging_rejected (
                    ts_code, trade_date, source_table, raw_data, reject_reason
                ) VALUES (%s, %s, %s, %s, %s)
            """
            args = []
            for r in rejected:
                args.append((
                    r["ts_code"], r["trade_date"], r["source_table"],
                    r["raw_data"], r["reject_reason"]
                ))
            await db.execute_many(query, args)
        except Exception as e:
            logger.error(f"记录拒绝数据失败: {e}")

    async def _sync_stock_daily_baostock_fallback(self, trade_date: str):
        """BaoStock 降级补偿逻辑"""
        try:
            logger.info(f"正在通过 BaoStock 执行降级同步: {trade_date}")
            # 注意: BaoStock 同步是后台异步的，我们触发 remediate
            url = f"{settings.BAOSTOCK_API_URL}/api/v1/sync/remediate"
            params = {
                "date": trade_date,
                "dataType": "kline",
                "scope": "incremental"}
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, params=params)
                resp.raise_for_status()

            # 由于是异步触发，我们无法立即获得计数，返回 -1 表示已触发降级
            logger.info(f"BaoStock 降级同步已触发: {trade_date}")
            return -1
        except Exception as e:
            logger.error(f"BaoStock 降级同步也失败了: {e}")
            raise

    async def sync_adj_factor(
            self,
            ts_code: str = '',
            start_date: str = '',
            end_date: str = ''):
        """同步复权因子 (优先 Tushare)"""
        try:
            logger.info(f"正在从 Tushare 同步复权因子: {ts_code if ts_code else '全市场'}")
            url = f"{self.tushare_url}/api/v1/stock/adj_factor"
            params = {
                "ts_code": ts_code,
                "start_date": start_date.replace("-", ""),
                "end_date": end_date.replace("-", "")
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json().get("data", [])

            if not data:
                return 0

            query = """
                INSERT IGNORE INTO stock_adjust_factor (
                    ts_code, adjust_date, fore_adjust_factor,
                    back_adjust_factor, adjust_factor
                ) VALUES (%s, %s, %s, %s, %s)
            """
            args = []
            for i in data:
                d = i.get("trade_date")
                dt_str = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
                args.append((
                    i.get("ts_code"), dt_str, i.get("adj_factor"),
                    # Tushare 只返回一个 adj_factor
                    i.get("adj_factor"), i.get("adj_factor")
                ))
            await db.execute_many(query, args)
            logger.info(f"成功保存 {len(args)} 条复权因子")

            # 这里不再强制触发，因为 K 线同步时会兜底刷新
            return len(args)
        except Exception as e:
            logger.error(f"同步复权因子失败: {e}")
            raise

    async def _refresh_factor_cache(
            self,
            ts_codes: Any,
            start_date: str,
            end_date: str):
        """增量刷新 ods_stock_factor_daily 缓存表 (MySQL 5.7 兼容版)"""
        try:
            if isinstance(ts_codes, str):
                ts_codes = [ts_codes]

            logger.info(
                f"正在增量刷新复权因子缓存: {
                    len(ts_codes)} 只股票 ({start_date} ~ {end_date})")

            # MySQL 5.7 兼容语法：使用关联子查询寻找最接近的因子记录
            sql = f"""
                INSERT INTO ods_stock_factor_daily (ts_code, trade_date, adjust_factor)
                SELECT
                    f_codes.ts_code,
                    c.cal_date,
                    (SELECT f2.adjust_factor
                     FROM stock_adjust_factor f2
                     WHERE f2.ts_code = f_codes.ts_code
                       AND f2.adjust_date <= c.cal_date
                     ORDER BY f2.adjust_date DESC LIMIT 1) as adjust_factor
                FROM trade_cal c
                CROSS JOIN (
                    SELECT DISTINCT ts_code FROM stock_adjust_factor
                    WHERE ts_code IN ({','.join(['%s'] * len(ts_codes))})
                ) f_codes
                WHERE c.is_open = 1
                  AND c.cal_date BETWEEN %s AND %s
                ON DUPLICATE KEY UPDATE
                    adjust_factor = VALUES(adjust_factor)

            """
            params = ts_codes + [start_date, end_date]
            await db.execute(sql, tuple(params))
            logger.info(f"复权因子缓存刷新完成: {len(ts_codes)} 只股票")
        except Exception as e:
            logger.error(f"刷新复权因子缓存失败: {e}")

    async def sync_index_daily(
            self,
            ts_code: str,
            start_date: str = '',
            end_date: str = '',
            trade_date: str = ''):
        """同步指数日线行情 (优先 Tushare)"""
        ts_code = normalize_ts_code(ts_code)
        try:
            logger.info(f"正在通过 Tushare 同步指数日线: {ts_code}")
            url = f"{self.tushare_url}/api/v1/index/daily"
            params = {
                "ts_code": ts_code,
                "start_date": start_date.replace("-", ""),
                "end_date": end_date.replace("-", ""),
                "trade_date": trade_date.replace("-", "")
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json().get("data", [])

            if data:
                await self._save_index_daily_to_db(data)
                logger.info(f"Tushare 指数同步完成: {ts_code}, {len(data)} 条")
                return len(data)
            else:
                logger.warning(f"Tushare 指数数据为空: {ts_code}")
                # TODO: 以后可增加 AkShare 备用逻辑
                return 0
        except Exception as e:
            logger.error(f"Tushare 指数同步失败: {ts_code}, {e}")
            raise

    async def _save_index_daily_to_db(self, data: List[Dict[str, Any]]):
        """统一保存指数日线"""
        query = """
            INSERT INTO ods_index_daily (
                trade_date, ts_code, open, high, low, close,
                pre_close, `change`, pct_chg, vol, amount
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            open=VALUES(open), high=VALUES(high), low=VALUES(low),
            close=VALUES(close), pre_close=VALUES(pre_close),
            `change`=VALUES(`change`), pct_chg=VALUES(pct_chg),
            vol=VALUES(vol), amount=VALUES(amount)
        """
        args = []
        for i in data:
            d = i.get("trade_date")
            dt_str = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
            pct_chg = float(i.get("pct_chg", 0)) / \
                100.0 if i.get("pct_chg") is not None else None
            args.append(
                (dt_str,
                 i.get("ts_code"),
                    i.get("open"),
                    i.get("high"),
                    i.get("low"),
                    i.get("close"),
                    i.get("pre_close"),
                    i.get("change"),
                    pct_chg,
                    i.get("vol"),
                    float(
                     i.get(
                         "amount",
                         0)) *
                    1000.0 if i.get("amount") is not None else None))
        await db.execute_many(query, args)

    async def sync_market_breadth_daily(self, target_date: str):
        """计算并同步当日市场广度到 ods_market_breadth_daily"""
        try:
            # 1. 基础涨跌家数统计
            sql_agg = """
                SELECT
                    COUNT(*) as count,
                    SUM(CASE WHEN pct_chg > 0 THEN 1 ELSE 0 END) as up_count,
                    SUM(CASE WHEN pct_chg < 0 THEN 1 ELSE 0 END) as down_count,
                    SUM(CASE WHEN pct_chg = 0 THEN 1 ELSE 0 END) as flat_count,
                    SUM(CASE WHEN pct_chg >= 0.05 THEN 1 ELSE 0 END) as up_5pct_count,
                    SUM(CASE WHEN pct_chg <= -0.05 THEN 1 ELSE 0 END) as down_5pct_count,
                    SUM(CASE WHEN pct_chg >= 0.09 THEN 1 ELSE 0 END) as up_9pct_count,
                    SUM(CASE WHEN pct_chg <= -0.09 THEN 1 ELSE 0 END) as down_9pct_count
                FROM stock_kline_daily
                WHERE trade_date = %s
                AND ts_code NOT LIKE '900%%' AND ts_code NOT LIKE '200%%'
            """
            res_agg = await db.execute(sql_agg, (target_date,))
            if not res_agg or not res_agg[0][0]:
                logger.warning(f"当日 {target_date} K线数据不足，无法计算广度")
                return False

            row = res_agg[0]
            curr_count, up_count, down_count, flat_count, up_5pct, down_5pct, up_9pct, down_9pct = row

            # 获取总数 (计算停牌)
            sql_count = """
                SELECT COUNT(*) FROM stock_basic_info
                WHERE list_status = 'L' AND list_date <= DATE_SUB(%s, INTERVAL 60 DAY)
                AND ts_code NOT LIKE '900%%' AND ts_code NOT LIKE '200%%'
            """
            res_total = await db.execute(sql_count, (target_date,))
            total_count = res_total[0][0] if res_total else 0
            suspended_count = max(0, total_count - curr_count)

            # 2. 计算 60/250 日新高新低 (分批处理以节省内存)
            sql_date_250 = "SELECT DISTINCT trade_date FROM stock_kline_daily WHERE trade_date < %s ORDER BY trade_date DESC LIMIT 249, 1"
            res_250 = await db.execute(sql_date_250, (target_date,))
            start_date_250 = res_250[0][0] if res_250 else '1970-01-01'

            sql_date_60 = "SELECT DISTINCT trade_date FROM stock_kline_daily WHERE trade_date < %s ORDER BY trade_date DESC LIMIT 59, 1"
            res_60 = await db.execute(sql_date_60, (target_date,))
            start_date_60 = res_60[0][0] if res_60 else '1970-01-01'

            high_60d, low_60d, high_250d, low_250d = 0, 0, 0, 0

            # 分批获取股票列表进行计算
            sql_all_codes = "SELECT DISTINCT ts_code FROM stock_kline_daily WHERE trade_date = %s"
            codes_res = await db.execute(sql_all_codes, (target_date,))
            all_codes = [r[0] for r in codes_res]

            batch_size = 500
            for i in range(0, len(all_codes), batch_size):
                batch_codes = all_codes[i:i + batch_size]

                # 获取该批次股票的复权因子
                placeholders = ','.join(['%s'] * len(batch_codes))
                sql_f = f"SELECT ts_code, adjust_date, back_adjust_factor FROM stock_adjust_factor WHERE ts_code IN ({placeholders}) ORDER BY ts_code, adjust_date"
                f_res = await db.execute(sql_f, tuple(batch_codes))
                f_map = {}
                for f_code, f_date, f_factor in f_res:
                    if f_code not in f_map:
                        f_map[f_code] = []
                    f_map[f_code].append((f_date, float(f_factor)))

                # 获取该批次股票的 K 线窗口
                sql_k = f"SELECT ts_code, trade_date, close FROM stock_kline_daily WHERE ts_code IN ({placeholders}) AND trade_date >= %s AND trade_date <= %s ORDER BY ts_code, trade_date"
                k_res = await db.execute(sql_k, tuple(batch_codes + [start_date_250, target_date]))

                target_date_obj = datetime.datetime.strptime(
                    target_date, '%Y-%m-%d').date() if isinstance(target_date, str) else target_date
                try:
                    start_date_60_obj = datetime.datetime.strptime(
                        str(start_date_60), '%Y-%m-%d').date()
                except BaseException:
                    start_date_60_obj = start_date_60

                for code, group in itertools.groupby(
                        k_res, key=lambda x: x[0]):
                    rows = list(group)
                    f_list = f_map.get(
                        code, [(datetime.date(1990, 1, 1), 1.0)])
                    f_dates = [x[0] for x in f_list]
                    latest_factor = f_list[-1][1] if f_list else 1.0

                    adj_rows = []
                    for _, t_date, raw_close in rows:
                        idx = bisect.bisect_right(f_dates, t_date) - 1
                        factor = f_list[idx if idx >= 0 else 0][1]
                        # 使用前复权公式: P_adj = P_raw * (F_date / F_latest)
                        adj_p = float(raw_close) * (factor / latest_factor)
                        adj_rows.append({'date': t_date, 'adj_close': adj_p})

                    target_row = next(
                        (r for r in adj_rows if r['date'] == target_date_obj), None)
                    if not target_row:
                        continue
                    curr_p = target_row['adj_close']

                    hist_250 = [r['adj_close']
                                for r in adj_rows if r['date'] < target_date_obj]
                    if hist_250:
                        if curr_p >= max(hist_250):
                            high_250d += 1
                        if curr_p <= min(hist_250):
                            low_250d += 1

                    hist_60 = [r['adj_close'] for r in adj_rows if r['date']
                               < target_date_obj and r['date'] >= start_date_60_obj]
                    if hist_60:
                        if curr_p >= max(hist_60):
                            high_60d += 1
                        if curr_p <= min(hist_60):
                            low_60d += 1

            query = """
                INSERT INTO ods_market_breadth_daily (
                    trade_date, total_count, up_count, down_count, flat_count,
                    suspended_count, up_5pct_count, down_5pct_count,
                    up_9pct_count, down_9pct_count, high_60d_count, low_60d_count,
                    high_250d_count, low_250d_count
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s
                ) ON DUPLICATE KEY UPDATE
                total_count=VALUES(total_count), up_count=VALUES(up_count),
                down_count=VALUES(down_count), flat_count=VALUES(flat_count),
                suspended_count=VALUES(suspended_count), up_5pct_count=VALUES(up_5pct_count),
                down_5pct_count=VALUES(down_5pct_count), up_9pct_count=VALUES(up_9pct_count),
                down_9pct_count=VALUES(down_9pct_count), high_60d_count=VALUES(high_60d_count),
                low_60d_count=VALUES(low_60d_count), high_250d_count=VALUES(high_250d_count),
                low_250d_count=VALUES(low_250d_count)
            """
            await db.execute(query, (
                target_date, total_count, up_count, down_count, flat_count,
                suspended_count, up_5pct, down_5pct,
                up_9pct, down_9pct, high_60d, low_60d,
                high_250d, low_250d
            ))
            return True
        except Exception as e:
            logger.error(f"同步市场广度失败: {target_date}, {e}")
            raise

    async def sync_limit_pool(self, target_date: str):
        """从 AkShare 同步涨跌停池到 ods_event_limit_pool"""
        try:
            pools = ['zt', 'dt', 'zb', 'lian']
            total_synced = 0

            for pool_type in pools:
                url = f"{self.akshare_url}/api/v1/market/limit_pool"
                params = {"date": target_date, "pool_type": pool_type}
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(url, params=params)
                    resp.raise_for_status()
                    data = resp.json()

                if not data:
                    continue

                query = """
                    INSERT INTO ods_event_limit_pool (
                        trade_date, ts_code, name, pool_type, close, pct_chg,
                        amount, circ_mv, turnover_rate, first_limit_time,
                        last_limit_time, board_height, seal_money, seal_count,
                        open_times, industry
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s
                    ) ON DUPLICATE KEY UPDATE
                    name=VALUES(name), close=VALUES(close), pct_chg=VALUES(pct_chg),
                    amount=VALUES(amount), circ_mv=VALUES(circ_mv),
                    turnover_rate=VALUES(turnover_rate), board_height=VALUES(board_height),
                    seal_money=VALUES(seal_money)
                """
                args = []
                for i in data:
                    # P0: 使用归一化工具
                    ts_code = normalize_ts_code(
                        i.get("code") or i.get("ts_code"))

                    args.append(
                        (target_date,
                         ts_code,
                         i.get("name"),
                            pool_type,
                            i.get("close"),
                            i.get("pct_chg"),
                            i.get("amount"),
                            i.get("circ_mv"),
                            i.get("turnover_rate"),
                            i.get("first_limit_time"),
                            i.get("last_limit_time"),
                            i.get("board_height"),
                            i.get("seal_money"),
                            i.get("seal_count"),
                            i.get("open_times"),
                            i.get("industry")))

                await db.execute_many(query, args)
                total_synced += len(args)
                logger.info(f"同步涨跌停池 [{pool_type}]: {len(args)} 条")

            return total_synced
        except Exception as e:
            logger.error(f"同步涨跌停池失败: {target_date}, {e}")
            raise

    async def sync_stock_suspend(
            self,
            suspend_date: str = '',
            resume_date: str = '',
            start_date: str = '',
            end_date: str = ''):
        """从 Tushare 同步股票停复牌记录到 dim_stock_suspend"""
        try:
            logger.info(
                f"正在从 Tushare 同步停复牌记录: start={start_date}, end={end_date}, date={suspend_date}")
            url = f"{self.tushare_url}/api/v1/suspend_d"
            params = {}
            if suspend_date:
                params["suspend_date"] = suspend_date.replace("-", "")
            if resume_date:
                params["resume_date"] = resume_date.replace("-", "")
            if start_date:
                params["start_date"] = start_date.replace("-", "")
            if end_date:
                params["end_date"] = end_date.replace("-", "")

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json().get("data", [])

            if not data:
                logger.info("未获取到任何停复牌记录")
                return 0

            query = """
                INSERT IGNORE INTO dim_stock_suspend (
                    ts_code, suspend_date, suspend_timing, suspend_type
                ) VALUES (%s, %s, %s, %s)
            """
            args = []
            for i in data:
                d = i.get("trade_date") or i.get("suspend_date")
                if not d:
                    continue
                dt_str = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
                ts_code = normalize_ts_code(i.get("ts_code"))
                args.append(
                    (ts_code,
                     dt_str,
                     i.get("suspend_timing"),
                        i.get("suspend_type")))

            if args:
                await db.execute_many(query, args)
                logger.info(f"成功同步停复牌记录: {len(args)} 条")
            return len(args)
        except Exception as e:
            logger.error(f"同步停复牌记录失败: {e}")
            raise
