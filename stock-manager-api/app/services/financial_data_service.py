from typing import List, Dict, Any, Optional
from app.utils.database import db
from app.utils.http_client import http_client
from app.utils.code_utils import normalize_ts_code
from app.utils.logger import get_logger
import datetime

logger = get_logger("stock-manager.financial_data")

class FinancialDataService:
    """基本面财务数据同步服务 (ODS 层)"""

    async def sync_all_financial_data(self, ts_code: str, period: Optional[str] = None):
        """同步指定股票的所有财务报表及指标"""
        ts_code = normalize_ts_code(ts_code)
        
        # 1. 同步资产负债表
        count_bs = await self.sync_balancesheet(ts_code, period)
        # 2. 同步利润表
        count_is = await self.sync_income(ts_code, period)
        # 3. 同步现金流量表
        count_cf = await self.sync_cashflow(ts_code, period)
        # 4. 同步财务指标
        count_ind = await self.sync_indicators(ts_code, period)
        
        return {
            "ts_code": ts_code,
            "balancesheet": count_bs,
            "income": count_is,
            "cashflow": count_cf,
            "indicators": count_ind
        }

    async def sync_balancesheet(self, ts_code: str, period: Optional[str] = None) -> int:
        params = {"ts_code": ts_code}
        if period:
            params["period"] = period
        
        res = await http_client.get("tushare", "/api/v1/balancesheet", params=params)
        data = res.get("data", [])
        if not data:
            return 0
        
        # 字段映射 (Tushare -> ODS Table)
        mapping = {
            "total_liab": "total_liabilities",
            "st_borr": "short_term_borrow",
            "lt_borr": "long_term_borrow"
        }
        
        sql = """
            INSERT INTO ods_fin_balancesheet
            (ts_code, ann_date, f_ann_date, end_date, report_type, comp_type,
             total_assets, total_liabilities, total_hldr_eqy_exc_min_int, total_hldr_eqy_inc_min_int,
             monetary_funds, notes_receiv, accounts_receiv, inventory, goodwill,
             short_term_borrow, long_term_borrow)
            VALUES (%(ts_code)s, %(ann_date)s, %(f_ann_date)s, %(end_date)s, %(report_type)s, %(comp_type)s,
                    %(total_assets)s, %(total_liabilities)s, %(total_hldr_eqy_exc_min_int)s, %(total_hldr_eqy_inc_min_int)s,
                    %(monetary_funds)s, %(notes_receiv)s, %(accounts_receiv)s, %(inventory)s, %(goodwill)s,
                    %(short_term_borrow)s, %(long_term_borrow)s)
            ON DUPLICATE KEY UPDATE
                ann_date = VALUES(ann_date),
                f_ann_date = VALUES(f_ann_date),
                total_assets = VALUES(total_assets),
                total_liabilities = VALUES(total_liabilities),
                total_hldr_eqy_exc_min_int = VALUES(total_hldr_eqy_exc_min_int),
                updated_at = CURRENT_TIMESTAMP
        """
        
        for item in data:
            # 日期转换
            for d_key in ["ann_date", "f_ann_date", "end_date"]:
                if item.get(d_key):
                    d = item[d_key]
                    item[d_key] = f"{d[:4]}-{d[4:6]}-{d[6:]}"
            # 字段映射
            for ts_key, db_key in mapping.items():
                if ts_key in item:
                    item[db_key] = item.pop(ts_key)
            # 补齐缺省字段
            for col in ["total_assets", "total_liabilities", "total_hldr_eqy_exc_min_int", "total_hldr_eqy_inc_min_int",
                        "monetary_funds", "notes_receiv", "accounts_receiv", "inventory", "goodwill",
                        "short_term_borrow", "long_term_borrow"]:
                if col not in item:
                    item[col] = None
        
        await db.execute_many(sql, data)
        return len(data)

    async def sync_income(self, ts_code: str, period: Optional[str] = None) -> int:
        params = {"ts_code": ts_code}
        if period:
            params["period"] = period
            
        res = await http_client.get("tushare", "/api/v1/income", params=params)
        data = res.get("data", [])
        if not data:
            return 0
            
        mapping = {
            "n_income": "net_profit"
        }
        
        sql = """
            INSERT INTO ods_fin_income
            (ts_code, ann_date, f_ann_date, end_date, report_type, comp_type,
             basic_eps, diluted_eps, total_revenue, revenue, total_cogs, oper_cost,
             sell_exp, admin_exp, fin_exp, operate_profit, total_profit, net_profit, n_income_attr_p)
            VALUES (%(ts_code)s, %(ann_date)s, %(f_ann_date)s, %(end_date)s, %(report_type)s, %(comp_type)s,
                    %(basic_eps)s, %(diluted_eps)s, %(total_revenue)s, %(revenue)s, %(total_cogs)s, %(oper_cost)s,
                    %(sell_exp)s, %(admin_exp)s, %(fin_exp)s, %(operate_profit)s, %(total_profit)s, %(net_profit)s, %(n_income_attr_p)s)
            ON DUPLICATE KEY UPDATE
                ann_date = VALUES(ann_date),
                total_revenue = VALUES(total_revenue),
                net_profit = VALUES(net_profit),
                updated_at = CURRENT_TIMESTAMP
        """
        for item in data:
            for d_key in ["ann_date", "f_ann_date", "end_date"]:
                if item.get(d_key):
                    d = item[d_key]
                    item[d_key] = f"{d[:4]}-{d[4:6]}-{d[6:]}"
            for ts_key, db_key in mapping.items():
                if ts_key in item:
                    item[db_key] = item.pop(ts_key)
            for col in ["basic_eps", "diluted_eps", "total_revenue", "revenue", "total_cogs", "oper_cost",
                        "sell_exp", "admin_exp", "fin_exp", "operate_profit", "total_profit", "net_profit", "n_income_attr_p"]:
                if col not in item:
                    item[col] = None
                    
        await db.execute_many(sql, data)
        return len(data)

    async def sync_cashflow(self, ts_code: str, period: Optional[str] = None) -> int:
        params = {"ts_code": ts_code}
        if period:
            params["period"] = period
            
        res = await http_client.get("tushare", "/api/v1/cashflow", params=params)
        data = res.get("data", [])
        if not data:
            return 0
            
        mapping = {
            "n_cashflow_act": "net_cash_flows_oper_act",
            "n_cashflow_inv_act": "net_cash_flows_inv_act",
            "n_cash_flows_fnc_act": "net_cash_flows_fnc_act"
        }
        
        sql = """
            INSERT INTO ods_fin_cashflow
            (ts_code, ann_date, f_ann_date, end_date, report_type, comp_type,
             net_cash_flows_oper_act, net_cash_flows_inv_act, net_cash_flows_fnc_act, free_cashflow)
            VALUES (%(ts_code)s, %(ann_date)s, %(f_ann_date)s, %(end_date)s, %(report_type)s, %(comp_type)s,
                    %(net_cash_flows_oper_act)s, %(net_cash_flows_inv_act)s, %(net_cash_flows_fnc_act)s, %(free_cashflow)s)
            ON DUPLICATE KEY UPDATE
                ann_date = VALUES(ann_date),
                net_cash_flows_oper_act = VALUES(net_cash_flows_oper_act),
                free_cashflow = VALUES(free_cashflow),
                updated_at = CURRENT_TIMESTAMP
        """
        for item in data:
            for d_key in ["ann_date", "f_ann_date", "end_date"]:
                if item.get(d_key):
                    d = item[d_key]
                    item[d_key] = f"{d[:4]}-{d[4:6]}-{d[6:]}"
            # 字段映射
            for ts_key, db_key in mapping.items():
                if ts_key in item:
                    item[db_key] = item.pop(ts_key)
            for col in ["net_cash_flows_oper_act", "net_cash_flows_inv_act", "net_cash_flows_fnc_act", "free_cashflow"]:
                if col not in item:
                    item[col] = None
                    
        await db.execute_many(sql, data)
        return len(data)

    async def sync_indicators(self, ts_code: str, period: Optional[str] = None) -> int:
        params = {"ts_code": ts_code}
        if period:
            params["period"] = period
            
        res = await http_client.get("tushare", "/api/v1/fina_indicator", params=params)
        data = res.get("data", [])
        if not data:
            return 0
            
        sql = """
            INSERT INTO ods_fin_indicators
            (ts_code, ann_date, end_date, eps, dt_eps, total_revenue_ps, revenue_ps,
             capital_rese_ps, undist_profit_ps, roe, roe_dt, roa, netprofit_margin,
             grossprofit_margin, debt_to_assets, current_ratio, quick_ratio)
            VALUES (%(ts_code)s, %(ann_date)s, %(end_date)s, %(eps)s, %(dt_eps)s, %(total_revenue_ps)s, %(revenue_ps)s,
                    %(capital_rese_ps)s, %(undist_profit_ps)s, %(roe)s, %(roe_dt)s, %(roa)s, %(netprofit_margin)s,
                    %(grossprofit_margin)s, %(debt_to_assets)s, %(current_ratio)s, %(quick_ratio)s)
            ON DUPLICATE KEY UPDATE
                ann_date = VALUES(ann_date),
                roe = VALUES(roe),
                grossprofit_margin = VALUES(grossprofit_margin),
                updated_at = CURRENT_TIMESTAMP
        """
        for item in data:
            for d_key in ["ann_date", "end_date"]:
                if item.get(d_key):
                    d = item[d_key]
                    item[d_key] = f"{d[:4]}-{d[4:6]}-{d[6:]}"
            for col in ["eps", "dt_eps", "total_revenue_ps", "revenue_ps", "capital_rese_ps", "undist_profit_ps",
                        "roe", "roe_dt", "roa", "netprofit_margin", "grossprofit_margin", "debt_to_assets",
                        "current_ratio", "quick_ratio"]:
                if col not in item:
                    item[col] = None
                    
        await db.execute_many(sql, data)
        return len(data)

    async def sync_daily_disclosures(self, trade_date: str):
        """扫描当日披露的股票并触发同步"""
        t_date = trade_date.replace("-", "")
        res = await http_client.get("tushare", "/api/v1/disclosure_date", params={"actual_date": t_date})
        disclosures = res.get("data", [])
        
        if not disclosures:
            logger.info(f"日期 {trade_date} 无财报披露")
            return 0
            
        success_count = 0
        for disc in disclosures:
            ts_code = disc.get("ts_code")
            end_date = disc.get("end_date") # 报告期
            if ts_code:
                try:
                    await self.sync_all_financial_data(ts_code, period=end_date)
                    success_count += 1
                except Exception as e:
                    logger.error(f"同步股票 {ts_code} 报表失败: {e}")
                    
        return success_count
