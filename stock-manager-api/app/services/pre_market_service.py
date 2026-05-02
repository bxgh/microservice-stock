from datetime import datetime, timedelta
import asyncio
from typing import Dict, Any, List
from app.utils.database import db
from app.utils.http_client import http_client
from app.utils.code_utils import normalize_ts_code
from app.utils.logger import get_logger

logger = get_logger("stock-manager.pre_market")

class PreMarketService:
    """早盘数据服务
    
    负责同步除权除息、新股上市、业绩预告等数据
    """
    
    # P0-3: 移除内联 DDL，已迁移至 /database/migrations/ 管理

    async def sync_company_events(self) -> Dict[str, Any]:
        """08:30 同步除权除息和新股"""
        # await self.create_tables_if_not_exists() # P0-3 移除
        stats = {"xr_count": 0, "new_stock_count": 0}
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        try:
            # --- 1. 同步除权除息 (从 dividend 接口获取最近的) ---
            # 这是一个简化的逻辑：遍历今日的分红配股数据太慢
            # 理想情况：AkShare 若有 "今日除权" 接口最好，否则需要维护全量
            # 暂时策略：不全量同步，仅作为 placeholder, 实际逻辑可能需要更复杂的上游接口支持
            # 由于 AkShare 接口限制，我们暂时跳过大规模同步，记录一条日志
            logger.info("正在执行除权除息检查 (Placeholder)")
            
            # --- 2. 同步新股 (今日上市) ---
            # AkShare: stock_new_gh_em
            # 这里调用 akshare-api 封装的接口 (如果还没封装，需要去 akshare-api 加)
            # 我们先假设在 akshare-api 增加一个 /api/v1/market/new_stocks
            pass 
            
        except Exception as e:
            logger.error(f"早盘事件同步失败: {e}")
            raise
        return stats

    async def sync_daily_performance_forecast(self) -> int:
        """08:45 同步业绩预告 (针对下一报告期)"""
        # 统一使用 InformationService 的 Tushare 同步逻辑
        from app.services.information_service import InformationService
        info_service = InformationService()
        
        now = datetime.now()
        current_year = now.year
        periods = [
            f"{current_year-1}1231", # Tushare 通常使用 YYYYMMDD
            f"{current_year}0331", 
            f"{current_year}0630",
            f"{current_year}0930"
        ]
        
        total_count = 0
        try:
            for period in periods:
                count = await info_service.sync_forecasts_from_tushare(period)
                total_count += count
                    
            logger.info(f"业绩预告同步完成: {total_count} 条")
            return total_count
            
        except Exception as e:
            logger.error(f"业绩预告同步失败: {e}")
            raise
