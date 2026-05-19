import sys
import os

# 0. 强制重定向环境路径 (解决 SCF 只读文件系统报错)
# 必须在 import 任何第三方行情库之前设置
os.environ['HOME'] = '/tmp'

import logging
import json
import asyncio

# 1. 强力路径搜索（确保 Layer 挂载被识别）
for path in ['/opt', '/opt/python', '/opt/python/lib/python3.10/site-packages']:
    if os.path.exists(path) and path not in sys.path:
        sys.path.insert(0, path)

# 2. 本地相对路径搜索
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 强制从当前目录加载 .env (优先于本地环境变量)
from dotenv import load_dotenv
load_dotenv(os.path.join(current_dir, '.env'), override=True)

# 初始化日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 引入自定义模块
from shared.collectors.tushare_cl import TushareCollector
from shared.collectors.akshare_cl import AkShareCollector
from shared.collectors.easyquotation_cl import EasyQuotationCollector
from shared.db.dao import StockDAO
from shared.utils.notifier import EmailNotifier
from shared.utils.shadow_auditor import ShadowAuditor
from shared.utils.trading_day import TradingDayGuard
import datetime
import uuid

# 缓存采集器实例
# 缓存采集器实例
try:
    COLLECTORS = {
        'tushare': TushareCollector(),
        'akshare': AkShareCollector(),
        'easyquotation': EasyQuotationCollector()
    }
except Exception as e:
    logger.error(f"Critical: Failed to initialize collectors: {e}")
    COLLECTORS = {}

FALLBACK_CHAIN = ['tushare', 'akshare', 'easyquotation']

from typing import List, Dict, Any

def deduplicate_records(data: List[Dict[str, Any]], has_report_type: bool = True) -> List[Dict[str, Any]]:
    """
    [E13-S4-T3] Python 业务层排重与预清洗逻辑
    针对可能存在的更正公告多条重复记录，按唯一键 (end_date, report_type) 对数据进行分组，
    仅保留公告日期 (ann_date 或 f_ann_date) 最新的那条有效记录。
    """
    if not data:
        return []
    
    groups = {}
    for item in data:
        end_date = item.get('end_date')
        if not end_date:
            continue
        
        # 确定唯一键标识
        if has_report_type:
            report_type = item.get('report_type', '1')
            key = (end_date, report_type)
        else:
            key = end_date
            
        ann_date = str(item.get('ann_date', '') or '')
        f_ann = str(item.get('f_ann_date', '') or '')
        # 优先使用实际披露公告日对比时序，否则使用默认公告日
        compare_date = f_ann if f_ann else ann_date
        
        if key not in groups:
            groups[key] = (compare_date, item)
        else:
            saved_date, _ = groups[key]
            if compare_date > saved_date:
                groups[key] = (compare_date, item)
                
    return [val[1] for val in groups.values()]

async def async_handler(event, context):
    logger.info(f"Received event: {event}")
    # 1. 尝试从 Message 字段解包 (Timer Trigger 专用)
    if 'Message' in event:
        try:
            msg_data = json.loads(event['Message'])
            if isinstance(msg_data, dict):
                event.update(msg_data)
        except Exception as e:
            logger.warning(f"Failed to parse Message field: {e}")

    op = event.get('op', 'collect')
    ts_code = event.get('ts_code', '600519.SH')
    # 如果没传日期，默认为当天 (CST北京时间)
    from zoneinfo import ZoneInfo
    trade_date = event.get('trade_date', datetime.datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y-%m-%d'))
    request_id = getattr(context, 'request_id', 'local_test')

    # [E7-S5-T4] 交易日准入校验
    if await TradingDayGuard.should_skip(op, trade_date):
        return {
            "status": "skipped", 
            "reason": "not_a_trading_day", 
            "op": op, 
            "biz_date": trade_date,
            "request_id": request_id
        }

    if op == 'verify':
        logger.info(f"[{request_id}] Entering Cloud Verification Mode...")
        results = {}
        for name, collector in COLLECTORS.items():
            try:
                # 统一测试 茅台 2026-05-11
                data = await collector.fetch_daily_kline(ts_code, trade_date)
                if data and len(data) > 0:
                    results[name] = f"SUCCESS ({data[0]['close']})"
                else:
                    results[name] = "FAILED (Empty)"
            except Exception as e:
                results[name] = f"ERROR ({str(e)})"
        return {"status": "verify_result", "data": results, "request_id": request_id}

    if op == 'migrate':
        logger.info(f"[{request_id}] Entering Cloud Source Inspection Mode (Disabled)...")
        return {"status": "success", "message": "Migration mode disabled for production"}

    if op == 'shadow_audit':
        # 执行影子审计：对比主源与备份源
        logger.info(f"[{request_id}] Starting shadow audit mission for {trade_date}...")
        auditor = ShadowAuditor()
        try:
            result = await auditor.run_audit(trade_date)
            overlap = result.get('overlap_count', 0)
            # 使用静态方法（与其他分支一致）
            await EmailNotifier.notify_success("数据源影子审计", trade_date, overlap, table_name="meta_data_audit_log")
            return {"status": "success", "audit": result, "request_id": request_id}
        except Exception as e:
            logger.error(f"Shadow audit failed: {e}")
            await EmailNotifier.notify_failure("数据源影子审计", trade_date, str(e))
            return {"status": "error", "message": str(e), "request_id": request_id}

    if op == 'sync_kline_daily':
        # 批量同步全 A 日 K 线并内嵌复权因子
        logger.info(f"[{request_id}] Starting batch K-line sync with embedded factor for {trade_date}...")
        collector = COLLECTORS.get('tushare')
        try:
            # 1. 主动校验今日 09:25 因子同步任务状态
            adj_status = await StockDAO.get_pipeline_status("Adj-Factor", trade_date)
            logger.info(f"[{request_id}] Morning Adj-Factor task status: {adj_status}")
            
            factors_dict = {}
            fallback_triggered = False
            raw_factors = None
            
            # 2. 选择拉取通道
            if adj_status == "success":
                # 【第一层】状态为成功：使用 100% 本地数据库因子极速关联合并 (0.02s)
                logger.info(f"[{request_id}] Morning Adj-Factor task succeeded. Fetching factors from local DB...")
                factors_dict = await StockDAO.get_all_latest_adj_factors()
            else:
                # 【第一层降级】状态为失败或未运行：触发云端实时拉取补货
                logger.warning(f"[{request_id}] Morning Adj-Factor status is '{adj_status}'. Triggering Tushare API fallback...")
                try:
                    raw_factors = await collector.fetch_adj_factor(trade_date)
                    if raw_factors:
                        for item in raw_factors:
                            ts_code = item.get('ts_code')
                            factor = item.get('adj_factor')
                            if ts_code and factor is not None:
                                factors_dict[ts_code] = float(factor)
                        fallback_triggered = True
                        logger.info(f"[{request_id}] Successfully fetched {len(factors_dict)} factors from Tushare in fallback mode.")
                    else:
                        logger.error(f"[{request_id}] Tushare returned empty factors in fallback mode!")
                except Exception as fe:
                    logger.error(f"[{request_id}] Failed to fetch factors from Tushare in fallback mode: {fe}")
            
            # 3. 兜底策略：如果没拿到任何因子，从本地取一次最新的历史因子，防止完全 NULL
            if not factors_dict:
                logger.warning(f"[{request_id}] Factor dict is empty. Loading latest local factors as absolute fallback...")
                factors_dict = await StockDAO.get_all_latest_adj_factors()
            
            # 4. 行情数据采集
            data = await collector.fetch_batch_daily_kline(trade_date)
            if data:
                # 5. 内存合并：将因子内嵌到日 K 线中
                for kline in data:
                    ts_code = kline.ts_code
                    kline.adj_factor = factors_dict.get(ts_code)
                    if kline.adj_factor is None:
                        logger.warning(f"[{request_id}] Stock {ts_code} has no factor for {trade_date}, default to 1.0")
                        kline.adj_factor = 1.0
                
                # 6. 保存并更新状态
                count = await StockDAO.save_kline_data(data)
                await StockDAO.update_data_readiness(trade_date, "stock_kline_daily", len(data))
                await StockDAO.log_pipeline_run("Daily-K-Line", "success", run_id=request_id, biz_date=trade_date)
                
                # 7. 【第二层自愈】后台静默补足事件并更新早晨任务状态为成功
                if fallback_triggered and raw_factors:
                    logger.info(f"[{request_id}] Triggering background self-healing to save factor events...")
                    try:
                        await StockDAO.save_adj_factor(raw_factors)
                        await StockDAO.update_data_readiness(trade_date, "stock_adjust_factor", len(raw_factors))
                        await StockDAO.log_pipeline_run("Adj-Factor", "success", run_id=request_id + "_healed", biz_date=trade_date)
                        logger.info(f"[{request_id}] Background self-healing completed successfully.")
                    except Exception as she:
                        logger.error(f"[{request_id}] Background self-healing failed: {she}")
                
                # 发送成功邮件 (包含表名)
                await EmailNotifier.notify_success("日K线批量合并采集", trade_date, count, table_name="stock_kline_daily")
                return {"status": "success", "count": count, "request_id": request_id}
            else:
                msg = "Tushare returned empty data (possibly non-trading day)."
                logger.info(f"[{request_id}] {msg}")
                return {"status": "empty", "count": 0, "request_id": request_id}
        except Exception as e:
            err_msg = f"Batch K-line sync with factor error: {str(e)}"
            logger.error(f"[{request_id}] {err_msg}")
            await StockDAO.log_pipeline_run("Daily-K-Line", "error", error_message=err_msg, run_id=request_id, biz_date=trade_date)
            
            # 发送失败邮件
            await EmailNotifier.notify_failure("日K线批量合并采集", trade_date, err_msg)
            return {"status": "error", "message": err_msg, "request_id": request_id}

    if op == 'sync_adj_factor':
        # 批量同步复权因子
        logger.info(f"[{request_id}] Starting batch adj factor sync for {trade_date}...")
        collector = COLLECTORS.get('tushare')
        try:
            data = await collector.fetch_adj_factor(trade_date)
            if data:
                count = await StockDAO.save_adj_factor(data)
                await StockDAO.update_data_readiness(trade_date, "stock_adjust_factor", len(data))
                await StockDAO.log_pipeline_run("Adj-Factor", "success", run_id=request_id, biz_date=trade_date)
                
                # 发送成功邮件 (增加表名)
                await EmailNotifier.notify_success("复权因子批量采集", trade_date, count, table_name="stock_adjust_factor")
                
                return {"status": "success", "count": count, "request_id": request_id}
            else:
                return {"status": "empty", "count": 0, "request_id": request_id}
        except Exception as e:
            err_msg = f"Batch adj factor sync error: {str(e)}"
            logger.error(f"[{request_id}] {err_msg}")
            await StockDAO.log_pipeline_run("Adj-Factor", "error", error_message=err_msg, run_id=request_id, biz_date=trade_date)
            
            # 发送失败邮件
            await EmailNotifier.notify_failure("复权因子批量采集", trade_date, err_msg)
            
            return {"status": "error", "message": err_msg, "request_id": request_id}

    if op == 'sync_index_daily':
        # 批量同步指定指数行情
        ts_codes = event.get('ts_codes', '000001.SH,399001.SZ,399006.SZ,000300.SH,000905.SH,000852.SH,985.SH')
        logger.info(f"[{request_id}] Starting index sync for {trade_date}, codes: {ts_codes}...")
        collector = COLLECTORS.get('tushare')
        all_data = []
        for code in ts_codes.split(','):
            try:
                data = await collector.fetch_index_daily(code.strip(), trade_date)
                all_data.extend(data)
            except Exception as e:
                logger.error(f"[{request_id}] Error fetching index {code}: {e}")
        
        if all_data:
            count = await StockDAO.save_index_kline(all_data)
            await StockDAO.update_data_readiness(trade_date, "ods_index_daily", len(all_data))
            await StockDAO.log_pipeline_run("Index-Daily", "success", run_id=request_id, biz_date=trade_date)
            
            # 发送成功邮件
            await EmailNotifier.notify_success("指数K线同步", trade_date, count, table_name="ods_index_daily")
            
            return {"status": "success", "count": count, "request_id": request_id}
        return {"status": "success", "count": 0, "request_id": request_id}

    if op == 'sync_financial_sheets':
        # 增量同步每日新公告的财务三表与指标 (通过获取披露计划后逐个股票同步，规避 Tushare 2000 积分无 ann_date 批量查询权限的限制)
        tushare_date = trade_date.replace('-', '')
        logger.info(f"[{request_id}] Starting incremental financial sheets sync for {trade_date} (Tushare: {tushare_date})...")
        collector = COLLECTORS.get('tushare')
        
        try:
            # 1. 查询当天实际披露报告的上市公司列表
            disclosure_list = await collector.fetch_disclosure_date(actual_date=tushare_date)
            logger.info(f"[{request_id}] Found {len(disclosure_list)} companies disclosing reports on {trade_date}.")
            
            bs_count = 0
            inc_count = 0
            cf_count = 0
            ind_count = 0
            
            # 2. 如果有披露，逐个股票增量同步
            if disclosure_list:
                # 提取去重后的 ts_code 列表
                ts_codes = list(set([item['ts_code'] for item in disclosure_list if item.get('ts_code')]))
                logger.info(f"[{request_id}] Unique stock codes to sync: {len(ts_codes)}")
                
                # 对这批披露的个股，单独拉取最新财务报告
                for idx, code in enumerate(ts_codes):
                    logger.info(f"[{request_id}] [{idx+1}/{len(ts_codes)}] Pulling financial reports for {code}...")
                    
                    try:
                        # (1) 资产负债表 (合并报表)
                        bs_data = await collector.fetch_balancesheet(ts_code=code)
                        bs_clean = deduplicate_records(bs_data, has_report_type=True)
                        if bs_clean:
                            bs_count += await StockDAO.save_balancesheet(bs_clean)
                            
                        # (2) 利润表 (合并报表)
                        inc_data = await collector.fetch_income(ts_code=code)
                        inc_clean = deduplicate_records(inc_data, has_report_type=True)
                        if inc_clean:
                            inc_count += await StockDAO.save_income(inc_clean)
                            
                        # (3) 现金流量表 (合并报表)
                        cf_data = await collector.fetch_cashflow(ts_code=code)
                        cf_clean = deduplicate_records(cf_data, has_report_type=True)
                        if cf_clean:
                            cf_count += await StockDAO.save_cashflow(cf_clean)
                            
                        # (4) 财务指标
                        ind_data = await collector.fetch_fina_indicator(ts_code=code)
                        ind_clean = deduplicate_records(ind_data, has_report_type=False)
                        if ind_clean:
                            ind_count += await StockDAO.save_fina_indicator(ind_clean)
                            
                        # Throttling to prevent Tushare rate limit
                        await asyncio.sleep(0.3)
                        
                    except Exception as e:
                        logger.error(f"[{request_id}] Failed to sync financial data for {code}: {e}")
                        continue
            
            total_saved = bs_count + inc_count + cf_count + ind_count
            logger.info(f"[{request_id}] Incremental financial sheets sync complete. "
                        f"Saved: bs={bs_count}, inc={inc_count}, cf={cf_count}, ind={ind_count}.")
            
            # 更新今日数据就绪性状态
            if total_saved > 0:
                await StockDAO.update_data_readiness(trade_date, "ods_fin_balancesheet", bs_count)
                await StockDAO.update_data_readiness(trade_date, "ods_fin_income", inc_count)
                await StockDAO.update_data_readiness(trade_date, "ods_fin_cashflow", cf_count)
                await StockDAO.update_data_readiness(trade_date, "ods_fin_indicators", ind_count)
            
            await StockDAO.log_pipeline_run("Financial-Sheets", "success", run_id=request_id, biz_date=trade_date)
            
            # 发送成功邮件
            email_body = f"披露公司数: {len(disclosure_list)} | 资产负债表: 保存 {bs_count} 条 | 利润表: 保存 {inc_count} 条 | 现金流量表: 保存 {cf_count} 条 | 关键财务指标: 保存 {ind_count} 条"
            await EmailNotifier.notify_success("每日财务数据采集", trade_date, total_saved, table_name="ods_fin_multiple", extra={"详细进度": email_body})
            
            return {
                "status": "success", 
                "disclosing_count": len(disclosure_list),
                "saved": {"balancesheet": bs_count, "income": inc_count, "cashflow": cf_count, "indicators": ind_count},
                "request_id": request_id
            }
            
        except Exception as e:
            err_msg = f"Incremental financial sheets sync error: {str(e)}"
            logger.error(f"[{request_id}] {err_msg}")
            await StockDAO.log_pipeline_run("Financial-Sheets", "error", error_message=err_msg, run_id=request_id, biz_date=trade_date)
            
            # 发送失败邮件
            await EmailNotifier.notify_failure("每日财务数据采集", trade_date, err_msg)
            
            return {"status": "error", "message": err_msg, "request_id": request_id}

    if op == 'sync_limit_pool':
        logger.info(f"[{request_id}] Starting sync_limit_pool for {trade_date}...")
        collector_ts = COLLECTORS.get('tushare')
        collector_ak = COLLECTORS.get('akshare')
        try:
            # A. 拉取 Tushare 涨跌停池 (包含 zt, dt, lian)
            tushare_raw = await collector_ts.fetch_limit_list(trade_date)
            limit_records = []
            
            for x in tushare_raw:
                limit_type = x.get('limit_type') or x.get('limit')
                pool_type = 'zt' if limit_type == 'U' or '涨停' in str(limit_type) else ('dt' if limit_type == 'D' or '跌停' in str(limit_type) else None)
                if not pool_type:
                    continue
                
                # 构造入库记录
                record = {
                    'trade_date': trade_date,
                    'ts_code': x.get('ts_code'),
                    'name': x.get('name'),
                    'pool_type': pool_type,
                    'close': x.get('close'),
                    'pct_chg': x.get('pct_chg'),
                    'amount': x.get('amount'),
                    'first_limit_time': x.get('first_time'),
                    'last_limit_time': x.get('last_time'),
                    'board_height': x.get('board_height'),
                    'seal_money': x.get('fd_amount'),
                    'open_times': x.get('open_times'),
                    'data_source': 'tushare'
                }
                limit_records.append(record)
                
                # 如果是连板
                bh = x.get('board_height')
                if pool_type == 'zt' and bh and int(bh) >= 2:
                    lian_record = dict(record)
                    lian_record['pool_type'] = 'lian'
                    limit_records.append(lian_record)

            # B. 拉取 AkShare 炸板池
            try:
                zb_data = await collector_ak.fetch_limit_pool(trade_date, 'zb')
                for x in zb_data:
                    record = dict(x)
                    record['trade_date'] = trade_date
                    record['pool_type'] = 'zb'
                    record['data_source'] = 'akshare'
                    limit_records.append(record)
            except Exception as ak_e:
                logger.error(f"[{request_id}] Failed to fetch 'zb' pool from AkShare: {ak_e}")

            if limit_records:
                count = await StockDAO.save_limit_pool(limit_records)
                await StockDAO.update_data_readiness(trade_date, "ods_event_limit_pool", len(limit_records))
                await StockDAO.log_pipeline_run("Limit-Pool", "success", run_id=request_id, biz_date=trade_date)
                
                # 发送成功邮件
                await EmailNotifier.notify_success("每日涨跌停池同步", trade_date, count, table_name="ods_event_limit_pool")
                return {"status": "success", "count": count, "request_id": request_id}
            else:
                return {"status": "empty", "count": 0, "request_id": request_id}
                
        except Exception as e:
            err_msg = f"Limit pool sync error: {str(e)}"
            logger.error(f"[{request_id}] {err_msg}")
            await StockDAO.log_pipeline_run("Limit-Pool", "error", error_message=err_msg, run_id=request_id, biz_date=trade_date)
            await EmailNotifier.notify_failure("每日涨跌停池同步", trade_date, err_msg)
            return {"status": "error", "message": err_msg, "request_id": request_id}

    if op == 'sync_suspend_calendar':
        logger.info(f"[{request_id}] Starting sync_suspend_calendar for {trade_date}...")
        collector_ts = COLLECTORS.get('tushare')
        try:
            suspend_raw = await collector_ts.fetch_suspend_d(trade_date)
            if suspend_raw:
                count = await StockDAO.save_suspend_calendar(suspend_raw)
                await StockDAO.update_data_readiness(trade_date, "stock_suspensions", len(suspend_raw))
                await StockDAO.log_pipeline_run("Suspend-Calendar", "success", run_id=request_id, biz_date=trade_date)
                
                await EmailNotifier.notify_success("每日停复牌同步", trade_date, count, table_name="stock_suspensions")
                return {"status": "success", "count": count, "request_id": request_id}
            else:
                return {"status": "empty", "count": 0, "request_id": request_id}
        except Exception as e:
            err_msg = f"Suspend calendar sync error: {str(e)}"
            logger.error(f"[{request_id}] {err_msg}")
            await StockDAO.log_pipeline_run("Suspend-Calendar", "error", error_message=err_msg, run_id=request_id, biz_date=trade_date)
            await EmailNotifier.notify_failure("每日停复牌同步", trade_date, err_msg)
            return {"status": "error", "message": err_msg, "request_id": request_id}

    if op == 'sync_margin_data':
        logger.info(f"[{request_id}] Starting sync_margin_data with incremental fail-safe for {trade_date}...")
        collector_ts = COLLECTORS.get('tushare')
        try:
            # 1. 查找最大已落库的交易日期
            latest_db_date = await StockDAO.get_latest_margin_date()
            if not latest_db_date:
                # 默认回溯到 7 天前，或者起始日期
                start_date_obj = datetime.datetime.strptime(trade_date, '%Y-%m-%d') - datetime.timedelta(days=7)
                start_date_str = start_date_obj.strftime('%Y-%m-%d')
            else:
                # 从最大已同步日期的次日开始
                start_date_obj = datetime.datetime.strptime(latest_db_date, '%Y-%m-%d') + datetime.timedelta(days=1)
                start_date_str = start_date_obj.strftime('%Y-%m-%d')

            target_date_obj = datetime.datetime.strptime(trade_date, '%Y-%m-%d')
            
            if start_date_obj > target_date_obj:
                logger.info(f"[{request_id}] Margin data is already up-to-date (DB: {latest_db_date}, Target: {trade_date}).")
                return {"status": "success", "message": "already_up_to_date", "request_id": request_id}

            logger.info(f"[{request_id}] Incremental range: {start_date_str} -> {trade_date}")
            
            # 2. 生成所有需要同步的日期列表
            curr_date = start_date_obj
            total_total_saved = 0
            total_detail_saved = 0
            
            while curr_date <= target_date_obj:
                date_str = curr_date.strftime('%Y-%m-%d')
                logger.info(f"[{request_id}] Syncing margin data for date: {date_str}...")
                
                # A. 市场总体数据
                total_data = await collector_ts.fetch_margin(date_str)
                if total_data:
                    saved_total = await StockDAO.save_margin_total(total_data)
                    total_total_saved += saved_total
                
                # B. 个股明细数据
                detail_data = await collector_ts.fetch_margin_detail(date_str)
                if detail_data:
                    saved_detail = await StockDAO.save_margin_detail(detail_data)
                    total_detail_saved += saved_detail
                
                # 间隔 0.5s 流控
                await asyncio.sleep(0.5)
                curr_date += datetime.timedelta(days=1)

            total_saved = total_total_saved + total_detail_saved
            if total_saved > 0:
                await StockDAO.update_data_readiness(trade_date, "ods_margin_total", total_total_saved)
                await StockDAO.update_data_readiness(trade_date, "ods_margin_detail", total_detail_saved)
                await StockDAO.log_pipeline_run("Margin-Data", "success", run_id=request_id, biz_date=trade_date)
                
                await EmailNotifier.notify_success("每日两融信用同步", trade_date, total_saved, table_name="ods_margin_total",
                                                    extra={"市场汇总": total_total_saved, "个股明细": total_detail_saved})
                return {"status": "success", "total_saved": total_total_saved, "detail_saved": total_detail_saved, "request_id": request_id}
            else:
                return {"status": "empty", "count": 0, "request_id": request_id}
                
        except Exception as e:
            err_msg = f"Margin data sync error: {str(e)}"
            logger.error(f"[{request_id}] {err_msg}")
            await StockDAO.log_pipeline_run("Margin-Data", "error", error_message=err_msg, run_id=request_id, biz_date=trade_date)
            await EmailNotifier.notify_failure("每日两融信用同步", trade_date, err_msg)
            return {"status": "error", "message": err_msg, "request_id": request_id}

    if op == 'derive_market_breadth':
        logger.info(f"[{request_id}] Starting derive_market_breadth (local derivation) for {trade_date}...")
        try:
            success = await StockDAO.derive_market_breadth(trade_date)
            if success:
                await StockDAO.update_data_readiness(trade_date, "ods_market_breadth_daily", 1)
                await StockDAO.log_pipeline_run("Market-Breadth", "success", run_id=request_id, biz_date=trade_date)
                
                await EmailNotifier.notify_success("市场广度派生", trade_date, 1, table_name="ods_market_breadth_daily")
                return {"status": "success", "count": 1, "request_id": request_id}
            else:
                return {"status": "failed", "message": "no_kline_data", "request_id": request_id}
        except Exception as e:
            err_msg = f"Market breadth derivation error: {str(e)}"
            logger.error(f"[{request_id}] {err_msg}")
            await StockDAO.log_pipeline_run("Market-Breadth", "error", error_message=err_msg, run_id=request_id, biz_date=trade_date)
            await EmailNotifier.notify_failure("市场广度派生", trade_date, err_msg)
            return {"status": "error", "message": err_msg, "request_id": request_id}

    if op == 'validate_and_failover':
        # 17:00 完整性校验与熔断编排
        logger.info(f"[{request_id}] Starting integrity validation & fail-over for {trade_date}...")
        
        # 1. 加载基准
        snapshot = await StockDAO.get_universe_snapshot(trade_date)
        if not snapshot:
            logger.warning(f"[{request_id}] No baseline snapshot found for {trade_date}. Skipping validation.")
            return {"status": "skipped", "reason": "no_snapshot"}
        
        expected_n = snapshot['expected_count']
        
        # 2. 检查当前已入库量
        current_data = await StockDAO.get_kline_daily(trade_date)
        current_n = len(current_data)
        coverage = current_n / expected_n if expected_n > 0 else 0
        
        logger.info(f"[{request_id}] Initial check: Expected={expected_n}, Actual={current_n}, Coverage={coverage:.2%}")
        
        # 3. 判定与补救逻辑
        source_tag = "TUSHARE_P0"
        
        # 如果覆盖率不足 98%，触发重试或熔断
        if coverage < 0.98:
            if coverage < 0.95:
                logger.warning(f"[{request_id}] Critical coverage gap detected (<95%).")
            else:
                logger.info(f"[{request_id}] Warning coverage gap detected (<98%).")
                
            # A. 原位重试一次 Tushare
            logger.info(f"[{request_id}] Attempting Tushare in-place retry...")
            collector_ts = COLLECTORS.get('tushare')
            try:
                retry_data = await collector_ts.fetch_batch_daily_kline(trade_date)
                if retry_data and len(retry_data) > current_n:
                    await StockDAO.save_kline_data(retry_data)
                    current_data = await StockDAO.get_kline_daily(trade_date)
                    current_n = len(current_data)
                    coverage = current_n / expected_n
                    logger.info(f"[{request_id}] Retry success. New count: {current_n}, Coverage: {coverage:.2%}")
            except Exception as e:
                logger.error(f"[{request_id}] Tushare retry failed: {e}")

            # B. 最终裁定：若重试后仍不足 95%，执行全量接管
            if coverage < 0.95:
                logger.critical(f"[{request_id}] FAIL-OVER TRIGGERED: Switching to AkShare.")
                collector_ak = COLLECTORS.get('akshare')
                try:
                    # 使用全量快照补齐
                    import akshare as ak
                    df_ak = await asyncio.to_thread(ak.stock_zh_a_spot_em)
                    from shared.collectors.akshare_adapter import AkShareAdapter
                    final_ak_models = AkShareAdapter.from_em_spot_records(df_ak.to_dict(orient='records'), trade_date)
                    
                    if final_ak_models:
                        await StockDAO.save_kline_data(final_ak_models)
                        source_tag = "AKSHARE_P1_FAILOVER"
                        logger.info(f"[{request_id}] Fail-over successful. Records saved from AkShare.")
                        await EmailNotifier.notify_failure("Tushare完整性熔断", trade_date, f"已自动切换至AkShare补救。覆盖率:{coverage:.2%}")
                except Exception as e:
                    logger.error(f"[{request_id}] Fail-over execution error: {e}")
                    await EmailNotifier.notify_failure("数据采集全面失效", trade_date, f"主备源均无法满足完整性要求。{str(e)}")

        # 3.5. 【第三层容灾自愈】盘后对账审计与脏数据因子热修补
        logger.info(f"[{request_id}] Executing third-layer factor self-healing audit...")
        repaired = await StockDAO.repair_null_factors(trade_date)
        if repaired > 0:
            logger.info(f"[{request_id}] Third-layer self-healing successfully repaired {repaired} missing factors.")
            # 重新获取当前入库数量，确保后续就绪信号行数准确
            current_data = await StockDAO.get_kline_daily(trade_date)
            current_n = len(current_data)

        # 4. 运行影子审计并同步 source_tag
        from shared.utils.shadow_auditor import ShadowAuditor
        auditor = ShadowAuditor()
        audit_res = await auditor.run_audit(trade_date)
        
        # 覆盖审计日志中的 source_tag
        audit_res['source_tag'] = source_tag
        await StockDAO.save_audit_log(audit_res)
        
        # 5. 更新就绪状态
        # 只要审计判定为 PASS 或 WARNING (非 FAIL)，且已完成补救，则更新信号
        if audit_res['status'] in ['PASS', 'WARNING']:
            await StockDAO.update_data_readiness(trade_date, "stock_kline_daily", current_n)
            
        return {
            "status": "completed",
            "coverage": coverage,
            "source_tag": source_tag,
            "audit_status": audit_res['status'],
            "request_id": request_id
        }

    try:
        preferred_source = event.get('source', 'tushare')
        auto_fallback = event.get('auto_fallback', True)
        
        logger.info(f"[{request_id}] Start collecting {ts_code} for {trade_date}. Preferred: {preferred_source}")
        
        try_sources = [preferred_source]
        if auto_fallback:
            for s in FALLBACK_CHAIN:
                if s != preferred_source:
                    try_sources.append(s)
                    
        final_data = None
        used_src = None

        for src in try_sources:
            collector = COLLECTORS.get(src)
            if not collector: continue
                
            logger.info(f"[{request_id}] Trying source: {src}...")
            try:
                data = await collector.fetch_daily_kline(ts_code, trade_date)
                if data and len(data) > 0:
                    final_data = data
                    used_src = src
                    break
                else:
                    logger.warning(f"[{request_id}] Source {src} returned empty data.")
            except Exception as e:
                logger.error(f"[{request_id}] Source {src} exception: {str(e)}")

        if final_data:
            try:
                await StockDAO.save_kline_data(final_data)
                await StockDAO.update_data_readiness(trade_date, "stock_kline_daily", len(final_data))
                await StockDAO.log_pipeline_run("Data-Hub", "success", run_id=request_id, biz_date=trade_date)
                
                return {
                    "status": "success",
                    "source_used": used_src,
                    "count": len(final_data),
                    "request_id": request_id
                }
            except Exception as db_e:
                err_msg = f"Database error: {str(db_e)}"
                logger.error(f"[{request_id}] {err_msg}")
                await StockDAO.log_pipeline_run("Data-Hub", "error", error_message=err_msg, run_id=request_id, biz_date=trade_date)
                return {"status": "failed", "error": err_msg, "request_id": request_id}
        else:
            err_msg = "All sources failed to fetch data."
            logger.error(f"[{request_id}] {err_msg}")
            await StockDAO.log_pipeline_run("Data-Hub", "error", error_message=err_msg, run_id=request_id, biz_date=trade_date)
            return {"status": "failed", "error": err_msg, "request_id": request_id}
    finally:
        # 核心修复：显式关闭连接池，防止 RuntimeError
        from shared.db.connection import DBManager
        await DBManager.close_pool()

def main_handler(event, context):
    return asyncio.run(async_handler(event, context))
