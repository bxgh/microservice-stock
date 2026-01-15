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
        
        # 执行全市场增量同步 (收盘批处理模式)
        await baostock_service.sync_daily_increment()
        
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
        
        # 执行全市场复权因子增量同步 (收盘批处理模式)
        await baostock_service.sync_daily_adjust_increment()
        
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


async def daily_comprehensive_sync_job() -> Dict[str, Any]:
    """全市场每日收盘综合同步流水线 (串行模式)
    
    依次同步 K 线数据和复权因子，包含数据未准备好的重试机制。
    """
    import asyncio
    max_retries = 3
    retry_interval = 30 * 60 # 30分钟重试一次
    
    for attempt in range(max_retries):
        try:
            logger.info(f"【定时任务】启动全市场综合同步流水线 (第 {attempt+1} 次尝试)...")
            
            from app.main import app
            baostock_service = app.state.baostock_service
            
            # 1. 第一阶段：K 线数据
            logger.info(">>> 阶段 1/2: 正在执行逐日 K 线增量补齐...")
            k_res = await baostock_service.sync_daily_increment()
            
            # 检查是否因为数据未发布而中止
            if not k_res.get("success") and k_res.get("error") == "数据源未更新":
                if attempt < max_retries - 1:
                    logger.warning(f"数据提供方尚未发布当日数据，{retry_interval // 60} 分钟后进行第 {attempt+2} 次尝试...")
                    await asyncio.sleep(retry_interval)
                    continue
                else:
                    logger.error("达到最大重试次数，当日数据同步任务遗憾中止")
                    return k_res

            # 2. 第二阶段：复权因子
            logger.info(">>> 阶段 2/2: 正在执行最新复权因子计算与同步...")
            a_res = await baostock_service.sync_daily_adjust_increment()
            
            logger.info("【定时任务】综合流水线全部执行完毕")
            return {
                'status': 'success',
                'message': '每日综合同步成功',
                'details': {
                    'kline': k_res,
                    'adjust': a_res
                }
            }
        except Exception as e:
            logger.error(f"【定时任务】综合流水线尝试 {attempt+1} 出错: {e}", exc_info=True)
            if attempt < max_retries - 1:
                await asyncio.sleep(60) # 崩溃类错误 1 分钟后快速重试
                continue
            return {'status': 'error', 'message': f'流水线崩溃: {str(e)}'}


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
