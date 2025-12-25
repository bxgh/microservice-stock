import asyncio
import time
from typing import Dict, Any, List, Optional
import baostock as bs
import numpy as np
from app.utils.logger import get_logger
from app.utils.database import db

logger = get_logger("baostock-api.service")

class BaoStockService:
    """包装 BaoStock 数据服务
    
    使用全局锁 (asyncio.Lock) 保证 BaoStock 单连接的线程安全性。
    所有同步 I/O 操作通过 asyncio.to_thread 在线程池中执行。
    """
    
    def __init__(self):
        self.lock = asyncio.lock = asyncio.Lock()
        self._is_logged_in = False
        self._sync_status = {"running": False, "total": 0, "current": 0, "last_synced": None}
        self._adjust_sync_status = {"running": False, "total": 0, "current": 0, "last_synced": None}

    async def get_all_a_shares(self) -> List[Dict[str, str]]:
        """获取全市场 A 股代码列表 (排除指数)"""
        import datetime
        today = datetime.date.today().strftime("%Y-%m-%d")
        
        try:
            rs = await self._execute_with_retry(bs.query_all_stock, day=today)
            if rs.error_code != "0":
                logger.error(f"无法获取全市场股票列表: {rs.error_msg}")
                return []
            
            def fetch_all(rs_obj):
                data = []
                while rs_obj.next():
                    row = rs_obj.get_row_data()
                    # 简单过滤: 忽略指数 (通常名称包含指数或代码特征)
                    # 更加精准的过滤可以在后续根据 basic_info 细化
                    code = row[0]
                    name = row[2]
                    if code.startswith(("sh.6", "sz.0", "sz.3", "sh.688", "bj.")):
                        data.append({"code": code, "name": name})
                return data
            
            stocks = await asyncio.to_thread(fetch_all, rs)
            logger.info(f"获取全市场 A 股列表成功，共 {len(stocks)} 只")
            return stocks
        except Exception as e:
            logger.error(f"获取全市场股票列表异常: {e}")
            return []
        
    def _login(self) -> bool:
        """同步执行登录逻辑"""
        try:
            lg = bs.login()
            if lg.error_code == "0":
                logger.info("BaoStock 登录成功")
                self._is_logged_in = True
                return True
            else:
                logger.error(f"BaoStock 登录失败: {lg.error_msg}")
                self._is_logged_in = False
                return False
        except Exception as e:
            logger.error(f"BaoStock 登录异常: {e}")
            self._is_logged_in = False
            return False

    async def _ensure_connection(self):
        """确保连接处于活跃状态，如果未登录则尝试登录"""
        if not self._is_logged_in:
            success = await asyncio.to_thread(self._login)
            if not success:
                logger.error("无法建立 BaoStock 连接")

    async def _execute_with_retry(self, func, *args, **kwargs):
        """执行 BaoStock 查询并带有自动重试机制"""
        async with self.lock:
            await self._ensure_connection()
            try:
                rs = await asyncio.to_thread(func, *args, **kwargs)
                
                # 检测连接类错误
                if rs.error_code != "0" and any(msg in rs.error_msg for msg in ["网络", "连接", "reset", "Broken pipe"]):
                    logger.warning(f"检测到连接问题({rs.error_msg})，尝试重新登录并重试...")
                    self._is_logged_in = False
                    await self._ensure_connection()
                    rs = await asyncio.to_thread(func, *args, **kwargs)
                
                return rs
            except Exception as e:
                if any(msg in str(e).lower() for msg in ["broken pipe", "connection", "reset"]):
                    logger.warning(f"捕获到连接异常: {e}，尝试重新登录并重试...")
                    self._is_logged_in = False
                    await self._ensure_connection()
                    try:
                        return await asyncio.to_thread(func, *args, **kwargs)
                    except Exception as re:
                        logger.error(f"重试后依然发生异常: {re}")
                        raise re
                raise e

    async def get_kline(
        self, 
        code: str, 
        frequency: str = "d", 
        adjust: str = "2", 
        start_date: str = "2020-01-01", 
        end_date: str = ""
    ) -> List[Dict[str, Any]]:
        """异步获取 K 线数据"""
        if not code.startswith(("sh.", "sz.")):
            code = f"sh.{code}" if code.startswith("6") else f"sz.{code}"
            
        try:
            rs = await self._execute_with_retry(
                bs.query_history_k_data_plus,
                code=code,
                fields="date,open,high,low,close,volume,amount,turn,pctChg",
                start_date=start_date,
                end_date=end_date,
                frequency=frequency,
                adjustflag=adjust
            )
            
            if rs.error_code != "0":
                logger.error(f"BaoStock查询失败: {rs.error_msg}")
                return []
            
            result = []
            def fetch_all(rs_obj):
                data = []
                while rs_obj.next():
                    data.append(rs_obj.get_row_data())
                return data
            
            rows = await asyncio.to_thread(fetch_all, rs)
            
            for row in rows:
                result.append({
                    "date": row[0],
                    "open": float(row[1]) if row[1] else None,
                    "high": float(row[2]) if row[2] else None,
                    "low": float(row[3]) if row[3] else None,
                    "close": float(row[4]) if row[4] else None,
                    "volume": int(float(row[5])) if row[5] else None,
                    "amount": float(row[6]) if row[6] else None,
                    "turn": float(row[7]) if row[7] else None,
                    "pctChg": float(row[8]) if row[8] else None,
                })
            
            return result[-500:] if len(result) > 500 else result
        except Exception as e:
            logger.error(f"BaoStock获取K线最终异常: {e}")
            return []

    async def sync_kline_to_db(
        self,
        code: str,
        start_date: str = "2020-01-01",
        end_date: str = "",
        frequency: str = "d",
        adjust: str = "2",
        use_db_latest: bool = True
    ) -> Dict[str, Any]:
        """抓取并同步 K 线数据到 MySQL (MySQL 5.7 兼容)"""
        start_process = time.time()
        
        if not code.startswith(("sh.", "sz.")):
            code = f"sh.{code}" if code.startswith("6") else f"sz.{code}"

        # 0. 智能增量同步逻辑：检查数据库中已有的数据范围
        original_start_date = start_date
        needs_historical = False
        needs_recent = False
        
        if use_db_latest:
            try:
                res = await db.execute(
                    "SELECT MIN(trade_date), MAX(trade_date) FROM stock_kline_daily WHERE code=%s", 
                    (code,)
                )
                if res and res[0][0]:
                    import datetime
                    db_min_date = res[0][0]
                    db_max_date = res[0][1]
                    param_start = datetime.datetime.strptime(original_start_date, "%Y-%m-%d").date()
                    today = datetime.date.today()
                    
                    # 判断1：是否需要补充历史数据（参数起点早于库中最早日期）
                    if param_start < db_min_date:
                        needs_historical = True
                        logger.info(f"股票 {code} 需要补充历史数据: {param_start} ~ {db_min_date - datetime.timedelta(days=1)}")
                    
                    # 判断2：是否需要补充最新数据（库中最新日期早于今天）
                    if db_max_date < today:
                        needs_recent = True
                        recent_start = db_max_date + datetime.timedelta(days=1)
                        logger.info(f"股票 {code} 需要补充最新数据: {recent_start} ~ 今天")
                    
                    # 策略：优先补充历史，再补充最新
                    # 本次调用仅处理历史部分，最新部分由下次调用处理
                    if needs_historical:
                        end_date = (db_min_date - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                        logger.info(f"股票 {code} 本次补充历史: {original_start_date} ~ {end_date}")
                    elif needs_recent:
                        start_date = (db_max_date + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                        logger.info(f"股票 {code} 本次补充最新: {start_date} ~ 今天")
                    else:
                        logger.debug(f"股票 {code} 数据已是最新，无需同步")
                        return {
                            "success": True, 
                            "count": 0, 
                            "message": "数据已是最新",
                            "performance": {"fetch_ms": 0, "write_ms": 0, "total_ms": 0, "rows_count": 0}
                        }
                        
            except Exception as e:
                logger.warning(f"获取股票 {code} 日期范围失败，使用原始参数 start_date={original_start_date}: {e}")
            
        try:
            # 1. 抓取数据
            fetch_start = time.time()
            rs = await self._execute_with_retry(
                bs.query_history_k_data_plus,
                code=code,
                fields="date,code,open,high,low,close,preclose,volume,amount,turn,tradestatus,pctChg",
                start_date=start_date,
                end_date=end_date,
                frequency=frequency,
                adjustflag=adjust
            )
            
            if rs.error_code != "0":
                return {"success": False, "error": rs.error_msg}
            
            def fetch_all(rs_obj):
                data = []
                while rs_obj.next():
                    data.append(rs_obj.get_row_data())
                return data
            
            rows = await asyncio.to_thread(fetch_all, rs)
            fetch_duration = time.time() - fetch_start
            
            if not rows:
                return {"success": True, "count": 0, "message": "没有新数据需要同步"}
            
            # 2. 准备数据 (清洗与转换)
            db_rows = []
            for row in rows:
                # 映射: date(0), code(1), open(2), high(3), low(4), close(5), preclose(6), volume(7), amount(8), turn(9), tradestatus(10), pctChg(11)
                db_rows.append((
                    row[1], # code
                    row[0], # trade_date
                    float(row[2]) if row[2] else None,
                    float(row[3]) if row[3] else None,
                    float(row[4]) if row[4] else None,
                    float(row[5]) if row[5] else None,
                    float(row[6]) if row[6] else None,
                    int(float(row[7])) if row[7] else 0,
                    float(row[8]) if row[8] else 0,
                    float(row[9]) if row[9] else 0,
                    float(row[11]) if row[11] else 0,
                    int(row[10]) if row[10] else 1,
                ))
            
            # 3. 批量写入 (Upsert 逻辑)
            # MySQL 5.7 语法: ON DUPLICATE KEY UPDATE
            write_start = time.time()
            sql = """
            INSERT INTO stock_kline_daily 
                (code, trade_date, open, high, low, close, pre_close, volume, amount, turnover, pct_chg, trade_status)
            VALUES 
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                open=VALUES(open), high=VALUES(high), low=VALUES(low), close=VALUES(close),
                pre_close=VALUES(pre_close), volume=VALUES(volume), amount=VALUES(amount),
                turnover=VALUES(turnover), pct_chg=VALUES(pct_chg), trade_status=VALUES(trade_status)
            """
            
            await db.execute_many(sql, db_rows)
            write_duration = time.time() - write_start
            
            total_duration = time.time() - start_process
            
            performance_metrics = {
                "fetch_ms": int(fetch_duration * 1000),
                "write_ms": int(write_duration * 1000),
                "total_ms": int(total_duration * 1000),
                "rows_count": len(rows),
                "avg_ms_per_row": round((total_duration * 1000) / len(rows), 2) if rows else 0
            }
            
            logger.info(f"同步完成: {code}, 数量={len(rows)}, 耗时={performance_metrics['total_ms']}ms")
            
            return {
                "success": True,
                "count": len(rows),
                "performance": performance_metrics
            }
            
        except Exception as e:
            logger.error(f"同步 K 线到数据库异常: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def sync_all_stocks_kline(self, start_date: str = "2020-01-01") -> None:
        """同步全市场股票 K 线 (支持断点续传)"""
        if self._sync_status["running"]:
            logger.warning("全市场同步任务已在运行中")
            return
        
        self._sync_status["running"] = True
        logger.info("开始获取全市场股票列表...")

        # 1. 获取全市场列表
        stocks = await self.get_all_a_shares()
        if not stocks:
            logger.error("未能获取股票列表，同步终止")
            self._sync_status["running"] = False
            return

        # 2. 从数据库恢复进度
        last_index = 0
        try:
            res = await db.execute("SELECT last_index, total_count FROM sync_progress WHERE task_name='full_market_sync'")
            if res and res[0][0] > 0:
                # 只有当总数一致或接近时才判定为同一批次（简单策略）
                if abs(res[0][1] - len(stocks)) < 100:
                    last_index = res[0][0]
                    logger.info(f"开启断点续传，将从索引 {last_index} 开始")
        except Exception as e:
            logger.warning(f"恢复同步进度失败: {e}")

        self._sync_status.update({
            "running": True,
            "total": len(stocks),
            "current": last_index,
            "start_time": time.time()
        })

        logger.info(f"开始全市场同步任务，目标共 {len(stocks)} 只股票")

        try:
            # 修改数据库状态为 running
            await db.execute(
                "UPDATE sync_progress SET status='running', total_count=%s WHERE task_name='full_market_sync'",
                (len(stocks),)
            )

            for i in range(last_index, len(stocks)):
                stock = stocks[i]
                code = stock["code"]
                self._sync_status["current"] = i + 1
                
                # 执行同步 (内部已包含增量逻辑)
                await self.sync_kline_to_db(code=code, start_date=start_date)
                
                # 每 10 只保存一次持久化进度 (平衡性能与安全性)
                if (i + 1) % 10 == 0 or (i + 1) == len(stocks):
                    await db.execute(
                        "UPDATE sync_progress SET current_code=%s, last_index=%s WHERE task_name='full_market_sync'",
                        (code, i + 1)
                    )

                # 每 100 只记录一次日志
                if (i + 1) % 100 == 0 or (i + 1) == len(stocks):
                    elapsed = time.time() - self._sync_status["start_time"]
                    logger.info(f"全市场同步进度: {i+1}/{len(stocks)} ({(i+1)/len(stocks)*100:.2f}%), 已耗时: {elapsed:.2f}s")
                
                await asyncio.sleep(0.01)

            # 完成任务
            await db.execute("UPDATE sync_progress SET status='completed', last_index=0 WHERE task_name='full_market_sync'")
            logger.info(f"全市场同步任务圆满完成! 共处理 {len(stocks)} 只股票")
            
        except Exception as e:
            await db.execute("UPDATE sync_progress SET status='failed' WHERE task_name='full_market_sync'")
            logger.error(f"全市场同步任务中途崩溃: {e}", exc_info=True)
        finally:
            self._sync_status["running"] = False
            self._sync_status["last_synced"] = time.strftime("%Y-%m-%d %H:%M:%S")

    async def reset_sync_progress(self) -> None:
        """强制重置同步进度，下次同步将从头开始"""
        await db.execute("UPDATE sync_progress SET last_index=0, status='idle' WHERE task_name='full_market_sync'")
        self._sync_status["current"] = 0
        logger.info("全市场同步进度已重置")

    def get_sync_status(self) -> Dict[str, Any]:
        """获取当前同步状态"""
        return self._sync_status


    async def get_index_cons(self, index_code: str) -> List[Dict[str, Any]]:
        """获取指数成分股"""
        try:
            # 标准化识别指数类型
            if index_code in ["sh.000300", "sz.399300"] or "300" in index_code:
                func = bs.query_hs300_stocks
            elif index_code in ["sh.000016"] or "50" in index_code:
                func = bs.query_sz50_stocks
            elif index_code in ["sh.000905", "sz.399005"] or "500" in index_code:
                func = bs.query_zz500_stocks
            else:
                logger.warning(f"不支持的指数代码: {index_code}")
                return []
            
            rs = await self._execute_with_retry(func)
            
            if rs.error_code != "0":
                return []
            
            def fetch_all(rs_obj):
                data = []
                while rs_obj.next():
                    data.append(rs_obj.get_row_data())
                return data
            
            rows = await asyncio.to_thread(fetch_all, rs)
            
            result = []
            for row in rows:
                result.append({
                    "code": row[1],
                    "name": row[2] if len(row) > 2 else "",
                })
            return result
        except Exception as e:
            logger.error(f"BaoStock获取指数成分异常: {e}")
            return []

    async def get_industry_classify(self) -> List[Dict[str, Any]]:
        """获取行业分类"""
        try:
            rs = await self._execute_with_retry(bs.query_stock_industry)
            
            if rs.error_code != "0":
                logger.error(f"BaoStock查询行业分类失败: {rs.error_msg}")
                return []
            
            def fetch_all(rs_obj):
                data = []
                while rs_obj.next():
                    data.append(rs_obj.get_row_data())
                return data
            
            rows = await asyncio.to_thread(fetch_all, rs)
            
            industries = {}
            for row in rows:
                code = row[1] if len(row) > 1 else ""
                industry = row[3] if len(row) > 3 else ""
                if industry:
                    if industry not in industries:
                        industries[industry] = []
                    industries[industry].append(code)
            
            result = []
            for industry, stocks in industries.items():
                result.append({
                    "industry": industry,
                    "stock_count": len(stocks),
                })
            return result
        except Exception as e:
            logger.error(f"BaoStock获取行业分类异常: {e}")
            return []

    async def get_valuation_history(
        self, 
        code: str, 
        start_date: str = "2020-01-01", 
        end_date: str = ""
    ) -> Dict[str, Any]:
        """获取历史估值数据 (PE/PB)"""
        if not code.startswith(("sh.", "sz.")):
            code = f"sh.{code}" if code.startswith("6") else f"sz.{code}"
            
        try:
            rs = await self._execute_with_retry(
                bs.query_history_k_data_plus,
                code=code,
                fields="date,close,peTTM,pbMRQ,psTTM",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag="3"
            )
            
            if rs.error_code != "0":
                logger.error(f"BaoStock查询估值失败: {rs.error_msg}")
                return {"history": [], "statistics": {}}
            
            def _fetch_all(rs_obj):
                data = []
                while rs_obj.next():
                    data.append(rs_obj.get_row_data())
                return data
            
            rows = await asyncio.to_thread(_fetch_all, rs)
            
            history = []
            for row in rows:
                history.append({
                    "date": row[0],
                    "price": float(row[1]) if row[1] else None,
                    "pe": float(row[2]) if row[2] else None,
                    "pb": float(row[3]) if row[3] else None,
                    "ps": float(row[4]) if row[4] else None,
                })
            
            # 计算统计指标
            pe_vals = [h['pe'] for h in history if h['pe'] is not None]
            pb_vals = [h['pb'] for h in history if h['pb'] is not None]
            ps_vals = [h['ps'] for h in history if h['ps'] is not None]
            
            stats = {}
            for key, vals in [("pe", pe_vals), ("pb", pb_vals), ("ps", ps_vals)]:
                if vals:
                    stats[key] = {
                        "mean": round(float(np.mean(vals)), 3),
                        "median": round(float(np.median(vals)), 3),
                        "min": round(float(np.min(vals)), 3),
                        "max": round(float(np.max(vals)), 3),
                        "p10": round(float(np.percentile(vals, 10)), 3),
                        "p25": round(float(np.percentile(vals, 25)), 3),
                        "p75": round(float(np.percentile(vals, 75)), 3),
                        "p90": round(float(np.percentile(vals, 90)), 3),
                        "current": vals[-1],
                        "percentile": round(float(np.sum(np.array(vals) < vals[-1]) / len(vals) * 100), 2) if len(vals) > 0 else None
                    }
                else:
                    stats[key] = None
                        
            return {
                "history": history,
                "statistics": stats
            }
        except Exception as e:
            logger.error(f"BaoStock获取历史估值异常: {e}")
            return {"history": [], "statistics": {}}

    async def get_profit_data(self, code: str, year: int, quarter: int) -> Optional[Dict[str, Any]]:
        """获取盈利能力数据"""
        if not code.startswith(("sh.", "sz.")):
            code = f"sh.{code}" if code.startswith("6") else f"sz.{code}"
        
        try:
            rs = await self._execute_with_retry(bs.query_profit_data, code=code, year=year, quarter=quarter)
            
            if rs.error_code != "0":
                # 尝试上一季度
                if quarter > 1:
                    rs = await self._execute_with_retry(bs.query_profit_data, code=code, year=year, quarter=quarter-1)
                else:
                    rs = await self._execute_with_retry(bs.query_profit_data, code=code, year=year-1, quarter=4)
            
            if rs.error_code != "0":
                logger.error(f"BaoStock查询盈利能力失败: {rs.error_msg}")
                return None
            
            def fetch_all(rs_obj):
                data = []
                while rs_obj.next():
                    data.append(rs_obj.get_row_data())
                return data
            
            rows = await asyncio.to_thread(fetch_all, rs)
            if not rows:
                return None
            
            row = rows[0]
            return {
                "code": row[0] if len(row) > 0 else code,
                "pub_date": row[1] if len(row) > 1 else "",
                "stat_date": row[2] if len(row) > 2 else "",
                "roe_avg": float(row[3]) if len(row) > 3 and row[3] else None,
                "np_margin": float(row[4]) if len(row) > 4 and row[4] else None,
                "gp_margin": float(row[5]) if len(row) > 5 and row[5] else None,
                "net_profit": float(row[6]) if len(row) > 6 and row[6] else None,
                "eps_ttm": float(row[7]) if len(row) > 7 and row[7] else None,
            }
        except Exception as e:
            logger.error(f"BaoStock获取盈利能力异常: {e}")
            return None

    async def sync_adjust_factor_to_db(
        self,
        code: str,
        start_date: str = "1990-01-01",
        end_date: str = "",
        use_db_latest: bool = True
    ) -> Dict[str, Any]:
        """同步复权因子到 MySQL (智能增量逻辑)"""
        start_process = time.time()
        
        if not code.startswith(("sh.", "sz.")):
            code = f"sh.{code}" if code.startswith("6") else f"sz.{code}"
        
        # 0. 智能增量同步逻辑
        original_start_date = start_date
        needs_historical = False
        needs_recent = False
        
        if use_db_latest:
            try:
                res = await db.execute(
                    "SELECT MIN(adjust_date), MAX(adjust_date) FROM stock_adjust_factor WHERE code=%s", 
                    (code,)
                )
                if res and res[0][0]:
                    import datetime
                    db_min_date = res[0][0]
                    db_max_date = res[0][1]
                    param_start = datetime.datetime.strptime(original_start_date, "%Y-%m-%d").date()
                    today = datetime.date.today()
                    
                    if param_start < db_min_date:
                        needs_historical = True
                        logger.info(f"股票 {code} 需要补充历史复权因子: {param_start} ~ {db_min_date - datetime.timedelta(days=1)}")
                    
                    if db_max_date < today:
                        needs_recent = True
                        recent_start = db_max_date + datetime.timedelta(days=1)
                        logger.info(f"股票 {code} 需要补充最新复权因子: {recent_start} ~ 今天")
                    
                    if needs_historical:
                        end_date = (db_min_date - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                        logger.info(f"股票 {code} 本次补充历史复权因子: {original_start_date} ~ {end_date}")
                    elif needs_recent:
                        start_date = (db_max_date + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                        logger.info(f"股票 {code} 本次补充最新复权因子: {start_date} ~ 今天")
                    else:
                        logger.debug(f"股票 {code} 复权因子已是最新，无需同步")
                        return {
                            "success": True, 
                            "count": 0, 
                            "message": "复权因子已是最新",
                            "performance": {"fetch_ms": 0, "write_ms": 0, "total_ms": 0, "rows_count": 0}
                        }
                        
            except Exception as e:
                logger.warning(f"获取股票 {code} 复权因子日期范围失败，使用原始参数 start_date={original_start_date}: {e}")
        
        try:
            # 1. 抓取复权因子数据
            fetch_start = time.time()
            rs = await self._execute_with_retry(
                bs.query_adjust_factor,
                code=code,
                start_date=start_date,
                end_date=end_date if end_date else ""
            )
            
            if rs.error_code != "0":
                return {"success": False, "error": rs.error_msg}
            
            def fetch_all(rs_obj):
                data = []
                while rs_obj.next():
                    data.append(rs_obj.get_row_data())
                return data
            
            rows = await asyncio.to_thread(fetch_all, rs)
            fetch_duration = time.time() - fetch_start
            
            if not rows:
                return {"success": True, "count": 0, "message": "没有新的复权因子数据"}
            
            # 2. 准备数据 (清洗与转换)
            # 字段: code, dividOperateDate, foreAdjustFactor, backAdjustFactor, adjustFactor
            db_rows = []
            for row in rows:
                db_rows.append((
                    row[0],  # code
                    row[1],  # adjust_date (dividOperateDate)
                    float(row[2]) if row[2] else None,  # fore_adjust_factor
                    float(row[3]) if row[3] else None,  # back_adjust_factor
                    float(row[4]) if row[4] else None,  # adjust_factor
                ))
            
            # 3. 批量写入 (Upsert 逻辑)
            write_start = time.time()
            sql = """
            INSERT INTO stock_adjust_factor 
                (code, adjust_date, fore_adjust_factor, back_adjust_factor, adjust_factor)
            VALUES 
                (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                fore_adjust_factor=VALUES(fore_adjust_factor), 
                back_adjust_factor=VALUES(back_adjust_factor), 
                adjust_factor=VALUES(adjust_factor)
            """
            
            await db.execute_many(sql, db_rows)
            write_duration = time.time() - write_start
            
            total_duration = time.time() - start_process
            
            performance_metrics = {
                "fetch_ms": int(fetch_duration * 1000),
                "write_ms": int(write_duration * 1000),
                "total_ms": int(total_duration * 1000),
                "rows_count": len(rows)
            }
            
            logger.info(f"复权因子同步完成: {code}, 数量={len(rows)}, 耗时={performance_metrics['total_ms']}ms")
            
            return {
                "success": True,
                "count": len(rows),
                "performance": performance_metrics
            }
            
        except Exception as e:
            logger.error(f"同步复权因子到数据库异常: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def sync_all_stocks_adjust_factor(self, start_date: str = "1990-01-01") -> None:
        """同步全市场股票复权因子 (支持断点续传)"""
        if self._adjust_sync_status["running"]:
            logger.warning("全市场复权因子同步任务已在运行中")
            return

        self._adjust_sync_status["running"] = True
        logger.info("开始获取全市场股票列表(复权因子)...")

        stocks = await self.get_all_a_shares()
        if not stocks:
            logger.error("未能获取股票列表，复权因子同步终止")
            self._adjust_sync_status["running"] = False
            return

        # 从数据库恢复进度
        last_index = 0
        try:
            res = await db.execute("SELECT last_index, total_count FROM sync_progress WHERE task_name='full_adjust_factor_sync'")
            if res and res[0][0] > 0:
                if abs(res[0][1] - len(stocks)) < 100:
                    last_index = res[0][0]
                    logger.info(f"开启断点续传（复权因子），将从索引 {last_index} 开始")
        except Exception as e:
            logger.warning(f"恢复复权因子同步进度失败: {e}")
            # 确保表存在
            await db.execute("""
                INSERT IGNORE INTO sync_progress (task_name, status) 
                VALUES ('full_adjust_factor_sync', 'idle')
            """)

        self._adjust_sync_status.update({
            "running": True,
            "total": len(stocks),
            "current": last_index,
            "start_time": time.time()
        })

        logger.info(f"开始全市场复权因子同步任务，目标共 {len(stocks)} 只股票")

        try:
            await db.execute(
                "UPDATE sync_progress SET status='running', total_count=%s WHERE task_name='full_adjust_factor_sync'",
                (len(stocks),)
            )

            for i in range(last_index, len(stocks)):
                stock = stocks[i]
                code = stock["code"]
                self._adjust_sync_status["current"] = i + 1
                
                await self.sync_adjust_factor_to_db(code=code, start_date=start_date)
                
                # 每 10 只保存一次持久化进度
                if (i + 1) % 10 == 0 or (i + 1) == len(stocks):
                    await db.execute(
                        "UPDATE sync_progress SET current_code=%s, last_index=%s WHERE task_name='full_adjust_factor_sync'",
                        (code, i + 1)
                    )

                # 每 100 只记录一次日志
                if (i + 1) % 100 == 0 or (i + 1) == len(stocks):
                    elapsed = time.time() - self._adjust_sync_status["start_time"]
                    logger.info(f"全市场复权因子同步进度: {i+1}/{len(stocks)} ({(i+1)/len(stocks)*100:.2f}%), 已耗时: {elapsed:.2f}s")
                
                await asyncio.sleep(0.01)

            # 完成任务
            await db.execute("UPDATE sync_progress SET status='completed', last_index=0 WHERE task_name='full_adjust_factor_sync'")
            logger.info(f"全市场复权因子同步任务圆满完成! 共处理 {len(stocks)} 只股票")
            
        except Exception as e:
            await db.execute("UPDATE sync_progress SET status='failed' WHERE task_name='full_adjust_factor_sync'")
            logger.error(f"全市场复权因子同步任务中途崩溃: {e}", exc_info=True)
        finally:
            self._adjust_sync_status["running"] = False
            self._adjust_sync_status["last_synced"] = time.strftime("%Y-%m-%d %H:%M:%S")

    def get_adjust_sync_status(self) -> Dict[str, Any]:
        """获取复权因子同步状态"""
        return self._adjust_sync_status
