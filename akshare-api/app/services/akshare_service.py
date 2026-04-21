import asyncio
import math
import gc
import httpx
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
import akshare as ak
import pandas as pd
from app.utils.logger import get_logger

logger = get_logger("akshare-api.service")

class AkShareService:
    """AkShare 数据服务封装
    
    提供对 AkShare 库的异步封装，所有同步 I/O 操作通过 asyncio.to_thread 在线程池中执行。
    """
    
    def _clean_value(self, val: Any, default: Any = None) -> Optional[float]:
        """清洗并转换数值（处理“1.2亿”, “-3.5%”, “NaN”, “None”等）"""
        if val is None or val is False:
            return default
            
        # 处理数值类型
        if isinstance(val, (int, float)):
            if math.isnan(val) or math.isinf(val):
                return default
            return float(val)
            
        s = str(val).strip()
        if not s or s.lower() in ['nan', 'none', 'false', '-', '--']:
            return default
            
        try:
            # 处理百分比
            multiplier = 1.0
            if s.endswith('%'):
                multiplier = 0.01
                s = s[:-1].strip()
            
            # 处理单位
            if s.endswith('亿'):
                multiplier *= 100000000
                s = s[:-1].strip()
            elif s.endswith('万'):
                multiplier *= 10000
                s = s[:-1].strip()
                
            final_val = float(s) * multiplier
            if math.isnan(final_val) or math.isinf(final_val):
                return default
            return final_val
        except (ValueError, TypeError):
            return default

    async def get_financial_abstract(self, symbol: str) -> Optional[Dict[str, Any]]:
        """异步获取财务摘要
        
        支持多种 AkShare 返回格式（长格式、宽格式、中英文指标名）。
        """
        try:
            df = await asyncio.to_thread(ak.stock_financial_abstract_ths, symbol=symbol)
            
            if df is None or df.empty:
                return None
            
            result = {
                "total_revenue": None,
                "net_profit": None,
                "roe": None,
                "report_date": None,
            }

            # 格式 A: 长格式 (report_date, metric_name, value ...)
            if 'metric_name' in df.columns and 'value' in df.columns:
                latest_report = df['report_date'].iloc[0] if 'report_date' in df.columns else None
                result["report_date"] = str(latest_report) if latest_report else None
                
                # 指标映射 (英文 -> 结果键)
                mapping = {
                    'operating_income_total': 'total_revenue',
                    'parent_holder_net_profit': 'net_profit',
                    'index_weighted_avg_roe': 'roe',
                }
                
                for _, row in df.iterrows():
                    m_name = row.get('metric_name')
                    if m_name in mapping:
                        result[mapping[m_name]] = self._clean_value(row.get('value'))

            # 格式 B: 宽格式 (报告期, 营业总收入, 净利润 ...)
            else:
                # 确定最新一行（通常是首行或尾行，根据日期判断）
                # 为了稳妥，按日期排序
                date_col = '报告期' if '报告期' in df.columns else ('report_date' if 'report_date' in df.columns else None)
                if date_col:
                    df = df.sort_values(by=date_col, ascending=False)
                    latest = df.iloc[0]
                    result["report_date"] = str(latest[date_col])
                    
                    # 字段映射 (中文 -> 结果键)
                    mapping = {
                        '营业总收入': 'total_revenue',
                        '净利润': 'net_profit',
                        '净资产收益率': 'roe',
                    }
                    
                    for cn_name, key in mapping.items():
                        if cn_name in df.columns:
                            result[key] = self._clean_value(latest[cn_name])

            return result
        except Exception as e:
            logger.error(f"AkShare获取财务摘要失败: symbol={symbol}, error={e}")
            return None

    async def get_valuation_spot(self, symbol: str) -> Optional[Dict[str, Any]]:
        """异步获取实时估值 (优化版: 直接调用接口, 避免 OOM)"""
        try:
            # 转换代码格式 6xxxx -> 1.6xxxx, 0xxxx -> 0.0xxxx
            secid = ""
            code = symbol
            if "." in symbol:
                code = symbol.split(".")[0]
            
            if code.startswith("6") or code.startswith("11") or code.startswith("9"):
                secid = f"1.{code}"
            else:
                secid = f"0.{code}"
            
            url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f57,f58,f162,f167,f116,f43"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return None
                
                data_json = resp.json()
                if not data_json or "data" not in data_json or not data_json["data"]:
                    return None
                
                d = data_json["data"]
                # f58=名称, f43=最新价, f162=PE-动, f167=PB, f116=总市值
                # EM 价格/PE/PB 通常带 2 位小数(即 *100)
                return {
                    "name": d.get("f58", ""),
                    "pe": self._clean_value(d.get("f162")) / 100.0 if d.get("f162") is not None else None,
                    "pb": self._clean_value(d.get("f167")) / 100.0 if d.get("f167") is not None else None,
                    "market_cap": self._clean_value(d.get("f116")),
                    "price": self._clean_value(d.get("f43")) / 100.0 if d.get("f43") is not None else None,
                }
        except Exception as e:
            logger.error(f"直接获取实时估值失败: symbol={symbol}, error={e}")
            # 如果直调失败, 且内存允许, 尝试回退到 ak (极小概率成功)
            return None
        finally:
            gc.collect()

    async def get_lhb_detail(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """异步获取龙虎榜详情"""
        try:
            target_date = start_date
            
            # 如果未指定日期，自动获取最近一个交易日
            if not target_date:
                try:
                    trade_days = await asyncio.to_thread(ak.tool_trade_date_hist_sina)
                    if not trade_days.empty:
                        # 过滤掉未来的日期
                        today = date.today()
                        past_days = trade_days[trade_days['trade_date'] <= today]
                        if not past_days.empty:
                            target_date = str(past_days.iloc[-1]['trade_date'])
                        else:
                            target_date = datetime.now().strftime("%Y-%m-%d")
                except Exception as date_e:
                    logger.warning(f"获取交易日历失败，使用当前日期回退: {date_e}")
                    target_date = datetime.now().strftime("%Y-%m-%d")

            # 转换格式为 YYYYMMDD
            sd = target_date.replace("-", "")
            ed = (end_date or target_date).replace("-", "")
            
            logger.info(f"请求龙虎榜详情: start_date={sd}, end_date={ed}")
            try:
                df = await asyncio.to_thread(ak.stock_lhb_detail_em, start_date=sd, end_date=ed)
            except Exception as ak_e:
                logger.warning(f"AkShare 原始龙虎榜调用出错: {ak_e}, 可能是数据尚未更新")
                df = None
                
            # 如果今日数据为空且未指定结束日期，尝试回退到上一个交易日
            if (df is None or (hasattr(df, 'empty') and df.empty)) and not end_date:
                try:
                    trade_days = await asyncio.to_thread(ak.tool_trade_date_hist_sina)
                    today = date.today()
                    past_days = trade_days[trade_days['trade_date'] < today] # 严格小于今天
                    if not past_days.empty:
                        prev_date = str(past_days.iloc[-1]['trade_date']).replace("-", "")
                        logger.info(f"今日数据未更新，尝试回退至上一交易日: {prev_date}")
                        try:
                            df = await asyncio.to_thread(ak.stock_lhb_detail_em, start_date=prev_date, end_date=prev_date)
                        except Exception as fallback_ak_e:
                            logger.error(f"龙虎榜回退调用失败: {fallback_ak_e}")
                            df = None
                except Exception as fallback_e:
                    logger.error(f"龙虎榜回退逻辑计算失败: {fallback_e}")

            if df is None or not hasattr(df, 'empty') or df.empty:
                logger.info(f"龙虎榜详情最终返回为空")
                return []
                
            df = df.head(100)
            result = []
            for _, row in df.iterrows():
                result.append({
                    "code": row.get("代码", ""),
                    "name": row.get("名称", ""),
                    "close": self._clean_value(row.get("收盘价")),
                    "change_pct": self._clean_value(row.get("涨跌幅")),
                    "turnover_rate": self._clean_value(row.get("换手率")),
                    "net_buy": self._clean_value(row.get("龙虎榜净买额")),
                    "reason": row.get("上榜原因", ""),
                    "date": str(row.get("上榜日", "")),
                })
            return result
        except Exception as e:
            logger.error(f"AkShare获取龙虎榜总成失败: error={e}")
            return []

    async def get_individual_info(self, symbol: str) -> Dict[str, Any]:
        """异步获取个股详情"""
        try:
            df = await asyncio.to_thread(ak.stock_individual_info_em, symbol=symbol)
            if df is None or df.empty:
                return {}
                
            info = {}
            for _, row in df.iterrows():
                item = row.get("item", "")
                value = row.get("value", "")
                if item == "行业": info["industry"] = value
                elif item == "股票简称": info["name"] = value
                elif item == "上市时间": info["list_date"] = value
                elif item == "总股本": info["total_share"] = value
            return info
        except Exception as e:
            logger.error(f"AkShare获取个股信息失败: symbol={symbol}, error={e}")
            return {}

    async def get_hot_rank(self, limit: int = 50) -> List[Dict[str, Any]]:
        """异步获取热门排行(以成交额为准) - 优化版"""
        try:
            # 使用更专用的热门板块/排行接口, 避免拉取全量 5000+ 股票
            # 这里如果不允许直连, 只能用 ak.stock_zh_a_spot_em. 
            # 为了内存安全, 直接调用 EM 接口获取排行
            url = f"https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz={limit}&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f6&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:7,m:1+t:3&fields=f12,f14,f2,f3,f5,f6,f8"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return []
                
                data_json = resp.json()
                if not data_json or "data" not in data_json or "diff" not in data_json["data"]:
                    return []
                
                result = []
                for d in data_json["data"]["diff"]:
                    # f12=代码, f14=名称, f2=最新价, f3=涨跌幅, f5=成交量, f6=成交额, f8=换手
                    result.append({
                        "code": d.get("f12", ""),
                        "name": d.get("f14", ""),
                        "price": self._clean_value(d.get("f2")) / 100.0 if d.get("f2") is not None else None,
                        "change_pct": self._clean_value(d.get("f3")) / 100.0 if d.get("f3") is not None else None,
                        "volume": self._clean_value(d.get("f5")),
                        "amount": self._clean_value(d.get("f6")),
                        "turnover_rate": self._clean_value(d.get("f8")) / 100.0 if d.get("f8") is not None else None,
                    })
                return result
        except Exception as e:
            logger.error(f"快速获取热门排行失败: error={e}")
            return []
        finally:
            gc.collect()

    async def get_full_financial_report(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取全量财务指标 (EPIC-002)
        
        通过整合资产负债表、利润表和现金流量表，提供计算型指标（EBITDA, FCF等）。
        """
        try:
            # 统一 symbol 格式
            s = str(symbol)
            if not (s.startswith("SH") or s.startswith("SZ") or s.startswith("BJ")):
                if s.startswith("6") or s.startswith("9") or s.startswith("11"): s = "SH" + s
                else: s = "SZ" + s
            
            logger.info(f"开始获取全量财务报表: {s}")
            
            # 并发获取三张表 (使用 report_em 接口，包含最新未审计数据)
            tasks = [
                asyncio.to_thread(ak.stock_balance_sheet_by_report_em, symbol=s),
                asyncio.to_thread(ak.stock_profit_sheet_by_report_em, symbol=s),
                asyncio.to_thread(ak.stock_cash_flow_sheet_by_report_em, symbol=s)
            ]
            dfs = await asyncio.gather(*tasks)
            df_bs, df_ps, df_cf = dfs
            
            if df_bs is None or df_bs.empty or df_ps is None or df_ps.empty or df_cf is None or df_cf.empty:
                logger.warning(f"未能获取完整的三大报表数据: {s}")
                return None
            
            # 获取最新一期的报告日期 (首行)
            bs_latest = df_bs.iloc[0]
            ps_latest = df_ps.iloc[0]
            cf_latest = df_cf.iloc[0]
            
            report_date = str(bs_latest.get("REPORT_DATE_NAME", bs_latest.get("REPORT_DATE", "")))
            
            # --- 映射核心字段 ---
            res = {
                "report_date": report_date.split(" ")[0] if report_date else None,
                # 资产负债 (BS)
                "total_assets": self._clean_value(bs_latest.get("TOTAL_ASSETS")),
                "total_liabilities": self._clean_value(bs_latest.get("TOTAL_LIABILITIES")),
                "total_equity": self._clean_value(bs_latest.get("TOTAL_PARENT_EQUITY", bs_latest.get("TOTAL_EQUITY"))),
                "monetary_funds": self._clean_value(bs_latest.get("MONETARYFUNDS")),
                "inventory": self._clean_value(bs_latest.get("INVENTORY")),
                "accounts_receivable": self._clean_value(bs_latest.get("NOTE_ACCOUNTS_RECE")),
                "goodwill": self._clean_value(bs_latest.get("GOODWILL")),
                "short_term_loans": self._clean_value(bs_latest.get("SHORT_LOAN")),
                "long_term_loans": self._clean_value(bs_latest.get("LONG_LOAN")),
                "bond_payable": self._clean_value(bs_latest.get("BOND_PAYABLE")),
                
                # 利润表 (PS)
                "operating_income": self._clean_value(ps_latest.get("TOTAL_OPERATE_INCOME")),
                "operating_cost": self._clean_value(ps_latest.get("OPERATE_COST")),
                "selling_expenses": self._clean_value(ps_latest.get("SALE_EXPENSE")),
                "administrative_expenses": self._clean_value(ps_latest.get("MANAGE_EXPENSE")),
                "finance_expenses": self._clean_value(ps_latest.get("FINANCE_EXPENSE")),
                "research_expenses": self._clean_value(ps_latest.get("RESEARCH_EXPENSE")),
                "operating_profit": self._clean_value(ps_latest.get("OPERATE_PROFIT")),
                "total_profit": self._clean_value(ps_latest.get("TOTAL_PROFIT")),
                "net_profit": self._clean_value(ps_latest.get("NETPROFIT", ps_latest.get("NET_PROFIT"))),
                "parent_net_profit": self._clean_value(ps_latest.get("PARENT_NETPROFIT", ps_latest.get("PARENT_NET_PROFIT"))),
                
                # 现金流 (CF)
                "net_operating_cash_flow": self._clean_value(cf_latest.get("NETCASH_OPERATE")),
                "net_investing_cash_flow": self._clean_value(cf_latest.get("NETCASH_INVEST")),
                "net_financing_cash_flow": self._clean_value(cf_latest.get("NETCASH_FINANCE")),
                "capex": self._clean_value(cf_latest.get("CONSTRUCT_LONG_ASSET")),
            }
            
            # --- 计算派生指标 ---
            # 1. 毛利
            if res["operating_income"] is not None and res["operating_cost"] is not None:
                res["gross_profit"] = res["operating_income"] - res["operating_cost"]
            else:
                res["gross_profit"] = None
                
            # 2. EBIT (Total Profit + Interest Expense)
            # 这里的利息支出通常取 FE_INTEREST_EXPENSE
            interest_expense = self._clean_value(ps_latest.get("FE_INTEREST_EXPENSE")) or 0
            if res["total_profit"] is not None:
                res["ebit"] = res["total_profit"] + interest_expense
            else:
                res["ebit"] = None
                
            # 3. EBITDA (EBIT + Depreciation + Amortization)
            depr = self._clean_value(cf_latest.get("FA_IR_DEPR")) or 0
            amort1 = self._clean_value(cf_latest.get("IA_AMORTIZE")) or 0
            amort2 = self._clean_value(cf_latest.get("LPE_AMORTIZE")) or 0
            amort_all = depr + amort1 + amort2
            
            if res["ebit"] is not None:
                res["ebitda"] = res["ebit"] + amort_all
            else:
                res["ebitda"] = None
                
            # 4. FCF (Net Operating Cash Flow - CAPEX)
            if res["net_operating_cash_flow"] is not None:
                res["fcf"] = res["net_operating_cash_flow"] - (res["capex"] or 0)
            else:
                res["fcf"] = None
            return res
        except Exception as e:
            logger.error(f"AkShare获取全量财务指标失败: symbol={symbol}, error={e}", exc_info=True)
            return None

    async def get_historical_financial_report(self, symbol: str) -> Optional[Dict[str, List[Dict[str, Any]]]]:
        """获取历史所有维度的财务报表数据 (盈利锚核心数据)
        
        返回包含资产负债表、利润表、现金流量表列表的字典。
        """
        try:
            # 统一 symbol 格式
            s = str(symbol)
            if not (s.startswith("SH") or s.startswith("SZ") or s.startswith("BJ")):
                if s.startswith("6") or s.startswith("9") or s.startswith("11"): s = "SH" + s
                else: s = "SZ" + s
            
            logger.info(f"开始获取历史全量财务报表: {s}")
            
            # 并发获取三张表
            tasks = [
                asyncio.to_thread(ak.stock_balance_sheet_by_report_em, symbol=s),
                asyncio.to_thread(ak.stock_profit_sheet_by_report_em, symbol=s),
                asyncio.to_thread(ak.stock_cash_flow_sheet_by_report_em, symbol=s)
            ]
            dfs = await asyncio.gather(*tasks)
            df_bs, df_ps, df_cf = dfs
            
            if df_bs is None or df_bs.empty:
                logger.warning(f"未能获取资产负债表数据: {s}")
                return None

            # --- 1. 资产负债表处理 ---
            balance_sheets = []
            for _, row in df_bs.iterrows():
                report_date = row.get("REPORT_DATE")
                notice_date = row.get("NOTICE_DATE")
                
                # 清洗日期: 处理 NaN 或非字符串情况
                clean_report_date = str(report_date).split(" ")[0] if pd.notna(report_date) else None
                clean_notice_date = str(notice_date).split(" ")[0] if pd.notna(notice_date) else None
                
                balance_sheets.append({
                    "report_date": clean_report_date,
                    "notice_date": clean_notice_date,
                    "total_assets": self._clean_value(row.get("TOTAL_ASSETS")),
                    "total_liabilities": self._clean_value(row.get("TOTAL_LIABILITIES")),
                    "total_equity": self._clean_value(row.get("TOTAL_EQUITY")),
                    "total_equity_ato_parent": self._clean_value(row.get("TOTAL_PARENT_EQUITY")),
                    "monetary_funds": self._clean_value(row.get("MONETARYFUNDS")),
                    "accounts_receivable": self._clean_value(row.get("NOTE_ACCOUNTS_RECE")),
                    "inventory": self._clean_value(row.get("INVENTORY")),
                    "goodwill": self._clean_value(row.get("GOODWILL")),
                    "short_term_borrowings": self._clean_value(row.get("SHORT_LOAN")),
                    "long_term_borrowings": self._clean_value(row.get("LONG_LOAN")),
                    "total_current_assets": self._clean_value(row.get("TOTAL_CURRENT_ASSETS")),
                    "total_non_current_assets": self._clean_value(row.get("TOTAL_NON_CURRENT_ASSETS")),
                    "total_current_liabilities": self._clean_value(row.get("TOTAL_CURRENT_LIABILITIES")),
                    "total_non_current_liabilities": self._clean_value(row.get("TOTAL_NON_CURRENT_LIABILITIES")),
                })

            # --- 2. 利润表处理 ---
            income_statements = []
            if df_ps is not None and not df_ps.empty:
                for _, row in df_ps.iterrows():
                    report_date = row.get("REPORT_DATE")
                    notice_date = row.get("NOTICE_DATE")
                    clean_report_date = str(report_date).split(" ")[0] if pd.notna(report_date) else None
                    clean_notice_date = str(notice_date).split(" ")[0] if pd.notna(notice_date) else None
                    
                    # 计算 ebit/ebitda (简化逻辑)
                    total_profit = self._clean_value(row.get("TOTAL_PROFIT"))
                    interest_exp = self._clean_value(row.get("FE_INTEREST_EXPENSE")) or 0
                    ebit = (total_profit + interest_exp) if total_profit is not None else None
                    
                    income_statements.append({
                        "report_date": clean_report_date,
                        "notice_date": clean_notice_date,
                        "total_revenue": self._clean_value(row.get("TOTAL_OPERATE_INCOME")),
                        "operating_revenue": self._clean_value(row.get("OPERATE_INCOME")),
                        "total_operating_cost": self._clean_value(row.get("TOTAL_OPERATE_COST")),
                        "operating_cost": self._clean_value(row.get("OPERATE_COST")),
                        "selling_expenses": self._clean_value(row.get("SALE_EXPENSE")),
                        "administrative_expenses": self._clean_value(row.get("MANAGE_EXPENSE")),
                        "financial_expenses": self._clean_value(row.get("FINANCE_EXPENSE")),
                        "research_expenses": self._clean_value(row.get("RESEARCH_EXPENSE")),
                        "operating_profit": self._clean_value(row.get("OPERATE_PROFIT")),
                        "total_profit": total_profit,
                        "net_profit": self._clean_value(row.get("NETPROFIT")),
                        "parent_net_profit": self._clean_value(row.get("PARENT_NETPROFIT")),
                        "deducted_net_profit": self._clean_value(row.get("DEDUCT_PARENT_NETPROFIT")),
                        "ebit": ebit,
                    })

            # --- 3. 现金流量表处理 ---
            cash_flows = []
            if df_cf is not None and not df_cf.empty:
                for _, row in df_cf.iterrows():
                    report_date = row.get("REPORT_DATE")
                    notice_date = row.get("NOTICE_DATE")
                    clean_report_date = str(report_date).split(" ")[0] if pd.notna(report_date) else None
                    clean_notice_date = str(notice_date).split(" ")[0] if pd.notna(notice_date) else None
                    
                    ocf = self._clean_value(row.get("NETCASH_OPERATE"))
                    capex = self._clean_value(row.get("CONSTRUCT_LONG_ASSET"))
                    fcf = (ocf - (capex or 0)) if ocf is not None else None
                    
                    cash_flows.append({
                        "report_date": clean_report_date,
                        "notice_date": clean_notice_date,
                        "net_operating_cash_flow": ocf,
                        "net_investing_cash_flow": self._clean_value(row.get("NETCASH_INVEST")),
                        "net_financing_cash_flow": self._clean_value(row.get("NETCASH_FINANCE")),
                        "capex": capex,
                        "free_cash_flow": fcf,
                        "cash_and_equivalents_at_end": self._clean_value(row.get("CASH_EQUIVALENTS_END")),
                    })

            return {
                "balance_sheets": balance_sheets,
                "income_statements": income_statements,
                "cash_flows": cash_flows
            }
        except Exception as e:
            logger.error(f"AkShare获取历史全量财务指标失败: symbol={symbol}, error={e}", exc_info=True)
            return None

    async def get_financial_analysis_indicators(self, symbol: str) -> List[Dict[str, Any]]:
        """获取财务分析指标 (ROE, ROA, 毛利率, 资产负债率, EPS等)
        
        接口: ak.stock_financial_analysis_indicator_em
        参数格式要求: 600519.SH / 000001.SZ
        """
        try:
            s = str(symbol)
            # 转换为 600519.SH 格式
            if "." not in s:
                if s.startswith("6") or s.startswith("9") or s.startswith("11"): s = s + ".SH"
                else: s = s + ".SZ"
            elif s.startswith("SH") or s.startswith("SZ"):
                # 处理 SH600519 到 600519.SH
                prefix = s[:2]
                code = s[2:]
                s = f"{code}.{prefix}"
            
            logger.info(f"开始获取历史财务分析指标: {s}")
            df = await asyncio.to_thread(ak.stock_financial_analysis_indicator_em, symbol=s)
            
            if df is None or df.empty:
                logger.warning(f"未能获取财务分析指标数据: {s}")
                return []
            
            result = []
            for _, row in df.iterrows():
                report_date = row.get("REPORT_DATE")
                # 兼容不同格式的日期清洗
                clean_report_date = str(report_date).split(" ")[0] if pd.notna(report_date) else None
                
                result.append({
                    "report_date": clean_report_date,
                    "roe": self._clean_value(row.get("ROEJQ")),
                    "roa": self._clean_value(row.get("ZZCJLL")),
                    "netprofit_margin": self._clean_value(row.get("XSJLL")),
                    "grossprofit_margin": self._clean_value(row.get("XSMLL")),
                    "asset_liab_ratio": self._clean_value(row.get("ZCFZL")),
                    "current_ratio": self._clean_value(row.get("LD")),
                    "eps": self._clean_value(row.get("EPSJB")),
                })
            
            return result
        except Exception as e:
            logger.error(f"AkShare获取财务分析指标失败: symbol={symbol}, error={e}", exc_info=True)
            return []

    async def get_capital_flow(self, symbol: str) -> List[Dict[str, Any]]:
        """获取个股资金流向"""
        try:
            # 判断市场
            market = "sh" if symbol.startswith("6") or symbol.startswith("9") else "sz"
            # AkShare individual fund flow
            df = await asyncio.to_thread(ak.stock_individual_fund_flow, stock=symbol, market=market)
            if df is None or df.empty:
                return []
            
            # Use recent 30 days
            df = df.head(30)
            result = []
            for _, row in df.iterrows():
                result.append({
                    "date": str(row.get("日期", "")),
                    "close": self._clean_value(row.get("收盘价")),
                    "change_pct": self._clean_value(row.get("涨跌幅")),
                    "main_net_inflow": self._clean_value(row.get("主力净流入-净额")),
                    "main_net_inflow_pct": self._clean_value(row.get("主力净流入-净占比")),
                    "super_large_net_inflow": self._clean_value(row.get("超大单净流入-净额")),
                    "large_net_inflow": self._clean_value(row.get("大单净流入-净额")),
                    "medium_net_inflow": self._clean_value(row.get("中单净流入-净额")),
                    "small_net_inflow": self._clean_value(row.get("小单净流入-净额")),
                })
            return result
        except Exception as e:
            logger.error(f"AkShare获取资金流向失败: symbol={symbol}, error={e}")
            return []

    async def get_block_trade(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """获取大宗交易每日明细 (日期范围)"""
        try:
            # 清致日期格式 YYYY-MM-DD -> YYYYMMDD
            s_date = start_date.replace("-", "")
            e_date = end_date.replace("-", "")
            df = await asyncio.to_thread(ak.stock_dzjy_mrmx, symbol="A股", start_date=s_date, end_date=e_date)
            if df is None or df.empty:
                return []
            
            result = []
            for _, row in df.iterrows():
                result.append({
                    "code": row.get("证券代码", ""),
                    "name": row.get("证券简称", ""),
                    "price": self._clean_value(row.get("成交价")),
                    "volume": self._clean_value(row.get("成交量")),
                    "amount": self._clean_value(row.get("成交额")),
                    "buyer": row.get("买方营业部", ""),
                    "seller": row.get("卖方营业部", ""),
                    "date": str(row.get("交易日期", "")),
                })
            return result
        except Exception as e:
            logger.error(f"AkShare获取大宗交易失败: start={start_date}, end={end_date}, error={e}")
            return []

    async def get_margin_data(self, symbol: str) -> List[Dict[str, Any]]:
        """获取融资融券数据"""
        try:
            # 判断市场 (简易逻辑)
            # 6开头为沪市，其他暂认为深市/其他
            is_sh = str(symbol).startswith("6") or str(symbol).startswith("9")
            
            # 东方财富接口往往不要sh/sz前缀, 只要纯数字
            code = symbol
            if "." in code:
                code = code.split(".")[0]
            
            if symbol.startswith("6"):
                df = await asyncio.to_thread(ak.stock_margin_detail_sse, symbol=symbol)
            else:
                df = await asyncio.to_thread(ak.stock_margin_detail_szse, symbol=symbol)
                
            if df is None or df.empty:
                return []
                
            # Recent 30 records
            df = df.head(30)
            
            result = []
            for _, row in df.iterrows():
                op_date = row.get("信用交易日期") or row.get("日期")
                result.append({
                    "date": str(op_date),
                    # 融资 (Financing)
                    "financing_balance": self._clean_value(row.get("融资余额")),
                    "financing_buy": self._clean_value(row.get("融资买入额")),
                    "financing_repay": self._clean_value(row.get("融资偿还额")),
                    # 融券 (Securities Lending)
                    "lending_balance": self._clean_value(row.get("融券余额") or row.get("融券余量")), 
                    "lending_sell": self._clean_value(row.get("融券卖出量")), 
                    "lending_repay": self._clean_value(row.get("融券偿还量")),
                })
            return result
        except Exception as e:
            logger.error(f"AkShare获取融资融券失败: symbol={symbol}, error={e}")
            return []

    async def get_shareholder_info(self, symbol: str, all_history: bool = False) -> Dict[str, Any]:
        """获取股东信息 (户数 + 前十大) - 优化版: 直接调用接口避免 OOM
        
        :param symbol: 股票代码
        :param all_history: 是否获取上市以来的所有数据 (默认为 False, 仅获取最近/最新)
        """
        result = {
            "holder_count_history": [],
            "top10_holders": []
        }
        
        # 统一代码
        code = symbol.split(".")[0] if "." in symbol else symbol
        
        # Determine page size based on history request
        # 5000 records cover ~1000 years for quarterly data (4 * 1000 = 4000)
        page_size_count = 5000 if all_history else 10
        page_size_holders = 5000 if all_history else 20
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            # 1. 股东户数历史
            try:
                url_count = f"https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_F10_EH_HOLDERNUM&columns=ALL&filter=(SECURITY_CODE%3D%22{code}%22)&pageNumber=1&pageSize={page_size_count}"
                resp = await client.get(url_count)
                if resp.status_code == 200:
                    data_json = resp.json()
                    if data_json.get("success") and "result" in data_json and data_json["result"]:
                        items = data_json["result"].get("data", [])
                        for item in items:
                            result["holder_count_history"].append({
                                "date": item.get("END_DATE", "")[:10] if item.get("END_DATE") else "",
                                "count": item.get("HOLDER_TOTAL_NUM"),
                                "change": item.get("TOTAL_NUM_RATIO"),
                                "avg_market_cap": item.get("AVG_HOLD_AMT"),
                            })
            except Exception as e:
                logger.warning(f"直接获取股东户数失败: code={code}, error={e}")

            # 2. 前十大自由流通股东
            try:
                url_top10 = f"https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_F10_EH_FREEHOLDERS&columns=ALL&filter=(SECURITY_CODE%3D%22{code}%22)&pageNumber=1&pageSize={page_size_holders}"
                resp = await client.get(url_top10)
                if resp.status_code == 200:
                    data_json = resp.json()
                    if data_json.get("success") and "result" in data_json and data_json["result"]:
                        items = data_json["result"].get("data", [])
                        
                        if items:
                            # 如果请求全量历史，直接返回所有记录
                            if all_history:
                                for item in items:
                                    result["top10_holders"].append({
                                        "rank": item.get("HOLDER_RANK"),
                                        "holder_name": item.get("HOLDER_NAME"),
                                        "share_type": "流通A股",
                                        "hold_count": item.get("HOLD_NUM"),
                                        "hold_pct": item.get("FREE_HOLDNUM_RATIO"),
                                        "change": item.get("HOLD_NUM_CHANGE"), 
                                        "time": item.get("END_DATE", "")[:10] if item.get("END_DATE") else ""
                                    })
                            else:
                                # 否则只取最新一期
                                latest_date = items[0].get("END_DATE")
                                for item in items:
                                    if item.get("END_DATE") == latest_date:
                                        result["top10_holders"].append({
                                            "rank": item.get("HOLDER_RANK"),
                                            "holder_name": item.get("HOLDER_NAME"),
                                            "share_type": "流通A股",
                                            "hold_count": item.get("HOLD_NUM"),
                                            "hold_pct": item.get("FREE_HOLDNUM_RATIO"),
                                            "change": item.get("HOLD_NUM_CHANGE"), 
                                            "time": item.get("END_DATE", "")[:10] if item.get("END_DATE") else ""
                                        })
            except Exception as e:
                logger.warning(f"直接获取前十大股东失败: code={code}, error={e}")
                
        gc.collect() # 显式回收
        return result

    async def get_dividend_history(self, symbol: str) -> List[Dict[str, Any]]:
        """获取分红配股历史"""
        try:
            # 东方财富接口往往不要sh/sz前缀
            code = symbol
            if "." in code:
                code = code.split(".")[0]
                
            # 增加 20 秒超时保护
            df = await asyncio.wait_for(
                asyncio.to_thread(ak.stock_fhps_detail_em, symbol=code),
                timeout=20.0
            )
            if df is None or df.empty:
                return []
                
            result = []
            for _, row in df.iterrows():
                result.append({
                    "report_date": str(row.get("报告期", "")), 
                    "plan_date": str(row.get("业绩披露日", "")),
                    "bonus_share_ratio": self._clean_value(row.get("送转股份-送转总比例")), 
                    "cash_dividend_ratio": self._clean_value(row.get("现金分红-现金分红比例")), 
                    "record_date": str(row.get("股权登记日", "")),
                    "ex_date": str(row.get("除权除息日", "")),
                    "progress": row.get("方案进度", ""),
                })
            return result
        except Exception as e:
            logger.error(f"AkShare获取分红配送失败: symbol={symbol}, error={e}")
            return []
    async def get_restricted_release(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """获取限售股解禁数据 (优化版: 使用东财详情接口)"""
        try:
            # 清化日期格式 YYYY-MM-DD -> YYYYMMDD
            s_date = start_date.replace("-", "")
            e_date = end_date.replace("-", "")
            
            df = await asyncio.to_thread(ak.stock_restricted_release_detail_em, start_date=s_date, end_date=e_date)
            if df is None or df.empty:
                return []
            
            result = []
            for _, row in df.iterrows():
                # 已经是 YYYY-MM-DD 格式或需要转换? 
                # 从之前 dump 看是 "2020-09-04" 这种格式
                release_date = str(row.get("解禁时间", ""))
                
                result.append({
                    "code": row.get("股票代码", ""),
                    "name": row.get("股票简称", ""),
                    "release_date": release_date,
                    "release_count": self._clean_value(row.get("解禁数量")),
                    "release_market_cap": self._clean_value(row.get("实际解禁市值")),
                    "ratio": self._clean_value(row.get("占解禁前流通市值比例")),
                    "holder_type": row.get("限售股类型", ""),
                })
            return result
        except Exception as e:
            logger.error(f"AkShare获取限售股解禁失败: start={start_date}, end={end_date}, error={e}")
            return []
    async def get_north_funds_daily(self, date: str) -> List[Dict[str, Any]]:
        """获取北向资金每日个股统计 (Latest via Rank)"""
        try:
            # 使用 '今日排行' 获取最新数据的快照
            # 注意: 这通常只返回最近一个交易日的数据
            df = await asyncio.to_thread(ak.stock_hsgt_hold_stock_em, market="北向", indicator="今日排行")
            
            if df is None or df.empty:
                return []
            
            result = []
            for _, row in df.iterrows():
                # Check date match
                row_date = str(row.get("日期", ""))
                if row_date != date:
                    continue
                    
                result.append({
                    "code": row.get("代码", ""),
                    "name": row.get("名称", ""),
                    "date": row_date,
                    "hold_count": self._clean_value(row.get("今日持股-股数")),
                    "hold_market_cap": self._clean_value(row.get("今日持股-市值")),
                    "hold_ratio": self._clean_value(row.get("今日持股-占总股本比")), 
                })
            return result
        except Exception as e:
            logger.error(f"AkShare获取北向资金失败: date={date}, error={e}")
            return []

    async def get_north_funds_history(self, code: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """获取个股北向资金持股历史"""
        try:
            s_date = start_date.replace("-", "")
            e_date = end_date.replace("-", "")
            df = await asyncio.to_thread(ak.stock_hsgt_individual_detail_em, symbol=code, start_date=s_date, end_date=e_date)
            
            if df is None or df.empty:
                return []
                
            result = []
            for _, row in df.iterrows():
                result.append({
                    "code": row.get("股票代码", code),
                    "name": row.get("股票简称", ""),
                    "date": str(row.get("持股日期", "")),
                    "hold_count": self._clean_value(row.get("持股数量")),
                    "hold_market_cap": self._clean_value(row.get("持股市值")),
                    "hold_ratio": self._clean_value(row.get("持股数量占发行股百分比")),
                })
            return result
        except Exception as e:
            logger.error(f"AkShare获取个股北向历史失败: code={code}, error={e}")
            return []

    async def get_lhb_inst_stats(self, date: str) -> List[Dict[str, Any]]:
        """获取龙虎榜机构买卖统计"""
        try:
            clean_date = date.replace("-", "")
            df = await asyncio.to_thread(ak.stock_lhb_jgmmtj_em, start_date=clean_date, end_date=clean_date)
            
            if df is None or df.empty:
                return []
            
            result = []
            for _, row in df.iterrows():
                result.append({
                    "code": row.get("代码", ""),
                    "name": row.get("名称", ""),
                    "buy_inst_count": self._clean_value(row.get("买方机构数")),
                    "sell_inst_count": self._clean_value(row.get("卖方机构数")),
                    "inst_buy_amt": self._clean_value(row.get("机构买入总额")),
                    "inst_sell_amt": self._clean_value(row.get("机构卖出总额")),
                    "inst_net_buy_amt": self._clean_value(row.get("机构买入净额")),
                })
            return result
        except Exception as e:
            logger.error(f"AkShare获取龙虎榜机构统计失败: date={date}, error={e}")
            return []

    async def get_analyst_ranks(self, current_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取个股研报评级 (Information Dimension)"""
        try:
            df = await asyncio.to_thread(ak.stock_research_report_em)
            if df is None or df.empty:
                return []
            result = []
            for _, row in df.iterrows():
                rpt_date = str(row.get("日期", ""))[:10]
                if current_date and rpt_date != current_date:
                    continue
                result.append({
                    "stock_code": row.get("股票代码", ""),
                    "report_date": rpt_date,
                    "analyst": row.get("机构", ""),
                    "rating": row.get("东财评级", ""),
                    "change_direction": None, # 该接口无直接变动方向
                    "target_price": None,
                    "stock_name": row.get("股票简称", "")
                })
            return result
        except Exception as e:
            logger.error(f"AkShare Research Report Error: {e}")
            return []


    async def get_performance_forecast(self, period_date: str) -> List[Dict[str, Any]]:
        """获取业绩预告 (Information Dimension)"""
        try:
            df = await asyncio.to_thread(ak.stock_yjyg_em, date=period_date.replace("-", ""))
            if df is None or df.empty:
                return []
            result = []
            for _, row in df.iterrows():
                result.append({
                    "stock_code": row.get("股票代码", ""),
                    "notice_date": str(row.get("公告日期", ""))[:10],
                    "report_period": period_date,
                    "type": row.get("业绩变动", ""),
                    "growth_range": str(row.get("业绩变动幅度", ""))
                })
            return result
        except Exception as e:
            logger.error(f"AkShare Forecast Error: {e}")
            return []

    async def get_sentiment_stats(self, symbol: str) -> Dict[str, Any]:
        """获取个股今日热度统计 (Information Dimension) - 使用东方财富热度榜"""
        try:
            # 格式转换 600519 -> SH600519
            code = symbol
            if not code.startswith(("SH", "SZ", "BJ")):
                if code.startswith("6"): code = "SH" + code
                else: code = "SZ" + code
            
            df = await asyncio.to_thread(ak.stock_hot_rank_detail_em, symbol=code)
            if df is None or df.empty:
                return {"post_count": 0, "read_count": 0, "comment_count": 0}
            
            # 取最新一条记录 (最后一行)
            latest = df.iloc[-1]
            # 我们将排名和粉丝比例映射到 post_count 等字段，以匹配原有 Schema
            # 排名越前(1最小)，热度越高
            rank = int(latest.get("排名", 0))
            new_fans = self._clean_value(latest.get("新晋粉丝")) or 0
            
            return {
                "post_count": 0, # 热度榜无直观帖数，暂设 0
                "read_count": int(new_fans * 1000000), # 模拟权重
                "comment_count": 0,
                "rank_score": rank
            }
        except Exception as e:
            logger.error(f"AkShare Sentiment Error: {symbol}, {e}")
            return {"post_count": 0, "read_count": 0, "comment_count": 0, "rank_score": 0}

    async def get_suspension_daily(self, date: str) -> List[Dict[str, Any]]:
        """获取每日停复牌信息 (Currently returns latest suspension list from EM)"""
        try:
            # 清洗日期格式 YYYY-MM-DD -> YYYYMMDD
            clean_date = date.replace("-", "")
            
            # Note: ak.stock_tfp_em might ignore the date and return the current active suspension list
            df = await asyncio.to_thread(ak.stock_tfp_em, date=clean_date)
            
            if df is None or df.empty:
                return []
            
            result = []
            for _, row in df.iterrows():
                result.append({
                    "code": row.get("代码", ""),
                    "name": row.get("名称", ""),
                    "suspension_date": str(row.get("停牌时间", ""))[:10] if row.get("停牌时间") else None,
                    "resumption_date": str(row.get("预计复牌时间", ""))[:10] if row.get("预计复牌时间") else None,
                    "reason": row.get("停牌原因", ""),
                    "market": row.get("所属市场", ""),
                })
            return result
        except Exception as e:
            logger.error(f"AkShare获取停复牌信息失败: date={date}, error={e}")
            return []

    async def get_market_breadth(self) -> Dict[str, Any]:
        """获取大盘涨跌分布与总市值 (实时)"""
        try:
            df = await asyncio.to_thread(ak.stock_zh_a_spot_em)
            if df is None or df.empty:
                logger.warning("AkShare 返回的大盘数据为空")
                return {}
            
            # 列名参考: ['代码', '名称', '最新价', '涨跌额', '涨跌幅', '成交量', '成交额', '振幅', '最高', '最低', '今开', '昨收', '量比', '换手率', '市盈率-动态', '市净率', '总市值', '流通市值', '涨速', '5分钟涨跌', '60日涨跌幅', '年初至今涨跌幅']
            # 注意: 部分版本列名可能带索引或稍有不同, 这里尝试多重匹配
            change_col = '涨跌幅' if '涨跌幅' in df.columns else None
            mkt_cap_col = '总市值' if '总市值' in df.columns else None
            turnover_col = '换手率' if '换手率' in df.columns else None
            
            if not change_col:
                logger.warning(f"未找到 '涨跌幅' 列, 现有列: {df.columns.tolist()}")
                return {}

            # 清洗数据，确保为数值
            df[change_col] = pd.to_numeric(df[change_col], errors='coerce')
            df = df.dropna(subset=[change_col])

            advance = len(df[df[change_col] > 0])
            decline = len(df[df[change_col] < 0])
            flat = len(df[df[change_col] == 0])
            
            total_market_cap = self._clean_value(df[mkt_cap_col].sum()) if mkt_cap_col else 0
            avg_turnover = self._clean_value(df[turnover_col].mean()) if turnover_col else 0
            
            return {
                "advance": advance,
                "decline": decline,
                "flat": flat,
                "total_market_cap": total_market_cap,
                "avg_turnover": avg_turnover / 100.0 if avg_turnover is not None else None
            }
        except Exception as e:
            logger.error(f"获取大盘涨跌分布失败: {e}")
            return {}

    async def get_north_fund_flow_summary(self) -> List[Dict[str, Any]]:
        """获取沪深港通北向合计资金流向历史 (聚合沪股通与深股通)"""
        try:
            # 获取沪股通历史
            df_sh = await asyncio.to_thread(ak.stock_hsgt_hist_em, symbol="沪股通")
            # 获取深股通历史
            df_sz = await asyncio.to_thread(ak.stock_hsgt_hist_em, symbol="深股通")
            
            if df_sh is None or df_sh.empty or df_sz is None or df_sz.empty:
                logger.warning("未能获取完整的沪深北向资金历史")
                return []
            
            # 清洗与列重命名
            # 列名: ['日期', '当日成交净买额', ...]
            df_sh = df_sh[['日期', '当日成交净买额']].rename(columns={'当日成交净买额': 'sh'})
            df_sz = df_sz[['日期', '当日成交净买额']].rename(columns={'当日成交净买额': 'sz'})
            
            # 合并
            df_merged = pd.merge(df_sh, df_sz, on='日期', how='outer').fillna(0)
            df_merged['total'] = df_merged['sh'] + df_merged['sz']
            df_merged = df_merged.sort_values('日期', ascending=False)
            
            result = []
            for _, row in df_merged.iterrows():
                dt = row['日期']
                dt_str = dt.strftime("%Y-%m-%d") if hasattr(dt, 'strftime') else str(dt)
                
                result.append({
                    "date": dt_str,
                    "north_net_inflow": float(row['total']) * 100000000 # 亿 -> 元
                })
            return result
        except Exception as e:
            logger.error(f"获取北向合计资金汇总失败: {e}")
            return []

    async def get_index_daily(self, symbol: str, start_date: str = "19700101", end_date: str = "20500101") -> List[Dict[str, Any]]:
        """获取指数日线行情 (A股)"""
        try:
            s_date = start_date.replace("-", "")
            e_date = end_date.replace("-", "")
            df = await asyncio.to_thread(ak.index_zh_a_hist, symbol=symbol, period="daily", start_date=s_date, end_date=e_date)
            if df is None or df.empty:
                return []
            
            result = []
            for _, row in df.iterrows():
                dt = row.get("日期")
                dt_str = dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else str(dt)
                result.append({
                    "date": dt_str,
                    "open": self._clean_value(row.get("开盘")),
                    "high": self._clean_value(row.get("最高")),
                    "low": self._clean_value(row.get("最低")),
                    "close": self._clean_value(row.get("收盘")),
                    "volume": self._clean_value(row.get("成交量"), 0),
                    "amount": self._clean_value(row.get("成交额"), 0)
                })
            return result
        except Exception as e:
            logger.error(f"获取指数行情失败: symbol={symbol}, error={e}")
            return []

    async def get_sw_index_daily(self, symbol: str) -> List[Dict[str, Any]]:
        """获取申万行业指数历史日线"""
        try:
            df = await asyncio.to_thread(ak.index_hist_sw, symbol=symbol, period="day")
            if df is None or df.empty:
                return []
            
            result = []
            for _, row in df.iterrows():
                dt = row.get("日期")
                dt_str = dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else str(dt)
                result.append({
                    "date": dt_str,
                    "open": self._clean_value(row.get("开盘")),
                    "high": self._clean_value(row.get("最高")),
                    "low": self._clean_value(row.get("最低")),
                    "close": self._clean_value(row.get("收盘")),
                    "volume": self._clean_value(row.get("成交量"), 0),
                    "amount": self._clean_value(row.get("成交额"), 0)
                })
            return result
        except Exception as e:
            logger.error(f"获取申万指数失败: symbol={symbol}, error={e}")
            return []

    async def get_us_index_daily(self, symbol: str = ".NDX") -> List[Dict[str, Any]]:
        """获取美股指数历史行情 (新浪)"""
        try:
            df = await asyncio.to_thread(ak.index_us_stock_sina, symbol=symbol)
            if df is None or df.empty:
                return []
            
            result = []
            for _, row in df.iterrows():
                dt = row.get("date") or row.get("日期")
                dt_str = dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else str(dt)
                result.append({
                    "date": dt_str,
                    "open": self._clean_value(row.get("open") or row.get("开盘")),
                    "high": self._clean_value(row.get("high") or row.get("最高")),
                    "low": self._clean_value(row.get("low") or row.get("最低")),
                    "close": self._clean_value(row.get("close") or row.get("收盘")),
                    "volume": self._clean_value(row.get("volume") or row.get("成交量"), 0)
                })
            return result
        except Exception as e:
            logger.error(f"获取美股指数失败: symbol={symbol}, error={e}")
            return []

    async def get_etf_daily(self, symbol: str, start_date: str = "19700101", end_date: str = "20500101") -> List[Dict[str, Any]]:
        """获取 ETF 日线行情"""
        try:
            s_date = start_date.replace("-", "")
            e_date = end_date.replace("-", "")
            df = await asyncio.to_thread(ak.fund_etf_hist_em, symbol=symbol, period="daily", start_date=s_date, end_date=e_date)
            if df is None or df.empty:
                return []
            
            result = []
            for _, row in df.iterrows():
                dt = row.get("日期")
                dt_str = dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else str(dt)
                result.append({
                    "date": dt_str,
                    "open": self._clean_value(row.get("开盘")),
                    "high": self._clean_value(row.get("最高")),
                    "low": self._clean_value(row.get("最低")),
                    "close": self._clean_value(row.get("收盘")),
                    "volume": self._clean_value(row.get("成交量"), 0),
                    "amount": self._clean_value(row.get("成交额"), 0)
                })
            return result
        except Exception as e:
            logger.error(f"获取 ETF 行情失败: symbol={symbol}, error={e}")
            return []
    async def get_margin_summary(self) -> List[Dict[str, Any]]:
        """获取全市场两融汇总数据 (沪深合计)"""
        try:
            import pandas as pd
            # 1. 沪市历史 (支持范围)
            today = datetime.now()
            start_date = (today - timedelta(days=60)).strftime("%Y%m%d")
            end_date = today.strftime("%Y%m%d")
            
            df_sh = await asyncio.to_thread(ak.stock_margin_sse, start_date=start_date, end_date=end_date)
            # 沪市列名: 信用交易日期, 融资余额, 融资买入额...
            
            # 2. 深市 (由于历史接口较碎，我们取最近 60 天并尝试循环或使用通用接口)
            # 为简化，我们暂时只取沪市作为代表，或者这里实现一个简单的多日循环
            # 理想情况下应找到全市场接口，但目前 ak.stock_margin_common_info 报错
            
            result = []
            if df_sh is not None and not df_sh.empty:
                for _, row in df_sh.iterrows():
                    dt = row.get("信用交易日期") or row.get("日期")
                    result.append({
                        "date": str(dt),
                        "margin_balance": self._clean_value(row.get("融资余额")),
                        "margin_buy": self._clean_value(row.get("融资买入额")),
                    })
            return result
        except Exception as e:
            logger.error(f"AkShare获取两融汇总失败: error={e}")
            return []
