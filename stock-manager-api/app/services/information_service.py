from typing import List, Dict, Any, Optional
from datetime import datetime
from app.utils.database import db
from app.utils.http_client import http_client
from app.utils.code_utils import normalize_ts_code
from app.utils.logger import get_logger

logger = get_logger("stock-manager.information")


class InformationService:
    """信息维度数据服务"""

    # -------------------------------------------------------------------------
    # 1. 机构评级 (Analyst Rank)
    # -------------------------------------------------------------------------
    async def sync_analyst_ranks(self, data: List[Dict[str, Any]]) -> int:
        if not data:
            return 0

        sql = """
            INSERT INTO stock_analyst_rank
            (ts_code, report_date, analyst, rating, change_direction, target_price)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                rating = VALUES(rating),
                change_direction = VALUES(change_direction),
                target_price = VALUES(target_price),
                created_at = CURRENT_TIMESTAMP
        """

        rows = []
        for item in data:
            # P0: 统一使用 ts_code 并进行归一化
            ts_code = normalize_ts_code(
                item.get("ts_code") or item.get("stock_code"))
            rows.append((
                ts_code,
                item.get("report_date"),
                item.get("analyst"),
                item.get("rating"),
                item.get("change_direction"),
                item.get("target_price")
            ))

        try:
            await db.execute_many(sql, rows)
            logger.info(f"同步机构评级成功: count={len(rows)}")
            return len(rows)
        except Exception as e:
            logger.error(f"同步机构评级失败: {e}")
            raise

    async def get_analyst_ranks(
            self, ts_code: str, limit: int = 50) -> List[Dict[str, Any]]:
        ts_code = normalize_ts_code(ts_code)
        sql = """
            SELECT id, ts_code, report_date, analyst, rating, change_direction, target_price, created_at
            FROM stock_analyst_rank
            WHERE ts_code = %s
            ORDER BY report_date DESC
            LIMIT %s
        """
        rows = await db.execute(sql, (ts_code, limit))
        return [{"id": r[0],
                 "ts_code": r[1],
                 "report_date": r[2],
                 "analyst": r[3],
                 "rating": r[4],
                 "change_direction": r[5],
                 "target_price": float(r[6]) if r[6] else None,
                 "created_at": r[7]} for r in rows]

    # -------------------------------------------------------------------------
    # 2. 业绩预告 (Performance Forecast)
    # -------------------------------------------------------------------------
    async def sync_forecasts(self, data: List[Dict[str, Any]]) -> int:
        if not data:
            return 0

        # P0: 修正表结构不匹配问题 (stock_code -> ts_code)
        sql = """
            INSERT INTO stock_performance_forecast
            (ts_code, notice_date, report_period, type, growth_min, growth_max)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                notice_date = VALUES(notice_date),
                type = VALUES(type),
                growth_min = VALUES(growth_min),
                growth_max = VALUES(growth_max)
        """

        rows = []
        for item in data:
            ts_code = normalize_ts_code(
                item.get("ts_code") or item.get("stock_code"))
            rows.append((
                ts_code,
                item.get("notice_date"),
                item.get("report_period"),
                item.get("type"),
                item.get("growth_min"),
                item.get("growth_max")
            ))

        try:
            await db.execute_many(sql, rows)
            logger.info(f"同步业绩预告成功: count={len(rows)}")
            return len(rows)
        except Exception as e:
            logger.error(f"同步业绩预告失败: {e}")
            raise

    async def get_forecasts(
            self, ts_code: str, limit: int = 20) -> List[Dict[str, Any]]:
        ts_code = normalize_ts_code(ts_code)
        sql = """
            SELECT id, ts_code, notice_date, report_period, type, growth_min, growth_max
            FROM stock_performance_forecast
            WHERE ts_code = %s
            ORDER BY notice_date DESC
            LIMIT %s
        """
        rows = await db.execute(sql, (ts_code, limit))
        return [{"id": r[0],
                 "ts_code": r[1],
                 "notice_date": r[2],
                 "report_period": r[3],
                 "type": r[4],
                 "growth_min": float(r[5]) if r[5] else None,
                 "growth_max": float(r[6]) if r[6] else None} for r in rows]

    # -------------------------------------------------------------------------
    # 3. 市场热度 (Sentiment Daily)
    # -------------------------------------------------------------------------
    async def sync_sentiment(self, data: List[Dict[str, Any]]) -> int:
        if not data:
            return 0

        sql = """
            INSERT INTO stock_sentiment_daily
            (ts_code, trade_date, post_count, read_count, comment_count, rank_score)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                post_count = VALUES(post_count),
                read_count = VALUES(read_count),
                comment_count = VALUES(comment_count),
                rank_score = VALUES(rank_score)
        """

        rows = []
        for item in data:
            ts_code = normalize_ts_code(
                item.get("ts_code") or item.get("stock_code"))
            rows.append((
                ts_code,
                item.get("trade_date"),
                item.get("post_count", 0),
                item.get("read_count", 0),
                item.get("comment_count", 0),
                item.get("rank_score", 0)
            ))

        try:
            await db.execute_many(sql, rows)
            logger.info(f"同步市场热度成功: count={len(rows)}")
            return len(rows)
        except Exception as e:
            logger.error(f"同步市场热度失败: {e}")
            raise

    async def get_sentiment(
            self, ts_code: str, limit: int = 30) -> List[Dict[str, Any]]:
        ts_code = normalize_ts_code(ts_code)
        sql = """
            SELECT id, ts_code, trade_date, post_count, read_count, comment_count, rank_score
            FROM stock_sentiment_daily
            WHERE ts_code = %s
            ORDER BY trade_date DESC
            LIMIT %s
        """
        rows = await db.execute(sql, (ts_code, limit))
        return [{"id": r[0],
                 "ts_code": r[1],
                 "trade_date": r[2],
                 "post_count": r[3],
                 "read_count": r[4],
                 "comment_count": r[5],
                 "rank_score": r[6]} for r in rows]

    # -------------------------------------------------------------------------
    # Orchestration Methods (Fetch from AkShare API -> Save to DB)
    # -------------------------------------------------------------------------

    async def sync_analyst_ranks_from_tushare(
            self, ann_date: Optional[str] = None) -> int:
        """从 Tushare API 获取并同步机构评级 (600积分)"""
        try:
            params = {}
            if ann_date:
                params["ann_date"] = ann_date.replace("-", "")
            else:
                # 默认获取最近一个月的
                from datetime import datetime, timedelta
                params["start_date"] = (
                    datetime.now() -
                    timedelta(
                        days=30)).strftime("%Y%m%d")

            resp = await http_client.get("tushare", "/api/v1/stk_rating", params=params)
            data = resp.get("data", [])
            if not data:
                return 0

            clean_items = []
            for item in data:
                clean_items.append({
                    "ts_code": normalize_ts_code(item.get("ts_code")),
                    "report_date": item.get("ann_date"),
                    "analyst": item.get("org_name"),
                    "rating": item.get("rating"),
                    "change_direction": None,
                    "target_price": None  # stk_rating 不带目标价，需 stk_target 接口
                })

            return await self.sync_analyst_ranks(clean_items)
        except Exception as e:
            logger.error(
                f"Orchestration sync_analyst_ranks_from_tushare failed: {e}")
            return await self.sync_analyst_ranks_from_akshare(ann_date)

    async def sync_analyst_ranks_from_akshare(
            self, report_date: Optional[str] = None) -> int:
        """从 AkShare API 获取并同步机构评级"""
        try:
            params = {}
            if report_date:
                params["date"] = report_date

            data = await http_client.get("akshare", "/api/v1/information/analyst-ranks", params=params)
            if not data:
                return 0

            # 统一洗入 DB 格式
            clean_items = []
            for item in data:
                rpt_date = item.get("report_date")
                if not rpt_date or rpt_date == "":
                    continue

                clean_items.append({
                    "ts_code": normalize_ts_code(item.get("ts_code") or item.get("stock_code")),
                    "report_date": rpt_date,
                    "analyst": item.get("analyst"),
                    "rating": item.get("rating"),
                    "change_direction": item.get("change_direction"),
                    "target_price": item.get("target_price")
                })

            return await self.sync_analyst_ranks(clean_items)
        except Exception as e:
            logger.error(f"Orchestration sync_analyst_ranks failed: {e}")
            raise

    async def sync_forecasts_from_tushare(
            self,
            period: str = None,
            ann_date: str = None) -> int:
        """从 Tushare API 获取并同步业绩预告 (2000积分)"""
        try:
            params = {}
            if period:
                params["period"] = period
            if ann_date:
                params["ann_date"] = ann_date

            # Tushare forecast 要求 ann_date 或 ts_code 必填其一
            if not ann_date and not params.get("ts_code"):
                # 如果没有 ann_date，尝试用今日日期作为默认值，或者由调用方提供
                # 这里为了兼容全量同步，如果只给了 period，可能需要多次调用或改用其他接口
                if not period:
                    from datetime import datetime
                    params["ann_date"] = datetime.now().strftime("%Y%m%d")

            resp = await http_client.get("tushare", "/api/v1/forecast", params=params)
            data = resp.get("data", [])
            if not data:
                return 0

            clean_items = []
            for item in data:
                clean_items.append({
                    "ts_code": normalize_ts_code(item.get("ts_code")),
                    "notice_date": item.get("ann_date"),
                    "report_period": item.get("end_date"),
                    "type": item.get("type"),
                    "growth_min": item.get("p_change_min"),
                    "growth_max": item.get("p_change_max")
                })

            return await self.sync_forecasts(clean_items)
        except Exception as e:
            logger.error(
                f"Orchestration sync_forecasts_from_tushare failed: {e}")
            # Fallback to AkShare if possible
            return await self.sync_forecasts_from_akshare(period)

    async def sync_forecasts_from_akshare(self, period: str) -> int:
        """从 AkShare API 获取并同步业绩预告 (备份数据源)"""
        try:
            params = {"period": period}
            data = await http_client.get("akshare", "/api/v1/forecast", params=params)
            if not data:
                return 0

            clean_items = []
            for item in data:
                # 尝试解析 AkShare 的业绩变动幅度字符串
                growth_min, growth_max = None, None
                range_str = item.get("growth_range", "")

                # 增强正则解析：匹配 百分比 或 数值(万元/亿元)
                try:
                    import re
                    # 匹配所有数字（含负号和小数点）
                    nums = re.findall(
                        r"(-?\d+\.?\d*)",
                        range_str.replace(
                            ",",
                            ""))
                    if "%" in range_str:
                        # 百分比模式：通常最后两个数字是范围
                        if len(nums) >= 2:
                            growth_min, growth_max = float(
                                nums[-2]), float(nums[-1])
                        elif len(nums) == 1:
                            growth_min = float(nums[0])
                    elif "元" in range_str:
                        # 金额模式：由于金额可能很大且包含日期数字，匹配较为复杂
                        # 仅当 nums 长度较多时尝试提取最后的部分
                        if len(nums) >= 2:
                            growth_min, growth_max = float(
                                nums[-2]), float(nums[-1])
                except BaseException:
                    pass

                clean_items.append({
                    "ts_code": normalize_ts_code(item.get("ts_code") or item.get("stock_code")),
                    "notice_date": item.get("notice_date"),
                    "report_period": item.get("report_period"),
                    "type": item.get("type") or "未知",
                    "growth_min": growth_min,
                    "growth_max": growth_max
                })

            return await self.sync_forecasts(clean_items)
        except Exception as e:
            logger.error(
                f"Orchestration sync_forecasts_from_akshare failed: {e}")
            raise

    async def sync_sentiment_from_akshare(self, ts_code: str) -> int:
        """从 AkShare API 获取并同步个股今日热度"""
        try:
            ts_code = normalize_ts_code(ts_code)
            data = await http_client.get("akshare", f"/api/v1/information/sentiment/{ts_code}")
            if not data:
                return 0

            # 获取当前交易日 (简单处理，暂取今日)
            now = datetime.now()
            trade_date = now.strftime("%Y-%m-%d")

            clean_item = {
                "ts_code": ts_code,
                "trade_date": trade_date,
                "post_count": data.get("post_count", 0),
                "read_count": data.get("read_count", 0),
                "comment_count": data.get("comment_count", 0),
                "rank_score": data.get("rank_score", 0)
            }

            return await self.sync_sentiment([clean_item])
        except Exception as e:
            logger.error(
                f"Orchestration sync_sentiment failed: ts_code={ts_code}, {e}")
            raise
