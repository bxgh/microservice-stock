import json
import logging
import datetime
from typing import List, Dict, Any, Optional
from .connection import execute_query

logger = logging.getLogger(__name__)

class StockDAO:
    """
    数据访问对象 - 处理股票采集相关数据库操作
    """

    @staticmethod
    async def save_kline_data(data: List[Any]) -> int:
        """
        批量保存 K 线数据 (幂等插入)
        支持 List[Dict] 或 List[KLineModel]
        """
        if not data:
            return 0

        # 构建批量插入 SQL (包含内嵌复权因子)
        sql = """
        INSERT INTO stock_kline_daily (
            ts_code, trade_date, open, high, low, close, 
            pre_close, pct_chg, volume, amount, adj_factor
        ) VALUES (
            %(ts_code)s, %(trade_date)s, %(open)s, %(high)s, %(low)s, %(close)s, 
            %(pre_close)s, %(pct_chg)s, %(volume)s, %(amount)s, %(adj_factor)s
        ) ON DUPLICATE KEY UPDATE 
            open = VALUES(open), 
            high = VALUES(high), 
            low = VALUES(low), 
            close = VALUES(close), 
            pre_close = VALUES(pre_close), 
            pct_chg = VALUES(pct_chg), 
            volume = VALUES(volume), 
            amount = VALUES(amount),
            adj_factor = VALUES(adj_factor)
        """
        
        count = 0
        for item in data:
            # 兼容 Pydantic 对象 (KLineModel)
            params = item.model_dump() if hasattr(item, 'model_dump') else item
            res = await execute_query(sql, params, is_select=False)
            count += res
        
        logger.info(f"Successfully saved {len(data)} records to stock_kline_daily (affected: {count}).")
        return count

    @classmethod
    async def get_all_latest_adj_factors(cls) -> Dict[str, float]:
        """
        [E3-S1-T2] 获取全市场所有股票的历史最新复权因子 (MySQL 5.7 高性能兼容版)
        返回: {ts_code: adjust_factor} 映射字典
        """
        sql = """
        SELECT a1.ts_code, a1.adjust_factor 
        FROM stock_adjust_factor a1
        JOIN (
            SELECT ts_code, MAX(adjust_date) as max_date 
            FROM stock_adjust_factor 
            GROUP BY ts_code
        ) a2 ON a1.ts_code = a2.ts_code AND a1.adjust_date = a2.max_date
        """
        try:
            rows = await execute_query(sql, is_select=True)
            result = {}
            for r in rows:
                ts_code = r.get('ts_code')
                factor = r.get('adjust_factor')
                if ts_code and factor is not None:
                    result[ts_code] = float(factor)
            logger.info(f"Successfully loaded {len(result)} latest adjust factors from DB.")
            return result
        except Exception as e:
            logger.error(f"Failed to fetch latest adjust factors from DB: {e}")
            return {}

    @classmethod
    async def repair_null_factors(cls, trade_date: str) -> int:
        """
        [E3-S1-T2] 盘后对账审计与脏数据因子热修补 (第三层容灾自愈)
        """
        sql_null_stocks = """
        SELECT ts_code FROM stock_kline_daily 
        WHERE trade_date = %s AND adj_factor IS NULL
        """
        sql_update = """
        UPDATE stock_kline_daily 
        SET adj_factor = %s 
        WHERE trade_date = %s AND ts_code = %s
        """
        try:
            null_rows = await execute_query(sql_null_stocks, (trade_date,), is_select=True)
            if not null_rows:
                return 0
            
            logger.warning(f"Found {len(null_rows)} records with NULL adj_factor for {trade_date}. Repairing...")
            latest_factors = await cls.get_all_latest_adj_factors()
            
            healed_count = 0
            for row in null_rows:
                code = row.get('ts_code')
                if not code:
                    continue
                factor = latest_factors.get(code, 1.0)
                res = await execute_query(sql_update, (factor, trade_date, code), is_select=False)
                healed_count += res
            logger.info(f"Successfully repaired {healed_count} NULL factors for {trade_date}.")
            return healed_count
        except Exception as e:
            logger.error(f"Failed to repair NULL factors for {trade_date}: {e}")
            return 0

    @staticmethod
    async def save_adj_factor(data: List[Dict[str, Any]]) -> int:
        """
        保存复权因子 - 变动检测写入
        仅在因子发生变化时写入，实现变动点存储。
        """
        if not data:
            return 0
        
        sql_select = """
        SELECT adjust_factor FROM stock_adjust_factor
        WHERE ts_code = %s
        ORDER BY adjust_date DESC
        LIMIT 1
        """
        
        sql_insert = """
        INSERT INTO stock_adjust_factor 
            (ts_code, adjust_date, fore_adjust_factor, back_adjust_factor, adjust_factor)
        VALUES (%(ts_code)s, %(trade_date)s, NULL, %(adj_factor)s, %(adj_factor)s)
        """
        
        count = 0
        for item in data:
            ts_code = item.get('ts_code')
            adj_factor = item.get('adj_factor')
            
            # 安全检查：跳过缺失关键字段的数据项
            if not ts_code or adj_factor is None:
                logger.warning(f"Skipping record due to missing ts_code or adj_factor: {item}")
                continue
            
            # 日期转换: 20240510 -> 2024-05-10
            trade_date = item.get('trade_date')
            if trade_date and len(str(trade_date)) == 8:
                 item['trade_date'] = f"{str(trade_date)[:4]}-{str(trade_date)[4:6]}-{str(trade_date)[6:]}"
            
            # 1. 查询库中最新值
            rows = await execute_query(sql_select, (ts_code,), is_select=True)
            latest_factor = rows[0]['adjust_factor'] if rows else None
            
            # 2. 对比 (浮点数阈值 1e-8)
            try:
                # 注意：Tushare 返回的 adj_factor 可能是字符串或数字，需转换
                if latest_factor is not None and abs(float(adj_factor) - float(latest_factor)) < 1e-8:
                    continue
            except (ValueError, TypeError) as e:
                logger.error(f"Data conversion error for {ts_code} on {trade_date}: {e}")
                continue
                
            # 3. 执行插入
            res = await execute_query(sql_insert, item, is_select=False)
            count += res
            
        return count

    @staticmethod
    async def save_industry_members(data: List[Dict[str, Any]]) -> int:
        """保存申万行业成员 (拉链表逻辑)"""
        if not data:
            return 0
        
        sql = """
        INSERT INTO dim_sw_industry_member (
            index_code, index_name, con_code, con_name, in_date, out_date, is_new
        ) VALUES (
            %(index_code)s, %(index_name)s, %(con_code)s, %(con_name)s, %(in_date)s, %(out_date)s, %(is_new)s
        ) ON DUPLICATE KEY UPDATE 
            index_name = VALUES(index_name),
            con_name = VALUES(con_name),
            out_date = VALUES(out_date),
            is_new = VALUES(is_new)
        """
        
        count = 0
        for item in data:
            # 日期转换
            for key in ['in_date', 'out_date']:
                val = item.get(key)
                if val and len(str(val)) == 8:
                    item[key] = f"{str(val)[:4]}-{str(val)[4:6]}-{str(val)[6:]}"
            
            res = await execute_query(sql, item, is_select=False)
            count += res
        return count

    @staticmethod
    async def save_index_kline(data: List[Dict[str, Any]], table_name: str = 'ods_index_daily') -> int:
        """保存指数 K 线数据"""
        if not data:
            return 0
        
        # 允许通过 table_name 切换 ods_index_daily 或 ods_sw_index_daily
        sql = f"""
        INSERT INTO {table_name} (
            ts_code, trade_date, open, high, low, close, 
            pre_close, pct_chg, vol, amount
        ) VALUES (
            %(ts_code)s, %(trade_date)s, %(open)s, %(high)s, %(low)s, %(close)s, 
            %(pre_close)s, %(pct_chg)s, %(volume)s, %(amount)s
        ) ON DUPLICATE KEY UPDATE 
            open = VALUES(open), 
            high = VALUES(high), 
            low = VALUES(low), 
            close = VALUES(close), 
            pre_close = VALUES(pre_close), 
            pct_chg = VALUES(pct_chg), 
            vol = VALUES(vol), 
            amount = VALUES(amount)
        """
        
        count = 0
        for item in data:
            res = await execute_query(sql, item, is_select=False)
            count += res
        return count

    @staticmethod
    async def log_pipeline_run(pipeline_id: str, status: str, error_message: str = None, run_id: str = None, biz_date: str = None) -> int:
        """
        记录任务流水审计 (使用 meta_pipeline_run)
        """
        sql = """
        INSERT INTO meta_pipeline_run (
            run_id, pipeline_id, biz_date, status, error_message, started_at, finished_at
        ) VALUES (
            %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        ) ON DUPLICATE KEY UPDATE 
            status = VALUES(status), 
            error_message = VALUES(error_message), 
            finished_at = CURRENT_TIMESTAMP
        """
        params = (run_id, pipeline_id, biz_date, status, error_message)
        return await execute_query(sql, params, is_select=False)

    @staticmethod
    async def log_pipeline_run_v2(
        pipeline_id: str, 
        status: str, 
        error_message: str = None, 
        run_id: str = None, 
        biz_date: str = None,
        output_summary: Any = None
    ) -> int:
        """
        [E14-S2-P1-T5] 升级版任务流水审计记录，支持 output_summary 结构化 JSON 写入
        """
        import json
        from typing import Any
        
        output_summary_str = None
        if output_summary is not None:
            try:
                if isinstance(output_summary, (dict, list)):
                    output_summary_str = json.dumps(output_summary, ensure_ascii=False)
                else:
                    output_summary_str = str(output_summary)
            except Exception as e:
                # 容错降级
                output_summary_str = json.dumps({"error": f"Serialize failed: {str(e)}"})
                
        sql = """
        INSERT INTO meta_pipeline_run (
            run_id, pipeline_id, biz_date, status, error_message, output_summary, started_at, finished_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        ) ON DUPLICATE KEY UPDATE 
            status = VALUES(status), 
            error_message = VALUES(error_message), 
            output_summary = VALUES(output_summary),
            finished_at = CURRENT_TIMESTAMP
        """
        params = (run_id, pipeline_id, biz_date, status, error_message, output_summary_str)
        return await execute_query(sql, params, is_select=False)


    @staticmethod
    async def get_pipeline_status(pipeline_id: str, biz_date: str) -> Optional[str]:
        """
        [E3-S1-T2] 获取指定任务在特定交易日期的执行状态
        """
        sql = """
        SELECT status FROM meta_pipeline_run 
        WHERE pipeline_id = %s AND biz_date = %s 
        ORDER BY finished_at DESC LIMIT 1
        """
        from typing import Optional
        rows = await execute_query(sql, (pipeline_id, biz_date), is_select=True)
        return rows[0]['status'] if rows else None

    @staticmethod
    async def update_data_readiness(biz_date: str, table_name: str, row_count: int) -> int:
        """
        更新数据就绪状态探测表 (绝对对齐 meta_data_readiness)
        """
        sql = """
        INSERT INTO meta_data_readiness (
            table_name, biz_date, storage, record_count, ready_at, status
        ) VALUES (
            %s, %s, 'MYSQL', %s, CURRENT_TIMESTAMP, 'READY'
        ) ON DUPLICATE KEY UPDATE 
            record_count = VALUES(record_count),
            ready_at = CURRENT_TIMESTAMP, 
            status = 'READY'
        """
        params = (table_name, biz_date, row_count)
        return await execute_query(sql, params, is_select=False)

    @staticmethod
    def _format_tushare_date(date_str: str) -> str:
        """将 '20260508' 转换为 '2026-05-08'"""
        if not date_str or not isinstance(date_str, str) or len(date_str) != 8:
            return None
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

    @classmethod
    async def save_trading_calendar(cls, data: List[Dict[str, Any]]) -> int:
        """保存交易日历"""
        if not data:
            return 0
        
        sql = """
        INSERT INTO trade_cal (cal_date, exchange, is_open, pretrade_date)
        VALUES (%(cal_date)s, %(exchange)s, %(is_open)s, %(pretrade_date)s)
        ON DUPLICATE KEY UPDATE 
            is_open = VALUES(is_open),
            pretrade_date = VALUES(pretrade_date)
        """
        
        count = 0
        for item in data:
            # 数据转换
            formatted_item = {
                "cal_date": cls._format_tushare_date(item.get('cal_date')),
                "exchange": item.get('exchange'),
                "is_open": int(item.get('is_open', 0)),
                "pretrade_date": cls._format_tushare_date(item.get('pretrade_date'))
            }
            res = await execute_query(sql, formatted_item, is_select=False)
            count += res
            
        logger.info(f"Saved {len(data)} calendar records to trade_cal.")
        return count

    @classmethod
    async def save_stock_list(cls, data: List[Dict[str, Any]]) -> int:
        """保存股票列表"""
        if not data:
            return 0
            
        sql = """
        INSERT INTO stock_basic_info (
            ts_code, symbol, name, area, industry, fullname, enname, cnspell, 
            market, exchange, curr_type, list_status, list_date, delist_date, 
            is_hs, act_name, act_ent_type
        ) VALUES (
            %(ts_code)s, %(symbol)s, %(name)s, %(area)s, %(industry)s, %(fullname)s, %(enname)s, %(cnspell)s, 
            %(market)s, %(exchange)s, %(curr_type)s, %(list_status)s, %(list_date)s, %(delist_date)s, 
            %(is_hs)s, %(act_name)s, %(act_ent_type)s
        ) ON DUPLICATE KEY UPDATE 
            name = VALUES(name),
            area = VALUES(area),
            industry = VALUES(industry),
            list_status = VALUES(list_status),
            delist_date = VALUES(delist_date),
            is_hs = VALUES(is_hs)
        """
        
        count = 0
        for item in data:
            # 日期处理
            item['list_date'] = cls._format_tushare_date(item.get('list_date'))
            item['delist_date'] = cls._format_tushare_date(item.get('delist_date'))
            
            res = await execute_query(sql, item, is_select=False)
            count += res
            
        logger.info(f"Saved {len(data)} stock list records to stock_basic_info.")
        return count

    @staticmethod
    async def save_suspensions(data: List[Dict[str, Any]]) -> int:
        """批量保存停牌数据 (ods_suspend_d) - 审计修正版"""
        if not data:
            return 0
        
        sql = """
        INSERT INTO ods_suspend_d (ts_code, trade_date, suspend_timing, suspend_type)
        VALUES (%(ts_code)s, %(trade_date)s, %(suspend_timing)s, %(suspend_type)s)
        ON DUPLICATE KEY UPDATE 
            suspend_timing = VALUES(suspend_timing),
            suspend_type = VALUES(suspend_type),
            is_deleted = 0
        """
        count = 0
        for item in data:
            # 日期转换: 20240510 -> 2024-05-10
            dt = item.get('trade_date')
            if dt and len(str(dt)) == 8:
                item['trade_date'] = f"{str(dt)[:4]}-{str(dt)[4:6]}-{str(dt)[6:]}"
            
            res = await execute_query(sql, item, is_select=False)
            count += res
        return count

    @staticmethod
    async def get_active_stock_codes(trade_date: str) -> List[str]:
        """获取当日理论应采的活跃股票列表"""
        sql = """
        SELECT ts_code FROM stock_basic_info 
        WHERE list_status = 'L' AND list_date <= %s
        """
        rows = await execute_query(sql, (trade_date,), is_select=True)
        return [row['ts_code'] for row in rows] if rows else []

    @staticmethod
    async def get_suspended_codes(trade_date: str) -> List[str]:
        """获取当日停牌的股票列表 - [DB Auditor] 补齐 is_deleted"""
        sql = "SELECT ts_code FROM ods_suspend_d WHERE trade_date = %s AND is_deleted = 0"
        rows = await execute_query(sql, (trade_date,), is_select=True)
        return [row['ts_code'] for row in rows] if rows else []

    @staticmethod
    async def save_universe_snapshot(biz_date: str, expected_count: int, codes: List[str]) -> int:
        """保存当日应采基准快照 (meta_universe_snapshot)"""
        sql = """
        INSERT INTO meta_universe_snapshot (biz_date, expected_count, codes_json)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            expected_count = VALUES(expected_count),
            codes_json = VALUES(codes_json),
            updated_at = CURRENT_TIMESTAMP,
            is_deleted = 0
        """
        params = (biz_date, expected_count, json.dumps(codes))
        return await execute_query(sql, params, is_select=False)

    @staticmethod
    async def get_universe_snapshot(biz_date: str) -> Dict[str, Any]:
        """获取盘前锁定的基准快照"""
        sql = "SELECT expected_count, codes_json FROM meta_universe_snapshot WHERE biz_date = %s AND is_deleted = 0"
        rows = await execute_query(sql, (biz_date,), is_select=True)
        if not rows:
            return None
        row = rows[0]
        return {
            "expected_count": row['expected_count'],
            "codes": json.loads(row['codes_json']) if row['codes_json'] else []
        }
    @staticmethod
    async def get_kline_daily(trade_date: str) -> List[Dict[str, Any]]:
        """获取指定日期的全量 K 线行情 (用于影子审计)"""
        sql = """
        SELECT ts_code, trade_date, open, high, low, close, pre_close, pct_chg, volume, amount 
        FROM stock_kline_daily 
        WHERE trade_date = %s
        """
        rows = await execute_query(sql, (trade_date,), is_select=True)
        return rows if rows else []

    @staticmethod
    async def is_trading_day(biz_date: str) -> bool:
        """
        [E7-S5-T1] 校验指定日期是否为 A 股交易日 (兼容 SSE 和 SH 编码)
        """
        sql = "SELECT is_open FROM trade_cal WHERE cal_date = %s AND exchange IN ('SSE', 'SH')"
        rows = await execute_query(sql, (biz_date,), is_select=True)
        if rows:
            return bool(rows[0]['is_open'])
        return False

    @staticmethod
    async def save_audit_log(data: Dict[str, Any]) -> int:
        """保存影子审计日志 (meta_data_audit_log) - 支持 v1.4 全量字段"""
        sql = """
        INSERT INTO meta_data_audit_log (
            trade_date, task_name, source_primary, source_secondary, 
            primary_count, secondary_count, overlap_count, expected_count, coverage_rate,
            open_mae, high_mae, low_mae, close_mae, volume_mae, amount_mae, pct_chg_mae,
            outlier_count, status, report_path, report_content, diff_list, source_tag
        ) VALUES (
            %(trade_date)s, %(task_name)s, %(primary_source)s, %(secondary_source)s, 
            %(primary_count)s, %(secondary_count)s, %(overlap_count)s, %(expected_count)s, %(coverage_rate)s,
            %(open_mae)s, %(high_mae)s, %(low_mae)s, %(close_mae)s, %(volume_mae)s, %(amount_mae)s, %(pct_chg_mae)s,
            %(outlier_count)s, %(status)s, %(report_path)s, %(report_content)s, %(diff_list)s, %(source_tag)s
        ) ON DUPLICATE KEY UPDATE 
            primary_count = VALUES(primary_count),
            secondary_count = VALUES(secondary_count),
            overlap_count = VALUES(overlap_count),
            coverage_rate = VALUES(coverage_rate),
            close_mae = VALUES(close_mae),
            outlier_count = VALUES(outlier_count),
            status = VALUES(status),
            report_content = VALUES(report_content),
            diff_list = VALUES(diff_list),
            source_tag = VALUES(source_tag),
            updated_at = CURRENT_TIMESTAMP
        """
        return await execute_query(sql, data, is_select=False)

    @classmethod
    def _format_date(cls, date_str: Any) -> Optional[str]:
        if not date_str:
            return None
        s = str(date_str).strip()
        if len(s) == 8:
            return f"{s[:4]}-{s[4:6]}-{s[6:]}"
        return s

    @classmethod
    def _clean_nan(cls, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        [Backend Engineer] 辅助方法：清除财务数据中的 NaN/Inf 浮点数，
        将其转换为 MySQL 支持 of None (对应数据库中的 NULL)，以防发生 "nan can not be used with MySQL" 报错。
        同时为了防止 MySQL DECIMAL 精度截断警告，自动将浮点数保留 4 位小数。
        """
        import math
        import pandas as pd
        cleaned = {}
        for k, v in item.items():
            if pd.isna(v):
                cleaned[k] = None
            else:
                if hasattr(v, 'item'):
                    v = v.item()
                if isinstance(v, float):
                    if math.isnan(v) or math.isinf(v):
                        cleaned[k] = None
                    else:
                        cleaned[k] = round(v, 4)
                else:
                    cleaned[k] = v
        return cleaned

    @classmethod
    async def save_balancesheet(cls, data: List[Dict[str, Any]]) -> int:
        """
        [E13-S4-T2] 批量保存资产负债表数据 (幂等插入)
        """
        if not data:
            return 0

        mapping = {
            "total_liab": "total_liabilities",
            "st_borr": "short_term_borrow",
            "lt_borr": "long_term_borrow"
        }

        sql = """
        INSERT INTO ods_fin_balancesheet (
            ts_code, ann_date, f_ann_date, end_date, report_type, comp_type,
            total_assets, total_liabilities, total_hldr_eqy_exc_min_int, total_hldr_eqy_inc_min_int,
            monetary_funds, notes_receiv, accounts_receiv, inventory, goodwill,
            short_term_borrow, long_term_borrow, is_deleted
        ) VALUES (
            %(ts_code)s, %(ann_date)s, %(f_ann_date)s, %(end_date)s, %(report_type)s, %(comp_type)s,
            %(total_assets)s, %(total_liabilities)s, %(total_hldr_eqy_exc_min_int)s, %(total_hldr_eqy_inc_min_int)s,
            %(monetary_funds)s, %(notes_receiv)s, %(accounts_receiv)s, %(inventory)s, %(goodwill)s,
            %(short_term_borrow)s, %(long_term_borrow)s, 0
        ) ON DUPLICATE KEY UPDATE 
            ann_date = VALUES(ann_date),
            f_ann_date = VALUES(f_ann_date),
            total_assets = VALUES(total_assets),
            total_liabilities = VALUES(total_liabilities),
            total_hldr_eqy_exc_min_int = VALUES(total_hldr_eqy_exc_min_int),
            total_hldr_eqy_inc_min_int = VALUES(total_hldr_eqy_inc_min_int),
            monetary_funds = VALUES(monetary_funds),
            notes_receiv = VALUES(notes_receiv),
            accounts_receiv = VALUES(accounts_receiv),
            inventory = VALUES(inventory),
            goodwill = VALUES(goodwill),
            short_term_borrow = VALUES(short_term_borrow),
            long_term_borrow = VALUES(long_term_borrow),
            is_deleted = 0,
            updated_at = CURRENT_TIMESTAMP
        """

        count = 0
        for item in data:
            item_copy = cls._clean_nan(dict(item))
            # 1. 字段映射
            for ts_key, db_key in mapping.items():
                if ts_key in item_copy:
                    item_copy[db_key] = item_copy.pop(ts_key)
            
            # 2. 日期转换
            for d_key in ["ann_date", "f_ann_date", "end_date"]:
                item_copy[d_key] = cls._format_date(item_copy.get(d_key))

            # 3. 补齐缺省字段
            for col in ["ann_date", "f_ann_date", "end_date", "report_type", "comp_type",
                        "total_assets", "total_liabilities", "total_hldr_eqy_exc_min_int", "total_hldr_eqy_inc_min_int",
                        "monetary_funds", "notes_receiv", "accounts_receiv", "inventory", "goodwill",
                        "short_term_borrow", "long_term_borrow"]:
                if col not in item_copy:
                    item_copy[col] = None

            res = await execute_query(sql, item_copy, is_select=False)
            count += res
        
        logger.info(f"Successfully saved {len(data)} records to ods_fin_balancesheet (affected: {count}).")
        return count

    @classmethod
    async def save_income(cls, data: List[Dict[str, Any]]) -> int:
        """
        [E13-S4-T2] 批量保存利润表数据 (幂等插入)
        """
        if not data:
            return 0

        mapping = {
            "n_income": "net_profit"
        }

        sql = """
        INSERT INTO ods_fin_income (
            ts_code, ann_date, f_ann_date, end_date, report_type, comp_type,
            basic_eps, diluted_eps, total_revenue, revenue, total_cogs, oper_cost,
            sell_exp, admin_exp, fin_exp, operate_profit, total_profit, net_profit, 
            n_income_attr_p, is_deleted
        ) VALUES (
            %(ts_code)s, %(ann_date)s, %(f_ann_date)s, %(end_date)s, %(report_type)s, %(comp_type)s,
            %(basic_eps)s, %(diluted_eps)s, %(total_revenue)s, %(revenue)s, %(total_cogs)s, %(oper_cost)s,
            %(sell_exp)s, %(admin_exp)s, %(fin_exp)s, %(operate_profit)s, %(total_profit)s, %(net_profit)s,
            %(n_income_attr_p)s, 0
        ) ON DUPLICATE KEY UPDATE 
            ann_date = VALUES(ann_date),
            f_ann_date = VALUES(f_ann_date),
            basic_eps = VALUES(basic_eps),
            diluted_eps = VALUES(diluted_eps),
            total_revenue = VALUES(total_revenue),
            revenue = VALUES(revenue),
            total_cogs = VALUES(total_cogs),
            oper_cost = VALUES(oper_cost),
            sell_exp = VALUES(sell_exp),
            admin_exp = VALUES(admin_exp),
            fin_exp = VALUES(fin_exp),
            operate_profit = VALUES(operate_profit),
            total_profit = VALUES(total_profit),
            net_profit = VALUES(net_profit),
            n_income_attr_p = VALUES(n_income_attr_p),
            is_deleted = 0,
            updated_at = CURRENT_TIMESTAMP
        """

        count = 0
        for item in data:
            item_copy = cls._clean_nan(dict(item))
            # 1. 字段映射
            for ts_key, db_key in mapping.items():
                if ts_key in item_copy:
                    item_copy[db_key] = item_copy.pop(ts_key)
            
            # 2. 日期转换
            for d_key in ["ann_date", "f_ann_date", "end_date"]:
                item_copy[d_key] = cls._format_date(item_copy.get(d_key))

            # 3. 补齐缺省字段
            for col in ["ann_date", "f_ann_date", "end_date", "report_type", "comp_type",
                        "basic_eps", "diluted_eps", "total_revenue", "revenue", "total_cogs", "oper_cost",
                        "sell_exp", "admin_exp", "fin_exp", "operate_profit", "total_profit", "net_profit", "n_income_attr_p"]:
                if col not in item_copy:
                    item_copy[col] = None

            res = await execute_query(sql, item_copy, is_select=False)
            count += res
        
        logger.info(f"Successfully saved {len(data)} records to ods_fin_income (affected: {count}).")
        return count

    @classmethod
    async def save_cashflow(cls, data: List[Dict[str, Any]]) -> int:
        """
        [E13-S4-T2] 批量保存现金流量表数据 (幂等插入)
        """
        if not data:
            return 0

        mapping = {
            "n_cashflow_act": "net_cash_flows_oper_act",
            "n_cashflow_inv_act": "net_cash_flows_inv_act",
            "n_cash_flows_fnc_act": "net_cash_flows_fnc_act"
        }

        sql = """
        INSERT INTO ods_fin_cashflow (
            ts_code, ann_date, f_ann_date, end_date, report_type, comp_type,
            net_cash_flows_oper_act, net_cash_flows_inv_act, net_cash_flows_fnc_act, free_cashflow, is_deleted
        ) VALUES (
            %(ts_code)s, %(ann_date)s, %(f_ann_date)s, %(end_date)s, %(report_type)s, %(comp_type)s,
            %(net_cash_flows_oper_act)s, %(net_cash_flows_inv_act)s, %(net_cash_flows_fnc_act)s, %(free_cashflow)s, 0
        ) ON DUPLICATE KEY UPDATE 
            ann_date = VALUES(ann_date),
            f_ann_date = VALUES(f_ann_date),
            net_cash_flows_oper_act = VALUES(net_cash_flows_oper_act),
            net_cash_flows_inv_act = VALUES(net_cash_flows_inv_act),
            net_cash_flows_fnc_act = VALUES(net_cash_flows_fnc_act),
            free_cashflow = VALUES(free_cashflow),
            is_deleted = 0,
            updated_at = CURRENT_TIMESTAMP
        """

        count = 0
        for item in data:
            item_copy = cls._clean_nan(dict(item))
            # 1. 字段映射
            for ts_key, db_key in mapping.items():
                if ts_key in item_copy:
                    item_copy[db_key] = item_copy.pop(ts_key)
            
            # 2. 日期转换
            for d_key in ["ann_date", "f_ann_date", "end_date"]:
                item_copy[d_key] = cls._format_date(item_copy.get(d_key))

            # 3. 补齐缺省字段
            for col in ["ann_date", "f_ann_date", "end_date", "report_type", "comp_type",
                        "net_cash_flows_oper_act", "net_cash_flows_inv_act", "net_cash_flows_fnc_act", "free_cashflow"]:
                if col not in item_copy:
                    item_copy[col] = None

            res = await execute_query(sql, item_copy, is_select=False)
            count += res
        
        logger.info(f"Successfully saved {len(data)} records to ods_fin_cashflow (affected: {count}).")
        return count

    @classmethod
    async def save_fina_indicator(cls, data: List[Dict[str, Any]]) -> int:
        """
        [E13-S4-T2] 批量保存财务指标数据 (幂等插入，百分比除以 100 转换)
        """
        if not data:
            return 0

        sql = """
        INSERT INTO ods_fin_indicators (
            ts_code, ann_date, end_date, eps, dt_eps, total_revenue_ps, revenue_ps,
            capital_rese_ps, undist_profit_ps, roe, roe_dt, roa, netprofit_margin,
            grossprofit_margin, debt_to_assets, current_ratio, quick_ratio, is_deleted
        ) VALUES (
            %(ts_code)s, %(ann_date)s, %(end_date)s, %(eps)s, %(dt_eps)s, %(total_revenue_ps)s, %(revenue_ps)s,
            %(capital_rese_ps)s, %(undist_profit_ps)s, %(roe)s, %(roe_dt)s, %(roa)s, %(netprofit_margin)s,
            %(grossprofit_margin)s, %(debt_to_assets)s, %(current_ratio)s, %(quick_ratio)s, 0
        ) ON DUPLICATE KEY UPDATE 
            ann_date = VALUES(ann_date),
            eps = VALUES(eps),
            dt_eps = VALUES(dt_eps),
            total_revenue_ps = VALUES(total_revenue_ps),
            revenue_ps = VALUES(revenue_ps),
            capital_rese_ps = VALUES(capital_rese_ps),
            undist_profit_ps = VALUES(undist_profit_ps),
            roe = VALUES(roe),
            roe_dt = VALUES(roe_dt),
            roa = VALUES(roa),
            netprofit_margin = VALUES(netprofit_margin),
            grossprofit_margin = VALUES(grossprofit_margin),
            debt_to_assets = VALUES(debt_to_assets),
            current_ratio = VALUES(current_ratio),
            quick_ratio = VALUES(quick_ratio),
            is_deleted = 0,
            updated_at = CURRENT_TIMESTAMP
        """

        count = 0
        for item in data:
            item_copy = cls._clean_nan(dict(item))
            
            # 1. 百分比字段除以 100 换算为标准小数
            percent_cols = ['roe', 'roe_dt', 'roa', 'netprofit_margin', 'grossprofit_margin', 'debt_to_assets']
            for col in percent_cols:
                val = item_copy.get(col)
                if val is not None:
                    try:
                        item_copy[col] = round(float(val) / 100.0, 4)
                    except (ValueError, TypeError):
                        item_copy[col] = None

            # 2. 日期转换
            for d_key in ["ann_date", "end_date"]:
                item_copy[d_key] = cls._format_date(item_copy.get(d_key))

            # 3. 补齐缺省字段
            for col in ["ann_date", "end_date", "eps", "dt_eps", "total_revenue_ps", "revenue_ps",
                        "capital_rese_ps", "undist_profit_ps", "roe", "roe_dt", "roa", "netprofit_margin",
                        "grossprofit_margin", "debt_to_assets", "current_ratio", "quick_ratio"]:
                if col not in item_copy:
                    item_copy[col] = None

            res = await execute_query(sql, item_copy, is_select=False)
            count += res
        
        logger.info(f"Successfully saved {len(data)} records to ods_fin_indicators (affected: {count}).")
        return count

    @classmethod
    async def save_limit_pool(cls, data: List[Dict[str, Any]]) -> int:
        """
        [E15-S1-T1] 批量保存涨跌停/炸板/连板池数据 (幂等插入)
        """
        if not data:
            return 0

        sql = """
        INSERT INTO ods_event_limit_pool (
            trade_date, ts_code, name, pool_type, close, pct_chg,
            amount, circ_mv, turnover_rate, first_limit_time,
            last_limit_time, board_height, seal_money, seal_count,
            open_times, industry, data_source
        ) VALUES (
            %(trade_date)s, %(ts_code)s, %(name)s, %(pool_type)s, %(close)s, %(pct_chg)s,
            %(amount)s, %(circ_mv)s, %(turnover_rate)s, %(first_limit_time)s,
            %(last_limit_time)s, %(board_height)s, %(seal_money)s, %(seal_count)s,
            %(open_times)s, %(industry)s, %(data_source)s
        ) ON DUPLICATE KEY UPDATE 
            name = VALUES(name),
            close = VALUES(close),
            pct_chg = VALUES(pct_chg),
            amount = VALUES(amount),
            circ_mv = VALUES(circ_mv),
            turnover_rate = VALUES(turnover_rate),
            first_limit_time = VALUES(first_limit_time),
            last_limit_time = VALUES(last_limit_time),
            board_height = VALUES(board_height),
            seal_money = VALUES(seal_money),
            seal_count = VALUES(seal_count),
            open_times = VALUES(open_times),
            industry = VALUES(industry),
            data_source = VALUES(data_source),
            updated_at = CURRENT_TIMESTAMP
        """

        count = 0
        for item in data:
            item_copy = cls._clean_nan(dict(item))
            
            # 日期格式化
            item_copy['trade_date'] = cls._format_date(item_copy.get('trade_date'))
            
            # 百分比转换 (安全处理)
            for col in ['pct_chg', 'turnover_rate']:
                val = item_copy.get(col)
                if val is not None:
                    if abs(float(val)) > 1.0:
                        item_copy[col] = round(float(val) / 100.0, 6)
                    else:
                        item_copy[col] = round(float(val), 6)

            # 封单金额处理 (元)
            seal_money = item_copy.get('seal_money') or item_copy.get('fd_amount')
            if seal_money is not None:
                item_copy['seal_money'] = round(float(seal_money), 2)
            else:
                item_copy['seal_money'] = None

            # 字段补齐
            for col in ['amount', 'circ_mv', 'first_limit_time', 'last_limit_time', 
                        'board_height', 'seal_count', 'open_times', 'industry', 'data_source']:
                if col not in item_copy:
                    item_copy[col] = None
                    
            if not item_copy.get('data_source'):
                item_copy['data_source'] = 'tushare'

            res = await execute_query(sql, item_copy, is_select=False)
            count += res
        
        logger.info(f"Successfully saved {len(data)} records to ods_event_limit_pool (affected: {count}).")
        return count

    @classmethod
    async def save_suspend_calendar(cls, data: List[Dict[str, Any]]) -> int:
        """
        [E15-S1-T2] 批量保存每日停复牌数据 (幂等插入)
        """
        if not data:
            return 0

        sql = """
        INSERT INTO stock_suspensions (
            ts_code, trade_date, is_suspended, reason
        ) VALUES (
            %(ts_code)s, %(trade_date)s, %(is_suspended)s, %(reason)s
        ) ON DUPLICATE KEY UPDATE 
            is_suspended = VALUES(is_suspended),
            reason = VALUES(reason),
            updated_at = CURRENT_TIMESTAMP
        """

        count = 0
        for item in data:
            item_copy = cls._clean_nan(dict(item))
            item_copy['trade_date'] = cls._format_date(item_copy.get('trade_date'))
            item_copy['is_suspended'] = 1
            
            if 'reason' not in item_copy:
                item_copy['reason'] = None
                
            res = await execute_query(sql, item_copy, is_select=False)
            count += res
            
        logger.info(f"Successfully saved {len(data)} records to stock_suspensions (affected: {count}).")
        return count

    @classmethod
    async def get_latest_margin_date(cls) -> Optional[str]:
        """
        [E15-S1-T3] 查询已落库的最大两融交易日期，用于断点续传
        """
        sql = "SELECT MAX(trade_date) as max_date FROM ods_margin_detail WHERE is_deleted = 0"
        rows = await execute_query(sql, is_select=True)
        if rows and rows[0]['max_date']:
            d = rows[0]['max_date']
            if isinstance(d, datetime.date):
                return d.strftime('%Y-%m-%d')
            return str(d)
        return None

    @classmethod
    async def save_margin_total(cls, data: List[Dict[str, Any]]) -> int:
        """
        [E15-S1-T3] 批量保存全市场与分市场两融每日汇总数据 (幂等插入)
        """
        if not data:
            return 0

        sql = """
        INSERT INTO ods_margin_total (
            trade_date, exchange_id, rzye, rzmre, rqye, rqyl, rzrqye
        ) VALUES (
            %(trade_date)s, %(exchange_id)s, %(rzye)s, %(rzmre)s, %(rqye)s, %(rqyl)s, %(rzrqye)s
        ) ON DUPLICATE KEY UPDATE 
            rzye = VALUES(rzye),
            rzmre = VALUES(rzmre),
            rqye = VALUES(rqye),
            rqyl = VALUES(rqyl),
            rzrqye = VALUES(rzrqye),
            is_deleted = 0,
            updated_at = CURRENT_TIMESTAMP
        """

        count = 0
        for item in data:
            item_copy = cls._clean_nan(dict(item))
            item_copy['trade_date'] = cls._format_date(item_copy.get('trade_date'))
            
            for col in ['rzye', 'rzmre', 'rqye', 'rqyl', 'rzrqye']:
                val = item_copy.get(col)
                item_copy[col] = float(val) if val is not None else None
                
            if 'exchange_id' not in item_copy:
                item_copy['exchange_id'] = 'ALL'

            res = await execute_query(sql, item_copy, is_select=False)
            count += res
            
        logger.info(f"Successfully saved {len(data)} records to ods_margin_total (affected: {count}).")
        return count

    @classmethod
    async def save_margin_detail(cls, data: List[Dict[str, Any]]) -> int:
        """
        [E15-S1-T3] 批量保存个股每日两融明细 (幂等插入)
        """
        if not data:
            return 0

        sql = """
        INSERT INTO ods_margin_detail (
            ts_code, trade_date, name, rzye, rzmre, rzche, rqye, rqyl, rqchl, rqmcl, rzrqye
        ) VALUES (
            %(ts_code)s, %(trade_date)s, %(name)s, %(rzye)s, %(rzmre)s, %(rzche)s, %(rqye)s, %(rqyl)s, %(rqchl)s, %(rqmcl)s, %(rzrqye)s
        ) ON DUPLICATE KEY UPDATE 
            name = VALUES(name),
            rzye = VALUES(rzye),
            rzmre = VALUES(rzmre),
            rzche = VALUES(rzche),
            rqye = VALUES(rqye),
            rqyl = VALUES(rqyl),
            rqchl = VALUES(rqchl),
            rqmcl = VALUES(rqmcl),
            rzrqye = VALUES(rzrqye),
            is_deleted = 0,
            updated_at = CURRENT_TIMESTAMP
        """

        count = 0
        for item in data:
            item_copy = cls._clean_nan(dict(item))
            item_copy['trade_date'] = cls._format_date(item_copy.get('trade_date'))
            
            for col in ['rzye', 'rzmre', 'rzche', 'rqye', 'rqyl', 'rqchl', 'rqmcl', 'rzrqye']:
                val = item_copy.get(col)
                item_copy[col] = float(val) if val is not None else None
                
            if 'name' not in item_copy:
                item_copy['name'] = None

            res = await execute_query(sql, item_copy, is_select=False)
            count += res
            
        logger.info(f"Successfully saved {len(data)} records to ods_margin_detail (affected: {count}).")
        return count

    @classmethod
    async def derive_market_breadth(cls, trade_date: str) -> bool:
        """
        [E15-S1-T4] 派生当日市场广度指标并入库 ods_market_breadth_daily
        """
        import itertools
        import bisect
        import datetime
        
        target_date = cls._format_date(trade_date)
        logger.info(f"Starting derive_market_breadth for {target_date}...")
        
        # 1. 基础涨跌家数统计
        sql_agg = """
            SELECT
                COUNT(*) as count,
                SUM(CASE WHEN pct_chg > 0 THEN 1 ELSE 0 END) as up_count,
                SUM(CASE WHEN pct_chg < 0 THEN 1 ELSE 0 END) as down_count,
                SUM(CASE WHEN pct_chg = 0 THEN 1 ELSE 0 END) as flat_count,
                SUM(CASE WHEN pct_chg >= 0.05 THEN 1 ELSE 0 END) as up_5pct_count,
                SUM(CASE WHEN pct_chg <= -0.05 THEN 1 ELSE 0 END) as down_5pct_count,
                SUM(CASE WHEN pct_chg >= 0.09 THEN 1 ELSE 0 END) as up_9pct_count,
                SUM(CASE WHEN pct_chg <= -0.09 THEN 1 ELSE 0 END) as down_9pct_count
            FROM stock_kline_daily
            WHERE trade_date = %s
            AND ts_code NOT LIKE '900%' AND ts_code NOT LIKE '200%'
        """
        res_agg = await execute_query(sql_agg, (target_date,), is_select=True)
        if not res_agg or not res_agg[0]['count']:
            logger.warning(f"No stock_kline_daily data found for {target_date}, cannot compute breadth.")
            return False

        row = res_agg[0]
        curr_count = row['count']
        up_count = row['up_count'] or 0
        down_count = row['down_count'] or 0
        flat_count = row['flat_count'] or 0
        up_5pct = row['up_5pct_count'] or 0
        down_5pct = row['down_5pct_count'] or 0
        up_9pct = row['up_9pct_count'] or 0
        down_9pct = row['down_9pct_count'] or 0

        # 获取上市超60天的股票总数 (用于计算停牌数)
        sql_count = """
            SELECT COUNT(*) as cnt FROM stock_basic_info
            WHERE list_status = 'L' AND list_date <= DATE_SUB(%s, INTERVAL 60 DAY)
            AND ts_code NOT LIKE '900%' AND ts_code NOT LIKE '200%'
        """
        res_total = await execute_query(sql_count, (target_date,), is_select=True)
        total_count = res_total[0]['cnt'] if res_total else 0
        suspended_count = max(0, total_count - curr_count)

        # 2. 计算 60/250 日新高新低
        sql_date_250 = "SELECT DISTINCT trade_date FROM stock_kline_daily WHERE trade_date < %s ORDER BY trade_date DESC LIMIT 249, 1"
        res_250 = await execute_query(sql_date_250, (target_date,), is_select=True)
        start_date_250 = res_250[0]['trade_date'] if res_250 else '1970-01-01'

        sql_date_60 = "SELECT DISTINCT trade_date FROM stock_kline_daily WHERE trade_date < %s ORDER BY trade_date DESC LIMIT 59, 1"
        res_60 = await execute_query(sql_date_60, (target_date,), is_select=True)
        start_date_60 = res_60[0]['trade_date'] if res_60 else '1970-01-01'

        high_60d, low_60d, high_250d, low_250d = 0, 0, 0, 0

        # 分批获取股票列表进行计算以节省内存
        sql_all_codes = "SELECT DISTINCT ts_code FROM stock_kline_daily WHERE trade_date = %s"
        codes_res = await execute_query(sql_all_codes, (target_date,), is_select=True)
        all_codes = [r['ts_code'] for r in codes_res]

        batch_size = 500
        for i in range(0, len(all_codes), batch_size):
            batch_codes = all_codes[i:i + batch_size]
            placeholders = ','.join(['%s'] * len(batch_codes))
            
            # 获取该批次股票的复权因子
            sql_f = f"SELECT ts_code, adjust_date, back_adjust_factor FROM stock_adjust_factor WHERE ts_code IN ({placeholders}) ORDER BY ts_code, adjust_date"
            f_res = await execute_query(sql_f, tuple(batch_codes), is_select=True)
            f_map = {}
            for r in f_res:
                f_code = r['ts_code']
                f_date = r['adjust_date']
                f_factor = r['back_adjust_factor']
                if f_code not in f_map:
                    f_map[f_code] = []
                # 兼容 date 与 datetime
                if isinstance(f_date, datetime.date):
                    f_map[f_code].append((f_date, float(f_factor)))
                else:
                    d_parsed = datetime.datetime.strptime(str(f_date)[:10], '%Y-%m-%d').date()
                    f_map[f_code].append((d_parsed, float(f_factor)))

            # 获取该批次股票的 K 线窗口
            sql_k = f"SELECT ts_code, trade_date, close FROM stock_kline_daily WHERE ts_code IN ({placeholders}) AND trade_date >= %s AND trade_date <= %s ORDER BY ts_code, trade_date"
            k_res = await execute_query(sql_k, tuple(batch_codes + [start_date_250, target_date]), is_select=True)

            target_date_obj = datetime.datetime.strptime(target_date, '%Y-%m-%d').date() if isinstance(target_date, str) else target_date
            
            # 转换 start_date_60
            if isinstance(start_date_60, str):
                start_date_60_obj = datetime.datetime.strptime(start_date_60, '%Y-%m-%d').date()
            else:
                start_date_60_obj = start_date_60

            # 转换并分组
            k_list = []
            for r in k_res:
                kd = r['trade_date']
                kd_obj = datetime.datetime.strptime(str(kd)[:10], '%Y-%m-%d').date() if not isinstance(kd, datetime.date) else kd
                k_list.append((r['ts_code'], kd_obj, float(r['close'])))

            for code, group in itertools.groupby(k_list, key=lambda x: x[0]):
                rows = list(group)
                f_list = f_map.get(code, [(datetime.date(1990, 1, 1), 1.0)])
                f_dates = [x[0] for x in f_list]
                latest_factor = f_list[-1][1] if f_list else 1.0

                adj_rows = []
                for _, t_date, raw_close in rows:
                    idx = bisect.bisect_right(f_dates, t_date) - 1
                    factor = f_list[idx if idx >= 0 else 0][1]
                    adj_p = float(raw_close) * (factor / latest_factor)
                    adj_rows.append({'date': t_date, 'adj_close': adj_p})

                target_row = next((r for r in adj_rows if r['date'] == target_date_obj), None)
                if not target_row:
                    continue
                curr_p = target_row['adj_close']

                hist_250 = [r['adj_close'] for r in adj_rows if r['date'] < target_date_obj]
                if hist_250:
                    if curr_p >= max(hist_250):
                        high_250d += 1
                    if curr_p <= min(hist_250):
                        low_250d += 1

                hist_60 = [r['adj_close'] for r in adj_rows if r['date'] < target_date_obj and r['date'] >= start_date_60_obj]
                if hist_60:
                    if curr_p >= max(hist_60):
                        high_60d += 1
                    if curr_p <= min(hist_60):
                        low_60d += 1

        # 写入或更新 market_breadth
        query = """
            INSERT INTO ods_market_breadth_daily (
                trade_date, total_count, up_count, down_count, flat_count,
                suspended_count, up_5pct_count, down_5pct_count,
                up_9pct_count, down_9pct_count, high_60d_count, low_60d_count,
                high_250d_count, low_250d_count, data_source
            ) VALUES (
                %(trade_date)s, %(total_count)s, %(up_count)s, %(down_count)s, %(flat_count)s,
                %(suspended_count)s, %(up_5pct_count)s, %(down_5pct_count)s,
                %(up_9pct_count)s, %(down_9pct_count)s, %(high_60d_count)s, %(low_60d_count)s,
                %(high_250d_count)s, %(low_250d_count)s, 'local_derived'
            ) ON DUPLICATE KEY UPDATE
                total_count = VALUES(total_count),
                up_count = VALUES(up_count),
                down_count = VALUES(down_count),
                flat_count = VALUES(flat_count),
                suspended_count = VALUES(suspended_count),
                up_5pct_count = VALUES(up_5pct_count),
                down_5pct_count = VALUES(down_5pct_count),
                up_9pct_count = VALUES(up_9pct_count),
                down_9pct_count = VALUES(down_9pct_count),
                high_60d_count = VALUES(high_60d_count),
                low_60d_count = VALUES(low_60d_count),
                high_250d_count = VALUES(high_250d_count),
                low_250d_count = VALUES(low_250d_count),
                data_source = VALUES(data_source),
                updated_at = CURRENT_TIMESTAMP
        """
        
        params = {
            'trade_date': target_date,
            'total_count': total_count,
            'up_count': up_count,
            'down_count': down_count,
            'flat_count': flat_count,
            'suspended_count': suspended_count,
            'up_5pct_count': up_5pct,
            'down_5pct_count': down_5pct,
            'up_9pct_count': up_9pct,
            'down_9pct_count': down_9pct,
            'high_60d_count': high_60d,
            'low_60d_count': low_60d,
            'high_250d_count': high_250d,
            'low_250d_count': low_250d
        }
        
        await execute_query(query, params, is_select=False)
        logger.info(f"Successfully computed and derived market breadth for {target_date}")
        return True
