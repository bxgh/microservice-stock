import logging
import datetime
from typing import Dict, Any
from app.common.scheduler_decorators import trading_day_only

logger = logging.getLogger(__name__)

async def _update_readiness(table_name: str, biz_date: str, count: int, status: str = "READY"):
    """更新数据就绪状态"""
    try:
        from app.utils.database import db
        sql = """
            INSERT INTO meta_data_readiness 
            (table_name, biz_date, storage, record_count, expected_min, producer_node, ready_at, status)
            VALUES (%s, %s, 'cloud_mysql', %s, 0, 'cloud', NOW(), %s)
            ON DUPLICATE KEY UPDATE 
                record_count=VALUES(record_count),
                ready_at=VALUES(ready_at),
                status=VALUES(status)
        """
        await db.execute(sql, (table_name, biz_date, count, status))
        logger.info(f"【契约申报】已更新 {table_name} 就绪状态为 {status}")
    except Exception as e:
        logger.error(f"更新就绪状态失败: {e}")


@trading_day_only()
async def daily_suspension_morning_sync_job() -> Dict[str, Any]:
    """每日早盘停牌数据同步任务 (09:15)"""
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
@trading_day_only(check_next=True)
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

@trading_day_only()
async def daily_monitor_data_sync_job() -> Dict[str, Any]:
    """每日收盘后资金面跨服务同步任务 (15:30)"""
    import httpx
    from app.config import settings
    
    try:

        logger.info("【定时任务】开始触发资金面监控数据同步")
        url = f"{settings.MONITOR_SERVICE_URL}/api/v1/sync/daily"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url)
            resp.raise_for_status()
            
            logger.info("【定时任务】资金面监测数据同步请求已送达")
            return {
                'status': 'success',
                'message': '资金面数据同步请求成功触发'
            }
    except Exception as e:
        logger.error(f"【定时任务】触发资金面同步失败: {e}")
        return {
            'status': 'error',
            'message': f'触发失败: {str(e)}'
        }

# 监控指标计算任务 (原 daily_monitor_calculate_job) 已下沉至内网处理

async def weekly_financial_indicators_sync_job() -> Dict[str, Any]:
    """每周全市场财务衍生指标同步任务
    
    遍历 stock_basic_info 中所有在市股票并同步指标
    """
    from app.services.finance_service import FinanceService
    from app.utils.database import db
    from app.scheduler.scheduler import get_scheduler_instance
    import asyncio
    
    job_id = "weekly_finance_indicators_sync"
    scheduler = get_scheduler_instance()
    
    try:
        logger.info("【定时任务】开始执行全市场财务衍生指标同步")
        if scheduler: scheduler.update_job_summary(job_id, "正在获取股票列表...")
        
        # 1. 获取所有在市股票
        sql = "SELECT ts_code FROM stock_basic_info WHERE list_status = 'L'"
        rows = await db.execute(sql)
        stock_codes = [row[0] for row in rows]
        total = len(stock_codes)
        
        logger.info(f"【定时任务】获取到 {total} 只股票需同步指标")
        
        # 2. 循环同步
        finance_service = FinanceService()
        success_count = 0
        error_count = 0
        
        for i, code in enumerate(stock_codes):
            try:
                # 模拟进度上报 (每 50 只上报一次)
                if i % 50 == 0:
                    progress = f"进度: {i}/{total} ({(i/total*100):.1f}%) | 成功: {success_count} | 失败: {error_count}"
                    logger.info(f"【定时任务】财务指标同步进度: {progress}")
                    if scheduler: scheduler.update_job_summary(job_id, progress)
                
                result = await finance_service.sync_financial_indicators(code)
                if result.get("success"):
                    success_count += 1
                else:
                    error_count += 1
                
                # 适当延时，避免 QPS 限制
                if i % 10 == 0:
                    await asyncio.sleep(0.5)
                
            except Exception as e:
                error_count += 1
                logger.error(f"同步股票 {code} 财务指标异常: {e}")
        
        summary = f"同步完成! 总数: {total}, 成功: {success_count}, 失败: {error_count}"
        logger.info(f"【定时任务】全市场财务衍生指标同步结束: {summary}")
        if scheduler: scheduler.update_job_summary(job_id, summary)
        
        return {
            'status': 'success',
            'message': summary,
            'stats': {'total': total, 'success': success_count, 'error': error_count}
        }
        
    except Exception as e:
        error_msg = f"全市场财务指标同步失败: {str(e)}"
        logger.error(f"【定时任务】{error_msg}", exc_info=True)
        if scheduler: scheduler.update_job_summary(job_id, f"错误: {str(e)}")
        return {
            'status': 'error',
            'message': error_msg
        }

@trading_day_only()
async def daily_market_overview_sync_job() -> Dict[str, Any]:
    """每日市场全景数据同步任务 (19:30)
    
    职责: 同步指数、K线、涨跌停池。计算逻辑已迁移至内网。
    """
    try:

        from app.services.market_data_service import MarketDataService
        from app.services.indicator_service import IndicatorService
        from app.utils.database import db

        target_date = datetime.datetime.now().strftime("%Y-%m-%d")
        logger.info(f"【定时任务】启动双源同步流水线: {target_date}")

        market_service = MarketDataService()
        indicator_service = IndicatorService()

        # 1. 指数行情同步 (优先 Tushare)
        sql = "SELECT ts_code FROM index_basic WHERE is_core = 1"
        rows = await db.execute(sql)
        core_indices = [row[0] for row in rows]
        
        index_success = 0
        for code in core_indices:
            count = await market_service.sync_index_daily(ts_code=code, trade_date=target_date)
            if count > 0: index_success += 1
        
        logger.info(f"核心指数同步完成: {index_success}/{len(core_indices)}")

        # 2. 全市场 K 线同步 (优先 Tushare, 失败则触发 BaoStock 异步补齐)
        # 注意：这里我们使用 trade_date 批量同步
        kline_count = await market_service.sync_stock_daily(trade_date=target_date)
        
        if kline_count == -1:
            logger.warning("Tushare 同步失败，已触发 BaoStock 降级流水线，等待异步完成...")
            # 如果是降级模式，后面的广度计算可能会因为数据未就绪而偏差，
            # 但 monitor-service 会在 BaoStock 完成后再次触发计算。
        elif kline_count == 0:
            logger.error("双源同步均未获取到有效 K 线数据")
        else:
            logger.info(f"全市场 K 线同步成功: {kline_count} 条")

        # 4. 同步涨跌停池 (AkShare)
        await market_service.sync_limit_pool(target_date)

        # 5. 同步停复牌记录 (Tushare)
        suspend_count = await market_service.sync_stock_suspend(suspend_date=target_date)
        logger.info(f"全市场停复牌同步完成: {suspend_count} 条")

        # 6. 主动更新就绪状态 (不再进行 L1/L2 计算)
        await _update_readiness("stock_kline_daily", target_date, kline_count)
        
        logger.info(f"【定时任务】采集流程结束: {target_date}")
        return {'status': 'success', 'message': f'采集已完成: {target_date}'}
        
    except Exception as e:
        logger.error(f"【定时任务】同步流水线崩溃: {e}", exc_info=True)
        return {'status': 'error', 'message': str(e)}

@trading_day_only()
async def daily_shareholder_sync_job() -> Dict[str, Any]:
    """每日股东数据同步任务 (Tushare 120积分)"""
    try:

        from app.services.shareholder_service import ShareholderService
        
        today = datetime.datetime.now().strftime("%Y%m%d")
        logger.info(f"【定时任务】开始同步公告日期为 {today} 的股东数据")
        
        service = ShareholderService()
        count = await service.sync_by_ann_date(today)
        
        return {'status': 'success', 'message': f'股东数据同步完成: {count} 个股票有更新'}
    except Exception as e:
        logger.error(f"【定时任务】股东数据同步失败: {e}")
        return {'status': 'error', 'message': str(e)}

@trading_day_only()
async def daily_analyst_rating_sync_job() -> Dict[str, Any]:
    """每日机构评级同步任务 (Tushare 600积分)"""
    try:

        from app.services.information_service import InformationService
        
        today = datetime.datetime.now().strftime("%Y%m%d")
        logger.info(f"【定时任务】开始同步公告日期为 {today} 的机构评级")
        
        service = InformationService()
        count = await service.sync_analyst_ranks_from_tushare(ann_date=today)
        
        return {'status': 'success', 'message': f'机构评级同步完成: {count} 条记录'}
    except Exception as e:
        logger.error(f"【定时任务】机构评级同步失败: {e}")
        return {'status': 'error', 'message': str(e)}
