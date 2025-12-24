import asyncio
import math
from datetime import datetime, date
from typing import Dict, Any, List, Optional
import akshare as ak
from app.utils.logger import get_logger

logger = get_logger("akshare-api.service")

class AkShareService:
    """AkShare 数据服务封装
    
    提供对 AkShare 库的异步封装，所有同步 I/O 操作通过 asyncio.to_thread 在线程池中执行。
    """
    
    def _clean_value(self, val: Any) -> Optional[float]:
        """清洗并转换数值（处理“1.2亿”, “-3.5%”, “NaN”, “None”等）"""
        if val is None or val is False:
            return None
            
        # 处理数值类型
        if isinstance(val, (int, float)):
            if math.isnan(val) or math.isinf(val):
                return None
            return float(val)
            
        s = str(val).strip()
        if not s or s.lower() in ['nan', 'none', 'false', '-', '--']:
            return None
            
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
                return None
            return final_val
        except (ValueError, TypeError):
            return None

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
        """异步获取实时估值
        
        Args:
            symbol: 股票代码，如 "600519"
            
        Returns:
            实时估值字典，包含 name, pe, pb, market_cap, price 字段
            如果查询失败或股票不存在，返回 None
        """
        try:
            df = await asyncio.to_thread(ak.stock_zh_a_spot_em)
            
            if df is None or df.empty:
                return None
                
            stock = df[df["代码"] == symbol]
            if stock.empty:
                return None
                
            row = stock.iloc[0]
            return {
                "name": row.get("名称", ""),
                "pe": self._clean_value(row.get("市盈率-动态")),
                "pb": self._clean_value(row.get("市净率")),
                "market_cap": self._clean_value(row.get("总市值")),
                "price": self._clean_value(row.get("最新价")),
            }
        except Exception as e:
            logger.error(f"AkShare获取实时估值失败: symbol={symbol}, error={e}")
            return None

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
        """异步获取热门排行(以成交额为准)
        
        Args:
            limit: 返回数量限制，默认 50
            
        Returns:
            热门股票列表，按成交额降序排列
            每条记录包含 code, name, price, change_pct, volume, amount 等字段
        """
        try:
            df = await asyncio.to_thread(ak.stock_zh_a_spot_em)
            if df is None or df.empty:
                return []
                
            df = df.sort_values("成交额", ascending=False).head(limit)
            result = []
            for _, row in df.iterrows():
                result.append({
                    "code": row.get("代码", ""),
                    "name": row.get("名称", ""),
                    "price": self._clean_value(row.get("最新价")),
                    "change_pct": self._clean_value(row.get("涨跌幅")),
                    "volume": self._clean_value(row.get("成交量")),
                    "amount": self._clean_value(row.get("成交额")),
                    "turnover_rate": self._clean_value(row.get("换手率")),
                })
            return result
        except Exception as e:
            logger.error(f"AkShare获取热门排行失败: error={e}")
            return []

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
