
import asyncio
import logging
from typing import Dict, Any, List
from app.utils.database import db
from app.services.akshare_service import AkShareService

logger = logging.getLogger("akshare-api.financial")

class FinancialService:
    def __init__(self):
        self.ak_service = AkShareService()

    async def sync_all_financial_reports(self, limit: int = None) -> Dict[str, Any]:
        """全量同步所有上市股票的历史财务报表"""
        logger.info("开始全量同步财务报表...")
        try:
            # 1. 获取需要同步的上市股票 (断点续传: 跳过最近5天成功同步过的)
            sql = "SELECT ts_code FROM stock_basic_info WHERE list_status = 'L' AND (finance_sync_time IS NULL OR finance_sync_time < NOW() - INTERVAL 5 DAY)"
            rows = await db.execute(sql)
            if not rows:
                logger.info("所有上市股票的财务数据都是最新的，跳过同步。")
                return {"status": "success", "message": "所有股票已同步，无需执行"}
            
            ts_codes = [r[0] for r in rows]
            if limit:
                ts_codes = ts_codes[:limit]
            
            logger.info(f"共需同步 {len(ts_codes)} 只股票")
            
            success_count = 0
            fail_count = 0
            
            # 2. 逐个同步
            for i, ts_code in enumerate(ts_codes):
                try:
                    # 获取 symbol (去掉后缀)
                    symbol = ts_code.split(".")[0]
                    
                    # 调用 AkShareService 获取数据
                    data = await self.ak_service.get_historical_financial_report(symbol)
                    if not data:
                        fail_count += 1
                        continue
                    
                    # 写入数据库
                    await self._save_to_db(ts_code, data)
                    
                    success_count += 1
                    if (i + 1) % 50 == 0:
                        logger.info(f"进度: {i+1}/{len(ts_codes)}. 成功: {success_count}, 失败: {fail_count}")
                    
                    # 频率限制
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"同步股票 {ts_code} 失败: {e}")
                    fail_count += 1
            
            logger.info(f"财务报表同步完成。成功: {success_count}, 失败: {fail_count}")
            return {
                "status": "success",
                "total": len(ts_codes),
                "success": success_count,
                "fail": fail_count
            }
            
        except Exception as e:
            logger.error(f"财务报表同步任务异常: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    async def _save_to_db(self, ts_code: str, data: Dict[str, List[Dict[str, Any]]]):
        """将财务数据保存到 MySQL"""
        
        # 1. 资产负债表
        bs_list = data.get("balance_sheets", [])
        if bs_list:
            cols = [
                "ts_code", "report_date", "notice_date", "total_assets", "total_liabilities",
                "total_equity", "total_equity_ato_parent", "monetary_funds", "accounts_receivable",
                "inventory", "goodwill", "short_term_borrowings", "long_term_borrowings",
                "total_current_assets", "total_non_current_assets", "total_current_liabilities", "total_non_current_liabilities"
            ]
            # 注意: 数据库里是 accounts_receivable, 而 AkShareService 返回的是 accounts_receivable
            # 发现在 SQL 中使用的字段名要和数据库一致。
            # 刚才在脚本中发现数据库字段是 accounts_receivable (没有复数), 
            # 让我检查一下 scripts/init_financial_tables.py
            
            db_rows = []
            for bs in bs_list:
                db_rows.append((
                    ts_code, bs.get("report_date"), bs.get("notice_date"),
                    bs.get("total_assets"), bs.get("total_liabilities"),
                    bs.get("total_equity"), bs.get("total_equity_ato_parent"),
                    bs.get("monetary_funds"), bs.get("accounts_receivable"),
                    bs.get("inventory"), bs.get("goodwill"),
                    bs.get("short_term_borrowings"), bs.get("long_term_borrowings"),
                    bs.get("total_current_assets"), bs.get("total_non_current_assets"),
                    bs.get("total_current_liabilities"), bs.get("total_non_current_liabilities")
                ))
            
            sql = f"""
            INSERT INTO stock_balance_sheet ({", ".join(cols)})
            VALUES ({", ".join(["%s"]*len(cols))})
            ON DUPLICATE KEY UPDATE 
            """ + ", ".join([f"{c}=VALUES({c})" for c in cols[2:]])
            await db.execute_many(sql, db_rows)

        # 2. 利润表
        is_list = data.get("income_statements", [])
        if is_list:
            cols = [
                "ts_code", "report_date", "notice_date", "total_revenue", "operating_revenue",
                "total_operating_cost", "operating_cost", "selling_expenses", "administrative_expenses",
                "financial_expenses", "research_expenses", "operating_profit", "total_profit",
                "net_profit", "parent_net_profit", "deducted_net_profit", "ebit"
            ]
            db_rows = []
            for is_row in is_list:
                db_rows.append((
                    ts_code, is_row.get("report_date"), is_row.get("notice_date"),
                    is_row.get("total_revenue"), is_row.get("operating_revenue"),
                    is_row.get("total_operating_cost"), is_row.get("operating_cost"),
                    is_row.get("selling_expenses"), is_row.get("administrative_expenses"),
                    is_row.get("financial_expenses"), is_row.get("research_expenses"),
                    is_row.get("operating_profit"), is_row.get("total_profit"),
                    is_row.get("net_profit"), is_row.get("parent_net_profit"),
                    is_row.get("deducted_net_profit"), is_row.get("ebit")
                ))
            
            sql = f"""
            INSERT INTO stock_income_statement ({", ".join(cols)})
            VALUES ({", ".join(["%s"]*len(cols))})
            ON DUPLICATE KEY UPDATE 
            """ + ", ".join([f"{c}=VALUES({c})" for c in cols[2:]])
            await db.execute_many(sql, db_rows)

        # 3. 现金流量表
        cf_list = data.get("cash_flows", [])
        if cf_list:
            cols = [
                "ts_code", "report_date", "notice_date", "net_operating_cash_flow",
                "net_investing_cash_flow", "net_financing_cash_flow", "capex",
                "free_cash_flow", "cash_and_equivalents_at_end"
            ]
            db_rows = []
            for cf in cf_list:
                db_rows.append((
                    ts_code, cf.get("report_date"), cf.get("notice_date"),
                    cf.get("net_operating_cash_flow"), cf.get("net_investing_cash_flow"),
                    cf.get("net_financing_cash_flow"), cf.get("capex"),
                    cf.get("free_cash_flow"), cf.get("cash_and_equivalents_at_end")
                ))
            
            sql = f"""
            INSERT INTO stock_cash_flow_statement ({", ".join(cols)})
            VALUES ({", ".join(["%s"]*len(cols))})
            ON DUPLICATE KEY UPDATE 
            """ + ", ".join([f"{c}=VALUES({c})" for c in cols[2:]])
            await db.execute_many(sql, db_rows)

        # 4. 更新基础信息的最近同步时间
        await db.execute("UPDATE stock_basic_info SET finance_sync_time = NOW() WHERE ts_code = %s", (ts_code,))

    async def sync_daily_incremental_reports(self) -> Dict[str, Any]:
        """每日增量同步: 只同步今天发了最新财报的股票"""
        logger.info("开始每日增量财务报表同步...")
        try:
            import datetime
            import akshare as ak
            
            # 1. 生成当前的报表期列表
            now = datetime.datetime.now()
            year = now.year
            month = now.month
            
            periods = []
            if month in (1, 2, 3, 4, 5):
                periods.extend([f"{year-1}1231", f"{year}0331"])
            elif month in (7, 8, 9, 10):
                periods.append(f"{year}0630")
                if month == 10:
                    periods.append(f"{year}0930")
            elif month in (11, 12):
                periods.append(f"{year}0930")
                
            today_str = now.strftime("%Y-%m-%d")
            logger.info(f"增量匹配条件: 最新公告日期为 {today_str}, 参考报告期: {periods}")
            
            need_sync_symbols = set()
            
            # 2. 从各个财报期的最新披露列表中寻找今天发布的股票
            for p in periods:
                try:
                    df = await asyncio.to_thread(ak.stock_yjbb_em, date=p)
                    if df is not None and not df.empty and "最新公告日期" in df.columns:
                        # 挑选公告日期是今天 (或者最近2天内，防止时差/周末等) 的股票
                        # 这里为了严谨，可以容忍昨天和今天的
                        yesterday_str = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                        
                        df_target = df[df["最新公告日期"].isin([today_str, yesterday_str])]
                        for _, row in df_target.iterrows():
                            # 股票代码是6位纯数字
                            code = str(row["股票代码"]).zfill(6)
                            need_sync_symbols.add(code)
                except Exception as e:
                    logger.warning(f"获取 {p} 期业绩报表失败: {e}")
                    
            if not need_sync_symbols:
                logger.info("今日没有新的财报披露数据。")
                return {"status": "success", "message": "今日无新财报披露"}
                
            logger.info(f"今日增量需同步 {len(need_sync_symbols)} 只股票: {list(need_sync_symbols)[:5]}...")
            
            success_count = 0
            fail_count = 0
            
            for symbol in need_sync_symbols:
                try:
                    # 确定 ts_code
                    ts_code = symbol
                    if symbol.startswith(('6', '9', '688')): ts_code = f"{symbol}.SH"
                    elif symbol.startswith(('0', '3')): ts_code = f"{symbol}.SZ"
                    elif symbol.startswith(('4', '8')): ts_code = f"{symbol}.BJ"
                    else: continue
                    
                    data = await self.ak_service.get_historical_financial_report(symbol)
                    if not data:
                        fail_count += 1
                        continue
                    
                    await self._save_to_db(ts_code, data)
                    success_count += 1
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error(f"增量同步股票 {symbol} 失败: {e}")
                    fail_count += 1
            
            logger.info(f"增量同步完成。成功: {success_count}, 失败: {fail_count}")
            return {
                "status": "success",
                "total": len(need_sync_symbols),
                "success": success_count,
                "fail": fail_count
            }
        except Exception as e:
            logger.error(f"每日增量同步任务异常: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}
