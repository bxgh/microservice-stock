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
        self.vol_amount_tolerance = 0.001  # 0.1%

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
        tasks = [self._compare_single_stock_with_sem(
            code, date_str, sem) for code in inspection_list]
        results = await asyncio.gather(*tasks)

        # 3. 汇总
        issues = [r for r in results if r is not None]
        logger.info(f"跨源比对完成: 扫描={len(inspection_list)}, 发现问题={len(issues)}")
        return {
            "date": date_str,
            "scanned": len(inspection_list),
            "issues": len(issues)
        }

    async def _compare_single_stock_with_sem(
            self,
            ts_code: str,
            date_str: str,
            sem: asyncio.Semaphore):
        async with sem:
            try:
                return await self.compare_stock(ts_code, date_str)
            except Exception as e:
                logger.error(f"比对失败: {ts_code}, {e}")
                return None

    async def compare_stock(
            self, ts_code: str, date_str: str) -> Optional[Dict[str, Any]]:
        """执行单只股票的跨源比对 (Triple Source Check)"""
        # 1. 获取三个源的数据
        # Source A: Local ODS (Tushare)
        # Source B: Mootdx
        # Source C: AkShare
        source_a = await self._fetch_from_ods(ts_code, date_str)
        if not source_a:
            return None

        # 并发获取外部源
        source_b, source_c = await asyncio.gather(
            self._fetch_from_mootdx(ts_code, date_str),
            self._fetch_from_akshare(ts_code, date_str),
            return_exceptions=True
        )
        
        # 处理异常
        if isinstance(source_b, Exception):
            logger.warning(f"Fetch from Mootdx failed: {source_b}")
            source_b = None
        if isinstance(source_c, Exception):
            logger.warning(f"Fetch from AkShare failed: {source_c}")
            source_c = None

        # 2. 执行三源仲裁逻辑
        arbitration = self._arbitrate_triple(source_a, source_b, source_c)
        
        if not arbitration["has_issue"]:
            return None

        # 3. 记录结果
        await self._log_finding(
            ts_code, 
            date_str, 
            arbitration["severity"], 
            arbitration["description"], 
            arbitration["diff_data"]
        )
        return {"ts_code": ts_code, "severity": arbitration["severity"]}

    def _is_match(self, s1: Optional[Dict], s2: Optional[Dict]) -> bool:
        """判定两个源是否一致"""
        if not s1 or not s2:
            return False
        diffs = self._calculate_diffs(s1, s2)
        return len(diffs) == 0

    def _arbitrate_triple(self, s_a: Dict, s_b: Optional[Dict], s_c: Optional[Dict]) -> Dict:
        """
        三源仲裁核心逻辑 (取二一致)
        """
        res = {
            "has_issue": False,
            "severity": "INFO",
            "description": "",
            "diff_data": {
                "source_a": s_a,
                "source_b": s_b,
                "source_c": s_c,
                "winner": "none"
            }
        }

        # 情况 1: A 与 B 一致 (最常见，数据正确)
        if self._is_match(s_a, s_b):
            # 检查 C 是否也一致 (如果 C 存在)
            if s_c and not self._is_match(s_a, s_c):
                res.update({
                    "has_issue": True,
                    "severity": "WARN",
                    "description": "跨源比对: AkShare 与主源不一致 (A=B!=C)",
                })
                res["diff_data"]["winner"] = "source_a_b"
                return res
            return res # 全部一致或 C 不存在，无问题

        # 情况 2: A 与 C 一致，但 B 不一致
        if self._is_match(s_a, s_c):
            res.update({
                "has_issue": True,
                "severity": "WARN",
                "description": "跨源比对: Mootdx 与主源不一致 (A=C!=B)",
            })
            res["diff_data"]["winner"] = "source_a_c"
            return res

        # 情况 3: B 与 C 一致，但 A (ODS) 不一致 -> 重点关注，ODS 可能有误
        if self._is_match(s_b, s_c):
            res.update({
                "has_issue": True,
                "severity": "ERROR",
                "description": "跨源比对: 本地 ODS 与外部源不一致 (B=C!=A). 建议修复 ODS.",
            })
            res["diff_data"]["winner"] = "source_b_c"
            return res

        # 情况 4: 三者均不一致
        if s_b and s_c:
            res.update({
                "has_issue": True,
                "severity": "ERROR",
                "description": "跨源比对: 三方数据均不一致 (A!=B!=C). 需人工介入.",
            })
            res["diff_data"]["winner"] = "none"
            return res
        
        # 情况 5: 只有一个外部源可用且不一致
        if (s_b and not s_c) or (not s_b and s_c):
            res.update({
                "has_issue": True,
                "severity": "WARN",
                "description": "跨源比对: 外部单源与主源不一致. (由于缺少仲裁源，无法判定胜负)",
            })
            return res

        return res

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
                diffs.append({"field": field, "v1": v1,
                             "v2": v2, "diff": rel_diff})
        # 成交量类字段
        for field in ["volume", "amount"]:
            v1, v2 = s1[field], s2[field]
            if v1 == 0 or v2 == 0:
                continue
            rel_diff = abs(v1 - v2) / v1
            if rel_diff > self.vol_amount_tolerance:
                diffs.append({"field": field, "v1": v1,
                             "v2": v2, "diff": rel_diff})
        return diffs

    async def _fetch_from_ods(
            self, ts_code: str, date_str: str) -> Optional[Dict[str, Any]]:
        """从本地 ODS (Tushare) 获取数据"""
        try:
            sql = "SELECT open, high, low, close, volume, amount FROM stock_kline_daily WHERE ts_code=%s AND trade_date=%s"
            res = await db.execute(sql, (ts_code, date_str))
            if res:
                return {
                    "open": float(res[0][0]), "high": float(res[0][1]),
                    "low": float(res[0][2]), "close": float(res[0][3]),
                    "volume": float(res[0][4]), "amount": float(res[0][5])
                }
            return None
        except Exception as e:
            logger.error(f"Fetch from ODS failed: {e}")
            return None

    async def _fetch_from_mootdx(
            self, ts_code: str, date_str: str) -> Optional[Dict[str, Any]]:
        """从 Mootdx 获取数据"""
        try:
            code = ts_code.split(".")[0]
            # 获取最近的历史记录
            resp = await http_client.get("mootdx", f"/api/v1/history/{code}", 
                                         params={"offset": 10})
            if resp and isinstance(resp, list):
                for item in resp:
                    # 匹配日期
                    item_date = item.get("datetime", "").split(" ")[0]
                    if item_date == date_str:
                        return {
                            "open": float(item["open"]),
                            "high": float(item["high"]),
                            "low": float(item["low"]),
                            "close": float(item["close"]),
                            "volume": float(item.get("vol", 0)) * 100,
                            "amount": float(item["amount"])
                        }
            return None
        except Exception as e:
            logger.error(f"Fetch from Mootdx failed: {e}")
            return None

    async def _fetch_from_akshare(
            self, ts_code: str, date_str: str) -> Optional[Dict[str, Any]]:
        """从 AkShare 获取数据 (仲裁源)"""
        try:
            code = ts_code.split(".")[0]
            # 格式化日期 YYYYMMDD
            d_str = date_str.replace("-", "")
            resp = await http_client.get("akshare", "/api/v1/market/stock/daily",
                                         params={"symbol": code, "start_date": d_str, "end_date": d_str})
            if resp and isinstance(resp, list) and len(resp) > 0:
                item = resp[0]
                return {
                    k: float(
                        item[k]) for k in [
                        "open",
                        "high",
                        "low",
                        "close",
                        "volume",
                        "amount"]}
            return None
        except Exception:
            return None

    async def _log_finding(
            self,
            ts_code: str,
            trade_date: str,
            severity: str,
            msg: str,
            diff_data: Dict):
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
