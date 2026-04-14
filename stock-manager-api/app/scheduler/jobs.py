"""
定时任务定义 (stock-manager)
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def daily_suspension_morning_sync_job() -> Dict[str, Any]:
    """每日早盘停牌数据同步任务
    
    每日 09:15 执行，从 AkShare 获取当日停牌、复牌信息
    
    Returns:
        执行结果信息
    """
    try:
        logger.info("【定时任务】开始执行每日早盘停牌数据同步")
        
        from app.services.suspension_service import SuspensionService
        
        service = SuspensionService()
        count = await service.sync_today_suspensions()
        
        logger.info(f"【定时任务】早盘停牌数据同步完成，共 {count} 条")
        return {
            'status': 'success',
            'message': f'早盘停牌数据同步成功，更新 {count} 条记录'
        }
        
    except Exception as e:
        logger.error(f"【定时任务】早盘停牌数据同步失败: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': f'早盘停牌同步失败: {str(e)}'
        }
async def daily_performance_forecast_sync_job() -> Dict[str, Any]:
    """每日早盘业绩预告同步任务 (08:45)"""
    try:
        from app.services.pre_market_service import PreMarketService
        service = PreMarketService()
        count = await service.sync_daily_performance_forecast()
        return {'status': 'success', 'message': f'业绩预告同步完成: {count} 条'}
    except Exception as e:
        logger.error(f"业绩预告同步失败: {e}", exc_info=True)
        return {'status': 'error', 'message': str(e)}
