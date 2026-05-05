import asyncio
import json
import yaml
import os
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.utils.database import db
from app.utils.logger import get_logger
from app.utils.data_validator import DataValidator
from app.utils.alerter import alerter
from app.config import settings

logger = get_logger("stock-manager.backfill")


class BackfillService:
    def __init__(self):
        self.tushare_url = settings.TUSHARE_API_URL
        self.akshare_url = settings.AKSHARE_API_URL
        self.baostock_url = settings.BAOSTOCK_API_URL
        self.lineage_config = self._load_lineage()
        # 熔断计数器: {rule_id: {fail_count: int, last_fail: datetime}}
        self._breaker_stats = {}

    def _load_lineage(self):
        try:
            path = os.path.join(
                os.path.dirname(__file__),
                "../core/lineage.yaml")
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f).get("lineage", {})
        except Exception as e:
            logger.error(f"加载数据血缘配置失败: {e}")
            return {}

    def is_breaker_open(self, rule_id: str) -> bool:
        """检查特定规则是否熔断 (E6)"""
        stats = self._breaker_stats.get(rule_id)
        if not stats:
            return False

        # 如果最近 10 分钟内失败超过 5 次，则熔断
        if stats['fail_count'] >= 5 and (
                datetime.now() - stats['last_fail']).total_seconds() < 600:
            return True

        # 自动恢复：如果超过 10 分钟没有新失败，重置计数
        if (datetime.now() - stats['last_fail']).total_seconds() >= 600:
            self._breaker_stats[rule_id] = {
                'fail_count': 0, 'last_fail': datetime.now()}
            return False

        return False

    def _update_breaker(self, rule_id: str):
        """更新熔断统计"""
        stats = self._breaker_stats.get(
            rule_id, {'fail_count': 0, 'last_fail': datetime.now()})
        # 如果距离上次失败超过 1 小时，重置计数
        if (datetime.now() - stats['last_fail']).total_seconds() > 3600:
            stats['fail_count'] = 1
        else:
            stats['fail_count'] += 1
        stats['last_fail'] = datetime.now()
        self._breaker_stats[rule_id] = stats

        if stats['fail_count'] == 5:
            logger.critical(f"补数服务已触发熔断告警: {rule_id}")
            asyncio.create_task(
                alerter.alert(
                    "CRITICAL", "补数服务熔断", {
                        "rule_id": rule_id, "fail_count": 5}))

    async def enqueue_findings(self):
        """将发现的问题记录入补数队列"""
        try:
            # 1. 筛选 OPEN 状态且严重级别高的记录
            # 2. 识别沪深 300 标的
            hs300_placeholder = "('600519.SH', '000001.SZ', '000002.SZ')"  # 示例

            sql = f"""
                INSERT IGNORE INTO backfill_queue (ts_code, trade_date, priority, target_table, request_id)
                SELECT
                    ts_code,
                    trade_date,
                    (CASE WHEN ts_code IN {hs300_placeholder} THEN 1 ELSE 2 END) as priority,
                    'stock_kline_daily' as target_table,
                    'ENQUEUE_TASK'
                FROM dq_findings
                WHERE status = 'OPEN' AND severity IN ('CRITICAL', 'ERROR')
                ORDER BY priority ASC, created_at DESC
                LIMIT 1000
            """
            await db.execute(sql)
            logger.info("已完成异常记录入队扫描")
        except Exception as e:
            logger.error(f"入队扫描失败: {e}")

    async def process_queue(self, batch_size: int = 5):
        """执行补数任务"""
        # 1. 检查熔断
        if self.is_breaker_open("general_backfill"):
            logger.warning("补数服务处于熔断状态，跳过本次处理")
            return

        sql_fetch = """
            SELECT id, ts_code, trade_date, target_table, priority, error_count, request_id
            FROM backfill_queue
            WHERE status = 'PENDING'
            ORDER BY priority ASC, id ASC
            LIMIT %s
        """
        tasks = await db.execute(sql_fetch, (batch_size,))
        if not tasks:
            return

        for task_id, ts_code, t_date, table, priority, err_cnt, req_id in tasks:
            # 生成本次执行的 request_id
            exec_req_id = f"BF-{datetime.now().strftime('%m%d%H%M')}-{task_id}"

            # 更新状态为 PROCESSING
            await db.execute("UPDATE backfill_queue SET status='PROCESSING', request_id=%s WHERE id=%s", (exec_req_id, task_id))

            try:
                success = await self._handle_single_backfill(task_id, ts_code, t_date, table, exec_req_id)
                if success:
                    await db.execute("UPDATE backfill_queue SET status='COMPLETED' WHERE id=%s", (task_id,))
                    # 触发级联失效
                    await self.invalidate_downstream(ts_code, t_date, table, exec_req_id)
                else:
                    await self._handle_failure(task_id, err_cnt, "数据抓取或校验失败", exec_req_id)
                    self._update_breaker("general_backfill")
            except Exception as e:
                await self._handle_failure(task_id, err_cnt, str(e), exec_req_id)
                self._update_breaker("general_backfill")

    async def _handle_single_backfill(
            self,
            task_id,
            ts_code,
            t_date,
            table,
            request_id):
        """处理单条补数逻辑"""
        # 1. 备份快照
        before_data = await self._get_current_snapshot(ts_code, t_date, table)

        # 2. 从 P0 源 (Tushare) 抓取数据
        data = await self._fetch_from_tushare(ts_code, t_date)

        # 3. 如果 Tushare 失败，尝试降级 (AkShare)
        if not data:
            logger.warning(
                f"[{request_id}] Tushare 未返回数据，尝试降级至 AkShare: {ts_code}@{t_date}")
            data = await self._fetch_from_akshare(ts_code, t_date)

        if not data:
            return False

        # 4. 校验数据
        passed, rejected = DataValidator.validate_kline_batch(data, table)
        if not passed:
            logger.error(f"[{request_id}] 数据校验未通过: {rejected}")
            return False

        # 5. 幂等写入
        await self._upsert_to_db(table, passed[0])

        # 6. 记录审计
        after_data = passed[0]
        await self._log_audit(ts_code, t_date, table, before_data, after_data, request_id)

        return True

    async def _get_current_snapshot(self, ts_code, t_date, table):
        """获取更新前的快照"""
        sql = f"SELECT * FROM {table} WHERE ts_code = %s AND trade_date = %s"
        res = await db.execute(sql, (ts_code, t_date))
        if res:
            return str(res[0])
        return None

    async def _fetch_from_tushare(self, ts_code, t_date):
        """从 Tushare API 获取数据"""
        try:
            url = f"{self.tushare_url}/api/v1/stock/daily"
            params = {
                "ts_code": ts_code,
                "trade_date": t_date.strftime("%Y%m%d")}
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    raw_data = resp.json().get("data", [])
                    if raw_data:
                        # 转换单位 (千元 -> 元)
                        item = raw_data[0]
                        d = item["trade_date"]
                        return [{
                            "ts_code": item["ts_code"],
                            "trade_date": f"{d[:4]}-{d[4:6]}-{d[6:8]}",
                            "open": item["open"],
                            "high": item["high"],
                            "low": item["low"],
                            "close": item["close"],
                            "pct_chg": float(item["pct_chg"]) / 100.0,
                            "volume": float(item["vol"]) * 100.0,
                            "amount": float(item["amount"]) * 1000.0
                        }]
        except Exception as e:
            logger.error(f"Tushare 抓取失败: {e}")
        return []

    async def _fetch_from_akshare(self, ts_code, t_date):
        """降级至 AkShare 抓取"""
        try:
            url = f"{self.akshare_url}/api/v1/market/stock/daily"
            params = {
                "symbol": ts_code.split(".")[0],
                "start_date": t_date.strftime("%Y%m%d"),
                "end_date": t_date.strftime("%Y%m%d")}
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    return data
        except Exception as e:
            logger.error(f"AkShare 降级抓取失败: {e}")
        return []

    async def _upsert_to_db(self, table, data):
        """幂等写入数据库"""
        sql = f"""
            INSERT INTO {table} (
                ts_code, trade_date, open, high, low, close, pct_chg, volume, amount
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                open=VALUES(open), high=VALUES(high), low=VALUES(low),
                close=VALUES(close), pct_chg=VALUES(pct_chg),
                volume=VALUES(volume), amount=VALUES(amount)
        """
        args = (
            data["ts_code"],
            data["trade_date"],
            data["open"],
            data["high"],
            data["low"],
            data["close"],
            data["pct_chg"],
            data["volume"],
            data["amount"])
        await db.execute(sql, args)

    async def _log_audit(
            self,
            ts_code,
            t_date,
            table,
            before,
            after,
            request_id):
        sql = """
            INSERT INTO backfill_audit (ts_code, trade_date, target_table, before_data, after_data, request_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        await db.execute(sql, (
            ts_code, t_date, table,
            json.dumps(before) if before else None,
            json.dumps(after),
            request_id
        ))

    async def invalidate_downstream(
            self,
            ts_code,
            t_date,
            source_table,
            request_id):
        """根据血缘标记下游指标失效"""
        config = self.lineage_config.get(source_table)
        if not config:
            return

        target_tables = config.get("target_tables", [])
        for table in target_tables:
            sql_del = f"DELETE FROM {table} WHERE ts_code = %s AND trade_date >= %s"
            await db.execute(sql_del, (ts_code, t_date))
            logger.info(
                f"[{request_id}] 已清理下游表数据: {table} | {ts_code} >= {t_date}")

        sql_sig = """
            INSERT INTO recalc_signal (ts_code, start_date, end_date, request_id)
            VALUES (%s, %s, %s, %s)
        """
        end_date = t_date + timedelta(days=250)
        await db.execute(sql_sig, (ts_code, t_date, end_date, request_id))

    async def _handle_failure(
            self,
            task_id,
            current_err_cnt,
            error_msg,
            request_id):
        new_err_cnt = current_err_cnt + 1
        status = 'FAILED' if new_err_cnt >= 3 else 'PENDING'

        sql = "UPDATE backfill_queue SET status=%s, error_count=%s, last_error=%s WHERE id=%s"
        await db.execute(sql, (status, new_err_cnt, error_msg[:500], task_id))

        logger.error(f"[{request_id}] 补数任务失败({new_err_cnt}/3): {error_msg}")

        if new_err_cnt >= 3:
            asyncio.create_task(
                alerter.alert(
                    "CRITICAL", f"补数任务彻底失败: {task_id}", {
                        "ts_code": "unknown", "error": error_msg, "request_id": request_id}))


# 全局服务单例
backfill_service = BackfillService()
