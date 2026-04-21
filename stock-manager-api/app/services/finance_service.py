from typing import List, Dict, Any, Optional
from app.utils.database import db
from app.utils.http_client import http_client
from app.utils.logger import get_logger
import aiomysql

logger = get_logger("stock-manager.finance")

class FinanceService:
    """财务报表服务"""

    async def get_financial_reports(self, ts_code: str, limit: int = 40) -> Dict[str, Any]:
        """从数据库查询三大报表数据"""
        
        # 1. 资产负债表
        sql_bs = """
            SELECT ts_code, report_date, notice_date, total_assets, total_liabilities, 
                   total_equity, total_equity_ato_parent, monetary_funds, accounts_receivable, 
                   notes_receivable, inventory, goodwill, short_term_borrowings, 
                   long_term_borrowings, total_non_current_assets, total_current_assets, 
                   total_non_current_liabilities, total_current_liabilities
            FROM stock_balance_sheet 
            WHERE ts_code = %s 
            ORDER BY report_date DESC LIMIT %s
        """
        
        # 2. 利润表
        sql_is = """
            SELECT ts_code, report_date, notice_date, total_revenue, operating_revenue, 
                   total_operating_cost, operating_cost, selling_expenses, administrative_expenses, 
                   financial_expenses, research_expenses, operating_profit, total_profit, 
                   net_profit, parent_net_profit, deducted_net_profit, ebit, ebitda
            FROM stock_income_statement 
            WHERE ts_code = %s 
            ORDER BY report_date DESC LIMIT %s
        """
        
        # 3. 现金流量表
        sql_cf = """
            SELECT ts_code, report_date, notice_date, net_operating_cash_flow, 
                   net_investing_cash_flow, net_financing_cash_flow, capex, 
                   free_cash_flow, cash_and_equivalents_at_end
            FROM stock_cash_flow_statement 
            WHERE ts_code = %s 
            ORDER BY report_date DESC LIMIT %s
        """
        
        # 使用 DictCursor 简化映射
        async def fetch_dict(query, params):
            if not db.pool:
                await db.connect()
            async with db.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(query, params)
                    return await cur.fetchall()

        bs_rows = await fetch_dict(sql_bs, (ts_code, limit))
        is_rows = await fetch_dict(sql_is, (ts_code, limit))
        cf_rows = await fetch_dict(sql_cf, (ts_code, limit))
        
        return {
            "ts_code": ts_code,
            "balance_sheets": bs_rows,
            "income_statements": is_rows,
            "cash_flow_statements": cf_rows
        }

    async def sync_financial_reports(self, ts_code: str) -> Dict[str, Any]:
        """从数据源同步财务报表"""
        try:
            # 1. 从 AkShare API 获取历史报表
            # 注意：ts_code 格式处理在 AkShare 端完成
            data = await http_client.get("akshare", f"/api/v1/finance/historical/{ts_code}")
            if not data:
                return {"ts_code": ts_code, "success": False, "message": "No data from source"}
            
            ts_code = data.get("code", ts_code)
            bs_data = data.get("balance_sheets", [])
            is_data = data.get("income_statements", [])
            cf_data = data.get("cash_flow_statements", [])
            
            # 2. 批量入库
            count_bs = await self._save_balance_sheets(ts_code, bs_data)
            count_is = await self._save_income_statements(ts_code, is_data)
            count_cf = await self._save_cash_flow_statements(ts_code, cf_data)
            
            return {
                "ts_code": ts_code,
                "success": True,
                "count_bs": count_bs,
                "count_is": count_is,
                "count_cf": count_cf
            }
        except Exception as e:
            logger.error(f"Sync finance failed for {ts_code}: {e}")
            return {"ts_code": ts_code, "success": False, "message": str(e)}

    async def get_financial_indicators(self, ts_code: str, limit: int = 40) -> Dict[str, Any]:
        """从数据库查询财务衍生指标 (ROE, EPS等)"""
        sql = """
            SELECT ts_code, report_date, roe, roa, netprofit_margin, grossprofit_margin, 
                   asset_liab_ratio, current_ratio, eps
            FROM stock_finance_indicators 
            WHERE ts_code = %s 
            ORDER BY report_date DESC LIMIT %s
        """
        if not db.pool:
            await db.connect()
        async with db.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, (ts_code, limit))
                rows = await cur.fetchall()
        
        return {
            "ts_code": ts_code,
            "indicators": rows
        }

    async def sync_financial_indicators(self, ts_code: str) -> Dict[str, Any]:
        """从数据源同步财务衍生指标"""
        try:
            # 1. 从 AkShare API 获取分析指标
            data = await http_client.get("akshare", f"/api/v1/finance/analysis-indicators/{ts_code}")
            if not data or "indicators" not in data:
                return {"ts_code": ts_code, "success": False, "message": "No indicator data from source"}
            
            indicators = data.get("indicators", [])
            
            # 2. 批量入库
            count = await self._save_financial_indicators(ts_code, indicators)
            
            return {
                "ts_code": ts_code,
                "success": True,
                "count": count
            }
        except Exception as e:
            logger.error(f"Sync indicators failed for {ts_code}: {e}")
            return {"ts_code": ts_code, "success": False, "message": str(e)}

    async def _save_financial_indicators(self, ts_code: str, data: List[Dict[str, Any]]) -> int:
        if not data: return 0
        sql = """
            INSERT INTO stock_finance_indicators 
            (ts_code, report_date, roe, roa, netprofit_margin, grossprofit_margin, 
             asset_liab_ratio, current_ratio, eps)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                roe = VALUES(roe),
                roa = VALUES(roa),
                netprofit_margin = VALUES(netprofit_margin),
                grossprofit_margin = VALUES(grossprofit_margin),
                asset_liab_ratio = VALUES(asset_liab_ratio),
                current_ratio = VALUES(current_ratio),
                eps = VALUES(eps),
                updated_at = CURRENT_TIMESTAMP
        """
        rows = []
        for item in data:
            rows.append((
                ts_code, item.get("report_date"), 
                item.get("roe"), item.get("roa"), 
                item.get("netprofit_margin"), item.get("grossprofit_margin"),
                item.get("asset_liab_ratio"), item.get("current_ratio"),
                item.get("eps")
            ))
        await db.execute_many(sql, rows)
        return len(rows)

    async def _save_balance_sheets(self, ts_code: str, data: List[Dict[str, Any]]) -> int:
        if not data: return 0
        sql = """
            INSERT INTO stock_balance_sheet 
            (ts_code, report_date, notice_date, total_assets, total_liabilities, 
             total_equity, total_equity_ato_parent, monetary_funds, accounts_receivable, 
             notes_receivable, inventory, goodwill, short_term_borrowings, 
             long_term_borrowings, total_non_current_assets, total_current_assets, 
             total_non_current_liabilities, total_current_liabilities)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                notice_date = VALUES(notice_date),
                total_assets = VALUES(total_assets),
                total_liabilities = VALUES(total_liabilities),
                total_equity = VALUES(total_equity),
                total_equity_ato_parent = VALUES(total_equity_ato_parent),
                updated_at = CURRENT_TIMESTAMP
        """
        rows = []
        for item in data:
            rows.append((
                ts_code, item.get("report_date"), item.get("notice_date"),
                item.get("total_assets"), item.get("total_liabilities"),
                item.get("total_equity"), item.get("total_equity_ato_parent"),
                item.get("monetary_funds"), item.get("accounts_receivable"),
                item.get("notes_receivable"), item.get("inventory"),
                item.get("goodwill"), item.get("short_term_borrowings"),
                item.get("long_term_borrowings"), item.get("total_non_current_assets"),
                item.get("total_current_assets"), item.get("total_non_current_liabilities"),
                item.get("total_current_liabilities")
            ))
        await db.execute_many(sql, rows)
        return len(rows)

    async def _save_income_statements(self, ts_code: str, data: List[Dict[str, Any]]) -> int:
        if not data: return 0
        sql = """
            INSERT INTO stock_income_statement 
            (ts_code, report_date, notice_date, total_revenue, operating_revenue, 
             total_operating_cost, operating_cost, selling_expenses, administrative_expenses, 
             financial_expenses, research_expenses, operating_profit, total_profit, 
             net_profit, parent_net_profit, deducted_net_profit, ebit, ebitda)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                notice_date = VALUES(notice_date),
                total_revenue = VALUES(total_revenue),
                net_profit = VALUES(net_profit),
                parent_net_profit = VALUES(parent_net_profit),
                updated_at = CURRENT_TIMESTAMP
        """
        rows = []
        for item in data:
            rows.append((
                ts_code, item.get("report_date"), item.get("notice_date"),
                item.get("total_revenue"), item.get("operating_revenue"),
                item.get("total_operating_cost"), item.get("operating_cost"),
                item.get("selling_expenses"), item.get("administrative_expenses"),
                item.get("financial_expenses"), item.get("research_expenses"),
                item.get("operating_profit"), item.get("total_profit"),
                item.get("net_profit"), item.get("parent_net_profit"),
                item.get("deducted_net_profit"), item.get("ebit"), item.get("ebitda")
            ))
        await db.execute_many(sql, rows)
        return len(rows)

    async def _save_cash_flow_statements(self, ts_code: str, data: List[Dict[str, Any]]) -> int:
        if not data: return 0
        sql = """
            INSERT INTO stock_cash_flow_statement 
            (ts_code, report_date, notice_date, net_operating_cash_flow, 
             net_investing_cash_flow, net_financing_cash_flow, capex, 
             free_cash_flow, cash_and_equivalents_at_end)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                notice_date = VALUES(notice_date),
                net_operating_cash_flow = VALUES(net_operating_cash_flow),
                free_cash_flow = VALUES(free_cash_flow),
                updated_at = CURRENT_TIMESTAMP
        """
        rows = []
        for item in data:
            rows.append((
                ts_code, item.get("report_date"), item.get("notice_date"),
                item.get("net_operating_cash_flow"), item.get("net_investing_cash_flow"),
                item.get("net_financing_cash_flow"), item.get("capex"),
                item.get("free_cash_flow"), item.get("cash_and_equivalents_at_end")
            ))
        await db.execute_many(sql, rows)
        return len(rows)
