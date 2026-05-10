import asyncio
import json
import httpx
from datetime import date, datetime
from typing import List, Dict, Any, Optional
from app.utils.database import db
from app.utils.logger import get_logger
from app.config import settings

logger = get_logger("stock-manager.healer")

class HealerService:
    def __init__(self):
        self.tushare_url = settings.TUSHARE_API_URL
        self.akshare_url = settings.AKSHARE_API_URL
        self.mootdx_url = settings.MOOTDX_API_URL

    async def scan_and_repair(self, limit: int = 10) -> Dict[str, Any]:
        """扫描 dq_findings 并触发自动修复"""
        # 1. 查找待修复项：ERROR 级别 且 状态为 OPEN 且 包含差异比对建议的记录
        sql = """
            SELECT id, ts_code, trade_date, rule_id, diff_data 
            FROM dq_findings 
            WHERE status = 'OPEN' AND severity IN ('ERROR', 'CRITICAL')
            LIMIT %s
        """
        findings = await db.execute(sql, (limit,))
        
        results = {
            "scanned": len(findings),
            "success": 0,
            "failed": 0,
            "details": []
        }

        for fid, ts_code, t_date, rule_id, diff_data_str in findings:
            try:
                # 尝试修复
                success = await self.repair_finding(fid)
                if success:
                    results["success"] += 1
                else:
                    results["failed"] += 1
            except Exception as e:
                logger.error(f"修复任务 {fid} 异常: {e}")
                results["failed"] += 1
        
        return results

    async def repair_finding(self, finding_id: int) -> bool:
        """执行单项修复"""
        # 1. 获取异常详情
        sql = "SELECT ts_code, trade_date, rule_id, diff_data FROM dq_findings WHERE id = %s"
        res = await db.execute(sql, (finding_id,))
        if not res:
            logger.warning(f"找不异常记录: {finding_id}")
            return False
        
        ts_code, t_date, rule_id, diff_data_json = res[0]
        diff_data = json.loads(diff_data_json) if isinstance(diff_data_json, str) else diff_data_json
        
        # 2. 确定修复建议
        # E200-S1 Scanner 会在 diff_data 中存储 consensus_source
        suggested_source = diff_data.get("consensus_source")
        if not suggested_source:
            # 如果没有明确建议，默认降级策略 (Tushare -> Mootdx -> AkShare)
            suggested_source = "MOOTDX" 
            
        target_table = "stock_kline_daily" 
        
        # 3. 备份快照 (Before)
        before_snapshot = await self._get_record_snapshot(target_table, ts_code, t_date)
        
        # 4. 抓取正确数据
        correct_data = await self._fetch_from_source(suggested_source, ts_code, t_date)
        if not correct_data:
            await self._log_repair_failure(finding_id, ts_code, t_date, target_table, suggested_source, "无法从建议源获取数据")
            return False

        # 5. 执行修复 (Update)
        try:
            await self._update_record(target_table, correct_data)
            after_snapshot = await self._get_record_snapshot(target_table, ts_code, t_date)
            
            # 获取当前 LSN 作为一个基准 (Wait for Stage F)
            base_lsn = await self._get_current_sync_lsn(target_table)
            
            # 6. 等待同步 ACK (Stage F)
            sync_result = await self.wait_for_sync_ack(target_table, base_lsn, timeout=60)
            
            # 7. 记录修复日志
            repair_id = await self._log_repair_success(
                finding_id, ts_code, t_date, target_table, 
                suggested_source, before_snapshot, after_snapshot,
                sync_lsn=sync_result.get("lsn", 0),
                sync_status=sync_result.get("status", "PENDING")
            )
            
            # 8. 更新异常状态
            await db.execute("UPDATE dq_findings SET status = 'RESOLVED' WHERE id = %s", (finding_id,))
            
            # 9. 触发级联失效 (Stage G)
            if sync_result.get("status") in ["ACKED", "ORPHAN"]:
                from app.services.backfill_service import backfill_service
                await backfill_service.invalidate_downstream(ts_code, t_date, target_table, f"HEAL-{finding_id}")
            
            logger.info(f"成功修复异常 {finding_id}: {ts_code}@{t_date} via {suggested_source}, Sync: {sync_result.get('status')}")
            return True
        except Exception as e:
            await self._log_repair_failure(finding_id, ts_code, t_date, target_table, suggested_source, f"更新数据库失败: {str(e)}")
            return False

    async def rollback_repair(self, repair_id: int) -> bool:
        """回滚修复：恢复 before_snapshot"""
        sql = "SELECT table_name, ts_code, trade_date, before_snapshot, status FROM meta_repair_log WHERE id = %s"
        res = await db.execute(sql, (repair_id,))
        if not res:
            return False
        
        table_name, ts_code, t_date, before_json, status = res[0]
        if status != 'SUCCESS':
            logger.warning(f"修复记录状态非 SUCCESS，无法回滚: {repair_id}")
            return False
            
        before_data = json.loads(before_json) if isinstance(before_json, str) else before_json
        if not before_data:
            logger.warning(f"快照为空，无法回滚: {repair_id}")
            return False

        try:
            # 恢复数据
            await self._update_record(table_name, before_data)
            # 更新状态
            await db.execute("UPDATE meta_repair_log SET status = 'ROLLED_BACK' WHERE id = %s", (repair_id,))
            logger.info(f"成功回滚修复 {repair_id}: {ts_code}@{t_date}")
            return True
        except Exception as e:
            logger.error(f"回滚失败 {repair_id}: {e}")
            return False

    async def _get_record_snapshot(self, table: str, ts_code: str, t_date: date) -> Optional[Dict]:
        """获取单条记录的完整快照"""
        # 获取列名
        desc_sql = f"DESC {table}"
        columns_res = await db.execute(desc_sql)
        column_names = [col[0] for col in columns_res]
        
        sql = f"SELECT * FROM {table} WHERE ts_code = %s AND trade_date = %s"
        res = await db.execute(sql, (ts_code, t_date))
        if res:
            # 将 tuple 转换为 dict
            record = res[0]
            result = {}
            for i, val in enumerate(record):
                if isinstance(val, (date, datetime)):
                    result[column_names[i]] = val.isoformat()
                else:
                    result[column_names[i]] = val
            return result
        return None

    async def _fetch_from_source(self, source: str, ts_code: str, t_date: date) -> Optional[Dict]:
        """从指定源抓取单条 K 线"""
        if source == "MOOTDX":
            return await self._fetch_mootdx(ts_code, t_date)
        elif source == "TUSHARE":
            return await self._fetch_tushare(ts_code, t_date)
        elif source == "AKSHARE":
            return await self._fetch_akshare(ts_code, t_date)
        return None

    async def _fetch_mootdx(self, ts_code: str, t_date: date) -> Optional[Dict]:
        try:
            # Mootdx history 接口返回最近 N 条，需要过滤出当天的
            symbol = ts_code.split('.')[0]
            url = f"{self.mootdx_url}/api/v1/history/{symbol}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params={"frequency": "d", "offset": 10})
                if resp.status_code == 200:
                    data = resp.json()
                    target_str = t_date.strftime("%Y-%m-%d")
                    for item in data:
                        # 假设 mootdx 返回 date 字段
                        if item.get("date") == target_str or item.get("datetime", "").startswith(target_str):
                            return {
                                "ts_code": ts_code,
                                "trade_date": t_date,
                                "open": item["open"],
                                "high": item["high"],
                                "low": item["low"],
                                "close": item["close"],
                                "volume": item["volume"],
                                "amount": item.get("amount", 0)
                            }
        except Exception as e:
            logger.error(f"Mootdx 抓取异常: {e}")
        return None

    async def _fetch_tushare(self, ts_code: str, t_date: date) -> Optional[Dict]:
        # 简化版实现，复用 BackfillService 逻辑更好
        try:
            url = f"{self.tushare_url}/api/v1/stock/daily"
            params = {"ts_code": ts_code, "trade_date": t_date.strftime("%Y%m%d")}
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    raw = resp.json().get("data", [])
                    if raw:
                        item = raw[0]
                        return {
                            "ts_code": ts_code,
                            "trade_date": t_date,
                            "open": item["open"],
                            "high": item["high"],
                            "low": item["low"],
                            "close": item["close"],
                            "volume": float(item["vol"]) * 100,
                            "amount": float(item["amount"]) * 1000
                        }
        except Exception as e:
            logger.error(f"Tushare 抓取异常: {e}")
        return None

    async def _fetch_akshare(self, ts_code: str, t_date: date) -> Optional[Dict]:
        # 略
        return None

    async def wait_for_sync_ack(self, table: str, base_lsn: int, timeout: int = 60) -> Dict[str, Any]:
        """等待同步 ACK (Stage F)"""
        start_time = datetime.now()
        logger.info(f"等待同步 ACK: 表={table}, 基准 LSN={base_lsn}, 超时={timeout}s")
        
        while (datetime.now() - start_time).total_seconds() < timeout:
            current_lsn = await self._get_current_sync_lsn(table)
            if current_lsn > base_lsn:
                logger.info(f"收到同步 ACK: 表={table}, 当前 LSN={current_lsn}")
                return {"status": "ACKED", "lsn": current_lsn}
            
            # 每 2 秒检查一次
            await asyncio.sleep(2)
            
        logger.warning(f"同步 ACK 超时 ({timeout}s): 表={table}, 数据判定为 ORPHAN 状态")
        return {"status": "ORPHAN", "lsn": base_lsn}

    async def _get_current_sync_lsn(self, table: str) -> int:
        """从 meta_sync_status 获取当前确认的 LSN"""
        try:
            sql = "SELECT last_commit_lsn FROM meta_sync_status WHERE table_name = %s"
            res = await db.execute(sql, (table,))
            if res:
                return res[0][0]
        except Exception as e:
            logger.error(f"获取 LSN 失败: {e}")
        return 0

    async def _update_record(self, table: str, data: Dict):
        """更新 ODS 记录"""
        # 动态构建 SQL (仅限受控字段以防注入)
        fields = ["open", "high", "low", "close", "volume", "amount"]
        set_clause = ", ".join([f"{f}=%s" for f in fields if f in data])
        values = [data[f] for f in fields if f in data]
        
        sql = f"UPDATE {table} SET {set_clause} WHERE ts_code = %s AND trade_date = %s"
        values.extend([data["ts_code"], data["trade_date"]])
        await db.execute(sql, tuple(values))

    async def _log_repair_success(self, finding_id, ts_code, t_date, table, source, before, after, sync_lsn=0, sync_status="PENDING"):
        # 处理 Decimal 无法序列化的问题
        before_json = self._sanitize_snapshot(before)
        after_snapshot = self._sanitize_snapshot(after)
        
        sql = """
            INSERT INTO meta_repair_log (finding_id, ts_code, trade_date, table_name, source_used, before_snapshot, after_snapshot, status, sync_lsn, sync_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'SUCCESS', %s, %s)
        """
        await db.execute(sql, (finding_id, ts_code, t_date, table, source, json.dumps(before_json), json.dumps(after_snapshot), sync_lsn, sync_status))
        
        # 获取刚才插入的 ID
        res = await db.execute("SELECT LAST_INSERT_ID()")
        return res[0][0] if res else 0

    def _sanitize_snapshot(self, snapshot: Any) -> Any:
        """递归转换 Decimal 为 float 以便 JSON 序列化"""
        from decimal import Decimal
        if isinstance(snapshot, dict):
            return {k: self._sanitize_snapshot(v) for k, v in snapshot.items()}
        elif isinstance(snapshot, list):
            return [self._sanitize_snapshot(i) for i in snapshot]
        elif isinstance(snapshot, Decimal):
            return float(snapshot)
        return snapshot

    async def _log_repair_failure(self, finding_id, ts_code, t_date, table, source, error):
        sql = """
            INSERT INTO meta_repair_log (finding_id, ts_code, trade_date, table_name, source_used, status, error_msg)
            VALUES (%s, %s, %s, %s, %s, 'FAILED', %s)
        """
        await db.execute(sql, (finding_id, ts_code, t_date, table, source, error))

healer_service = HealerService()
