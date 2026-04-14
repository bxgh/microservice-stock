
"""
AkShare API 定时任务定义 (Updated)
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def daily_etf_kline_sync_job() -> Dict[str, Any]:
    """每日ETF K线同步任务
    
    每日 17:30 执行
    """
    try:
        logger.info("【定时任务】开始执行每日ETF K线同步")
        
        from app.services.etf_service import EtfService
        
        service = EtfService()
        result = await service.sync_etf_daily()
        
        logger.info(f"【定时任务】ETF K线同步完成: {result}")
        return {
            'status': 'success',
            'result': result
        }
        
    except Exception as e:
        logger.error(f"【定时任务】ETF K线同步失败: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': str(e)
        }

async def weekly_metadata_sync_job() -> Dict[str, Any]:
    """每周元数据同步任务 (申万行业 + 发行价)
    
    每周六 02:00 执行
    """
    try:
        logger.info("【定时任务】开始执行每周元数据同步")
        
        from app.services.metadata_service import MetadataService
        
        service = MetadataService()
        
        # 1. 行业分类同步
        res_sw = await service.sync_shenwan_industries()
        logger.info(f"申万行业同步结果: {res_sw}")

        # 2. 发行价同步 (补全缺失)
        res_ip = await service.sync_issue_prices()
        logger.info(f"发行价同步结果: {res_ip}")
        
        return {
            'status': 'success',
            'details': {
                'shenwan': res_sw,
                'issue_price': res_ip
            }
        }
    except Exception as e:
        logger.error(f"【定时任务】元数据同步失败: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': str(e)
        }

async def daily_market_data_sync_job() -> Dict[str, Any]:
    """每日市场数据同步 (龙虎榜 + 北向资金)
    
    每日 19:00 执行
    """
    try:
        logger.info("【定时任务】开始执行每日市场数据同步")
        from app.services.akshare_service import AkShareService
        import datetime
        
        service = AkShareService()
        today = datetime.date.today().strftime("%Y%m%d")
        
        # 1. 龙虎榜机构统计
        res_lhb = await service.get_lhb_inst_stats(today)
        logger.info(f"龙虎榜统计同步: {len(res_lhb)} 条")
        
        # 2. 北向资金
        res_north = await service.get_north_funds_daily(today)
        logger.info(f"北向资金同步: {len(res_north)} 条")
        
        return {
            'status': 'success',
            'details': {
                'lhb_count': len(res_lhb),
                'north_count': len(res_north)
            }
        }
    except Exception as e:
        logger.error(f"【定时任务】市场数据同步失败: {e}", exc_info=True)
        return {'status': 'error', 'message': str(e)}

async def daily_sentiment_sync_job() -> Dict[str, Any]:
    """每日情绪数据同步 (热门排行 + 停复牌)
    
    每日 19:30 执行
    """
    try:
        logger.info("【定时任务】开始执行每日情绪数据同步")
        from app.services.akshare_service import AkShareService
        import datetime
        
        service = AkShareService()
        today = datetime.date.today().strftime("%Y%m%d")
        
        # 1. 热门排行 (前50)
        res_hot = await service.get_hot_rank(50)
        logger.info(f"热门排行同步: {len(res_hot)} 条")
        
        # 2. 停复牌信息
        res_susp = await service.get_suspension_daily(today)
        logger.info(f"停复牌信息同步: {len(res_susp)} 条")
        
        return {
            'status': 'success',
            'details': {
                'hot_rank_count': len(res_hot),
                'suspension_count': len(res_susp)
            }
        }
    except Exception as e:
        logger.error(f"【定时任务】情绪数据同步失败: {e}", exc_info=True)
        return {'status': 'error', 'message': str(e)}

async def weekly_stock_list_sync_job() -> Dict[str, Any]:
    """每周全量股票列表同步
    
    每周六 01:00 执行
    """
    try:
        logger.info("【定时任务】开始执行每周股票列表同步")
        from app.services.metadata_service import MetadataService
        
        service = MetadataService()
        res = await service.sync_stock_list()
        
        logger.info(f"股票列表同步完成: {res}")
        return {'status': 'success', 'result': res}
    except Exception as e:
        logger.error(f"【定时任务】股票列表同步失败: {e}", exc_info=True)
        return {'status': 'error', 'message': str(e)}

async def weekly_ths_sector_sync_job() -> Dict[str, Any]:
    """每周同花顺板块同步 (深度模式)
    
    每周六 03:00 执行
    """
    try:
        logger.info("【定时任务】开始执行每周同花顺板块同步")
        from app.services.metadata_service import MetadataService
        
        service = MetadataService()
        # 使用 standard 模式进行深度同步
        await service.sync_ths_industries(mode="standard")
        
        logger.info("同花顺板块同步完成")
        return {'status': 'success', 'message': 'THS Sector Sync Completed'}
    except Exception as e:
        logger.error(f"【定时任务】同花顺板块同步失败: {e}", exc_info=True)
        return {'status': 'error', 'message': str(e)}

async def weekly_restricted_release_job() -> Dict[str, Any]:
    """每周限售股解禁预告同步 (下周)
    
    每周六 04:00 执行
    """
    try:
        logger.info("【定时任务】开始执行限售股解禁预告同步")
        from app.services.akshare_service import AkShareService
        import datetime
        
        service = AkShareService()
        today = datetime.date.today()
        # 获取未来 30 天的解禁信息
        start_date = today.strftime("%Y%m%d")
        end_date = (today + datetime.timedelta(days=30)).strftime("%Y%m%d")
        
        res = await service.get_restricted_release(start_date, end_date)
        
        logger.info(f"限售股解禁同步: {len(res)} 条")
        return {'status': 'success', 'count': len(res)}
    except Exception as e:
        logger.error(f"【定时任务】限售股解禁同步失败: {e}", exc_info=True)
        return {'status': 'error', 'message': str(e)}
