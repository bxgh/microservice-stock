import datetime
from typing import List, Dict, Any, Optional
from app.utils.database import db
from app.utils.logger import get_logger

logger = get_logger("gateway.market_service")

class MarketService:
    """市场行情纵览服务 (ADS L1)"""

    def _map_row(self, row: tuple) -> Dict[str, Any]:
        """将数据库行映射为字典"""
        return {
            "trade_date": str(row[0]),
            "indices": {
                "sh": {"close": float(row[1]) if row[1] else None, "pct": float(row[2]) if row[2] else None},
                "sz": {"close": float(row[3]) if row[3] else None, "pct": float(row[4]) if row[4] else None},
                "cyb": {"close": float(row[5]) if row[5] else None, "pct": float(row[6]) if row[6] else None},
                "kc50": {"close": float(row[7]) if row[7] else None, "pct": float(row[8]) if row[8] else None},
                "bz50": {"close": float(row[9]) if row[9] else None, "pct": float(row[10]) if row[10] else None},
                "hs300": {"close": float(row[11]) if row[11] else None, "pct": float(row[12]) if row[12] else None},
                "zz500": {"close": float(row[13]) if row[13] else None, "pct": float(row[14]) if row[14] else None},
                "zz1000": {"close": float(row[15]) if row[15] else None, "pct": float(row[16]) if row[16] else None},
                "zz2000": {"close": float(row[17]) if row[17] else None, "pct": float(row[18]) if row[18] else None},
                "winda": {"close": float(row[19]) if row[19] else None, "pct": float(row[20]) if row[20] else None},
            },
            "liquidity": {
                "turnover_total": float(row[21]) if row[21] else None,
                "turnover_ma5": float(row[22]) if row[22] else None,
                "turnover_ma20": float(row[23]) if row[23] else None,
                "turnover_pct_vs_ma20": float(row[24]) if row[24] else None,
                "turnover_pctile_1y": float(row[25]) if row[25] else None,
            },
            "sentiment": {
                "up_count": row[26],
                "down_count": row[27],
                "flat_count": row[28],
                "up_down_ratio": float(row[29]) if row[29] else None,
                "limit_up_count": row[30],
                "limit_down_count": row[31],
                "blast_count": row[32],
                "lian_count": row[33],
                "max_board_height": row[34],
                "high_60d_count": row[35],
                "low_60d_count": row[36],
                "market_breadth": float(row[37]) if row[37] else None,
                "market_regime": row[38],
            },
            "compute_version": row[39],
            "updated_at": str(row[41])
        }

    async def get_latest_overview(self) -> Optional[Dict[str, Any]]:
        """获取最新的市场概览"""
        try:
            sql = "SELECT * FROM ads_l1_market_overview ORDER BY trade_date DESC LIMIT 1"
            rows = await db.execute(sql)
            if rows:
                return self._map_row(rows[0])
            return None
        except Exception as e:
            logger.error(f"获取最新市场概览失败: {e}")
            return None

    async def get_overview_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取市场概览历史"""
        try:
            sql = "SELECT * FROM ads_l1_market_overview ORDER BY trade_date DESC LIMIT %s"
            rows = await db.execute(sql, (limit,))
            return [self._map_row(row) for row in rows]
        except Exception as e:
            logger.error(f"获取市场概览历史失败: {e}")
            return []

market_service = MarketService()
