import datetime
from typing import Dict, Any
from app.utils.database import db
from app.utils.logger import get_logger

logger = get_logger("stock-manager.baseline")

class BaselineService:
    """标的基线服务"""
    
    async def get_current_baseline(self) -> Dict[str, Any]:
        """获取当前全市场基线总数"""
        sql = "SELECT market, count(*) as count FROM stock_basic_info WHERE list_status='L' GROUP BY market"
        rows = await db.execute(sql)
        
        markets = []
        total = 0
        market_name_map = {"主板": "沪市A股", "创业板": "创业板", "北交所": "北交所", "科创板": "科创板"}
        
        for row in rows:
            m = row[0]
            c = int(row[1])
            markets.append({
                "market": m,
                "name": market_name_map.get(m, m.upper()),
                "count": c
            })
            total += c
        
        return {
            "lastUpdated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total": total,
            "markets": markets
        }
