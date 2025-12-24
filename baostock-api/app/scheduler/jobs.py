"""
定时任务定义
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def daily_kline_sync_job() -> Dict[str, Any]:
    """每日K线数据增量同步任务
    
    每日 18:30 执行，同步当天收盘数据
    
    Returns:
        执行结果信息
    """
    try:
        logger.info("【定时任务】开始执行每日K线数据同步")
        
        # 导入必要的模块（延迟导入避免循环依赖）
        from app.main import app
        
        baostock_service = app.state.baostock_service
        
        # 执行全市场增量同步（start_date 设为较早日期，增量逻辑会自动处理）
        await baostock_service.sync_all_stocks_kline(start_date="2024-01-01")
        
        logger.info("【定时任务】每日K线数据同步完成")
        return {
            'status': 'success',
            'message': '每日K线数据同步成功'
        }
        
    except Exception as e:
        logger.error(f"【定时任务】每日K线数据同步失败: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': f'K线同步失败: {str(e)}'
        }


async def daily_adjust_factor_sync_job() -> Dict[str, Any]:
    """每日复权因子同步任务
    
    每日 19:00 执行，同步当天的复权因子数据
    
    Returns:
        执行结果信息
    """
    try:
        logger.info("【定时任务】开始执行每日复权因子同步")
        
        from app.main import app
        
        baostock_service = app.state.baostock_service
        
        # 执行全市场复权因子增量同步
        await baostock_service.sync_all_stocks_adjust_factor(start_date="1990-01-01")
        
        logger.info("【定时任务】每日复权因子同步完成")
        return {
            'status': 'success',
            'message': '每日复权因子同步成功'
        }
        
    except Exception as e:
        logger.error(f"【定时任务】每日复权因子同步失败: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': f'复权因子同步失败: {str(e)}'
        }


async def health_check_job() -> Dict[str, Any]:
    """系统健康检查任务
    
    每小时执行，检查系统健康状况
    
    Returns:
        健康检查结果
    """
    try:
        logger.debug("【定时任务】执行系统健康检查")
        
        from app.main import app
        from app.utils.database import db
        
        health_status = {
            "baostock_service": "ok",
            "database": "ok"
        }
        
        # 检查 BaoStock 服务
        baostock_service = app.state.baostock_service
        if not baostock_service:
            health_status["baostock_service"] = "error"
        
        # 检查数据库连接
        try:
            await db.execute("SELECT 1")
        except Exception as e:
            health_status["database"] = f"error: {str(e)}"
            logger.warning(f"数据库健康检查失败: {e}")
        
        is_healthy = all(status == "ok" for status in health_status.values())
        
        if is_healthy:
            logger.debug("【定时任务】系统健康检查正常")
        else:
            logger.warning(f"【定时任务】系统健康检查发现问题: {health_status}")
        
        return {
            'status': 'success' if is_healthy else 'warning',
            'message': '系统健康检查完成',
            'details': health_status
        }
        
    except Exception as e:
        logger.error(f"【定时任务】健康检查失败: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': f'健康检查失败: {str(e)}'
        }
