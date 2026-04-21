from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import date

class FinancialReportBase(BaseModel):
    ts_code: str
    report_date: date
    notice_date: Optional[date] = None

# --- 资产负债表 ---
class BalanceSheetResponse(FinancialReportBase):
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    total_equity: Optional[float] = None
    total_equity_ato_parent: Optional[float] = None
    monetary_funds: Optional[float] = None
    accounts_receivable: Optional[float] = None
    notes_receivable: Optional[float] = None
    inventory: Optional[float] = None
    goodwill: Optional[float] = None
    short_term_borrowings: Optional[float] = None
    long_term_borrowings: Optional[float] = None
    total_non_current_assets: Optional[float] = None
    total_current_assets: Optional[float] = None
    total_non_current_liabilities: Optional[float] = None
    total_current_liabilities: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

# --- 利润表 ---
class IncomeStatementResponse(FinancialReportBase):
    total_revenue: Optional[float] = None
    operating_revenue: Optional[float] = None
    total_operating_cost: Optional[float] = None
    operating_cost: Optional[float] = None
    selling_expenses: Optional[float] = None
    administrative_expenses: Optional[float] = None
    financial_expenses: Optional[float] = None
    research_expenses: Optional[float] = None
    operating_profit: Optional[float] = None
    total_profit: Optional[float] = None
    net_profit: Optional[float] = None
    parent_net_profit: Optional[float] = None
    deducted_net_profit: Optional[float] = None
    ebit: Optional[float] = None
    ebitda: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

# --- 现金流量表 ---
class CashFlowStatementResponse(FinancialReportBase):
    net_operating_cash_flow: Optional[float] = None
    net_investing_cash_flow: Optional[float] = None
    net_financing_cash_flow: Optional[float] = None
    capex: Optional[float] = None
    free_cash_flow: Optional[float] = None
    cash_and_equivalents_at_end: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

# --- 综合响应 ---
class FullFinancialReportResponse(BaseModel):
    ts_code: str
    balance_sheets: List[BalanceSheetResponse]
    income_statements: List[IncomeStatementResponse]
    cash_flow_statements: List[CashFlowStatementResponse]

# --- 财务衍生指标 ---
class FinanceIndicatorResponse(BaseModel):
    ts_code: str
    report_date: date
    roe: Optional[float] = None
    roa: Optional[float] = None
    netprofit_margin: Optional[float] = None
    grossprofit_margin: Optional[float] = None
    asset_liab_ratio: Optional[float] = None
    current_ratio: Optional[float] = None
    eps: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

class FinancialIndicatorsListResponse(BaseModel):
    ts_code: str
    indicators: List[FinanceIndicatorResponse]

class SyncFinanceResult(BaseModel):
    ts_code: str
    success: bool
    count_bs: int
    count_is: int
    count_cf: int
    message: str = ""

class SyncFinanceIndicatorsResult(BaseModel):
    ts_code: str
    success: bool
    count: int
    message: str = ""
