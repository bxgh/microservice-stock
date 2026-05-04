import asyncio
import datetime
import json
from typing import List, Dict, Any, Optional
from app.utils.database import db
from app.utils.logger import get_logger
from app.utils.http_client import http_client
from app.services.sampling_service import sampling_service
from app.models.dq import DQFindingCreate

logger = get_logger("stock-manager.cross_compare")

class CrossCompareService:
    def __init__(self):
        # 容差设置 (E4-S3)
        self.price_tolerance = 0.0001  # 0.01%
        self.vol_amount_tolerance = 0.001 # 0.1%

    async def run_daily_comparison(self, target_date: datetime.date = None):
        """执行每日跨源比对任务"""
        if not target_date:
            # 默认比对最后一个交易日
            sql = "SELECT cal_date FROM trade_cal WHERE is_open=1 AND cal_date < CURDATE() ORDER BY cal_date DESC LIMIT 1"
            res = await db.execute(sql)
            if not res:
                logger.error("无法获取比对目标日期")
                return
            target_date = res[0][0]
        
        date_str = target_date.strftime("%Y-%m-%d")
        logger.info(f"开始执行跨源比对: 日期={date_str}")
        
        # 1. 获取巡检清单 (E4-S2: 100% HS300 + 1/7 轮转)
        inspection_list = await sampling_service.get_daily_inspection_list(target_date)
        
        # 2. 并发比对 (限制并发以保护 API)
        sem = asyncio.Semaphore(10)
        tasks = [self._compare_single_stock_with_sem(code, date_str, sem) for code in inspection_list]
        results = await asyncio.gather(*tasks)
        
        # 3. 汇总
        issues = [r for r in results if r is not None]
        logger.info(f"跨源比对完成: 扫描={len(inspection_list)}, 发现问题={len(issues)}")
        return {
            "date": date_str,
            "scanned": len(inspection_list),
            "issues": len(issues)
        }

    async def _compare_single_stock_with_sem(self, ts_code: str, date_str: str, sem: asyncio.Semaphore):
        async with sem:
            try:
                return await self.compare_stock(ts_code, date_str)
            except Exception as e:
                logger.error(f"比对失败: {ts_code}, {e}")
                return None

    async def compare_stock(self, ts_code: str, date_str: str) -> Optional[Dict[str, Any]]:
        """执行单只股票的跨源比对 (Triple Source Check)"""
        # 1. 获取源 A (Tushare / Local ODS)
        sql = "SELECT open, high, low, close, volume, amount FROM stock_kline_daily WHERE ts_code=%s AND trade_date=%s"
        res_ods = await db.execute(sql, (ts_code, date_str))
        if not res_ods:
            return None
        
        source_a = {
            "open": float(res_ods[0][0]), "high": float(res_ods[0][1]),
            "low": float(res_ods[0][2]), "close": float(res_ods[0][3]),
            "volume": float(res_ods[0][4]), "amount": float(res_ods[0][5])
        }

        # 2. 获取源 B (BaoStock)
        source_b = await self._fetch_from_baostock(ts_code, date_str)
        
        # 3. 如果 A 和 B 存在显著差异，引入源 C (AkShare) 进行仲裁
        has_diff_ab = self._calculate_diffs(source_a, source_b) if source_b else []
        
        if not has_diff_ab:
            return None

        # 发现差异，引入 AkShare
        source_c = await self._fetch_from_akshare(ts_code, date_str)
        
        # 4. 执行三重比对逻辑
        final_diffs = has_diff_ab
        tie_breaker_msg = ""
        
        if source_c:
            diff_ac = self._calculate_diffs(source_a, source_c)
            diff_bc = self._calculate_diffs(source_b, source_c) if source_b else []
            
            if not diff_bc and diff_ac:
                tie_breaker_msg = " [仲裁: BaoStock 与 AkShare 一致, Tushare 可能有误]"
            elif not diff_ac and diff_bc:
                tie_breaker_msg = " [仲裁: Tushare 与 AkShare 一致, BaoStock 可能有误]"
            elif diff_ac and diff_bc:
                tie_breaker_msg = " [仲裁: 三方数据均不一致, 需人工介入]"

        # 5. 记录结果
        max_diff = max([d["diff"] for d in final_diffs])
        severity = "ERROR" if max_diff > 0.05 else "WARN"
        finding_msg = f"跨源比对差异: {len(final_diffs)} 个字段超限.{tie_breaker_msg}"
        
        await self._log_finding(ts_code, date_str, severity, finding_msg, {
            "source_a": source_a,
            "source_b": source_b,
            "source_c": source_c,
            "diff_details": final_diffs
        })
        return {"ts_code": ts_code, "severity": severity}

    def _calculate_diffs(self, s1: Dict, s2: Dict) -> List[Dict]:
        """计算两个源之间的差异"""
        diffs = []
        # 价格类字段
        for field in ["open", "high", "low", "close"]:
            v1, v2 = s1[field], s2[field]
            if v1 == 0 or v2 == 0:
                continue
            rel_diff = abs(v1 - v2) / v1
            if rel_diff > self.price_tolerance:
                diffs.append({"field": field, "v1": v1, "v2": v2, "diff": rel_diff})
        # 成交量类字段
        for field in ["volume", "amount"]:
            v1, v2 = s1[field], s2[field]
            if v1 == 0 or v2 == 0:
                continue
            rel_diff = abs(v1 - v2) / v1
            if rel_diff > self.vol_amount_tolerance:
                diffs.append({"field": field, "v1": v1, "v2": v2, "diff": rel_diff})
        return diffs

    async def _fetch_from_baostock(self, ts_code: str, date_str: str) -> Optional[Dict[str, Any]]:
        """从 BaoStock 获取数据"""
        try:
            parts = ts_code.split(".")
            bs_code = f"{parts[1].lower()}.{parts[0]}"
            resp = await http_client.get("baostock", f"/api/v1/history/kline/{bs_code}", 
                                       params={"start_date": date_str, "end_date": date_str, "adjust": 3})
            if resp and isinstance(resp, list) and len(resp) > 0:
                item = resp[0]
                return {k: float(item[k]) for k in ["open", "high", "low", "close", "volume", "amount"]}
            return None
        except Exception:
            return None

    async def _fetch_from_akshare(self, ts_code: str, date_str: str) -> Optional[Dict[str, Any]]:
        """从 AkShare 获取数据 (仲裁源)"""
        try:
            code = ts_code.split(".")[0]
            # 格式化日期 YYYYMMDD
            d_str = date_str.replace("-", "")
            resp = await http_client.get("akshare", "/api/v1/market/stock/daily", 
                                       params={"symbol": code, "start_date": d_str, "end_date": d_str})
            if resp and isinstance(resp, list) and len(resp) > 0:
                item = resp[0]
                return {k: float(item[k]) for k in ["open", "high", "low", "close", "volume", "amount"]}
            return None
        except Exception:
            return None

    async def _log_finding(self, ts_code: str, trade_date: str, severity: str, msg: str, diff_data: Dict):
        """落库 dq_findings"""
        try:
            sql = """
                INSERT INTO dq_findings (ts_code, trade_date, rule_id, severity, description, diff_data)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            await db.execute(sql, (
                ts_code, trade_date, "CROSS_SOURCE", severity, msg, json.dumps(diff_data)
            ))
        except Exception as e:
            logger.error(f"Log DQ finding failed: {e}")

cross_compare_service = CrossCompareService()
