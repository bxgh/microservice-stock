import asyncio
import datetime
import time
import httpx
from typing import Dict, Any, List, Optional
import baostock as bs
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from app.services import baostock_worker
from app.utils.logger import get_logger
from app.utils.database import db

logger = get_logger("baostock-api.service")

class BaoStockService:
    """包装 BaoStock 数据服务
    
    使用全局锁 (asyncio.Lock) 保证 BaoStock 单连接的线程安全性。
    所有同步 I/O 操作通过 asyncio.to_thread 在线程池中执行。
    """
    
    def __init__(self):
        self.lock = asyncio.Lock()
        self._is_logged_in = False
        # 初始化 K 线同步进度
        self._sync_status = {
            "running": False,
            "total": 0,
            "current": 0, 
            "last_synced": None,
            "start_time": 0
        }
        # 初始化复权因子同步进度
        self._adjust_sync_status = {
            "running": False,
            "total": 0,
            "current": 0, 
            "last_synced": None,
            "start_time": 0
        }
        
        from concurrent.futures import ThreadPoolExecutor
        self.thread_pool = ThreadPoolExecutor(max_workers=1)
        
        # 股票列表缓存 (避免频繁查询耗时)
        self._all_a_shares_cache = {
            "data": [],
            "last_updated": 0,
            "date_string": None
        }
        logger.info("初始化线程池与股票列表缓存...")

    async def get_all_a_shares(self) -> List[Dict[str, str]]:
        """获取全市场 A 股代码列表 (排除指数) - 带回溯重试与缓存"""
        import datetime
        now_ts = time.time()
        
        # 1. 检查缓存 (1小时内有效)
        if self._all_a_shares_cache["data"] and (now_ts - self._all_a_shares_cache["last_updated"] < 3600):
            return self._all_a_shares_cache["data"]
            
        for i in range(5): # 缩短回溯深度至 5 天，避免超时
            target_date = (datetime.date.today() - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            
            try:
                rs = await self._execute_with_retry(bs.query_all_stock, day=target_date, timeout=10)
                if rs.error_code != "0":
                    if i == 0:
                        logger.warning(f"无法获取日期 {target_date} 的股票列表: {rs.error_msg}")
                    continue
                
                def fetch_all(rs_obj):
                    data = []
                    while rs_obj.next():
                        row = rs_obj.get_row_data()
                        code = row[0]
                        name = row[2]
                        if code.startswith(("sh.6", "sz.0", "sz.3", "sh.688", "bj.")):
                            data.append({"code": code, "name": name})
                    return data
                
                stocks = await asyncio.to_thread(fetch_all, rs)
                if len(stocks) > 0:
                    # 写入缓存
                    self._all_a_shares_cache = {
                        "data": stocks,
                        "last_updated": now_ts,
                        "date_string": target_date
                    }
                    if i > 0:
                        logger.info(f"回溯 {i} 天获取股票列表成功，日期: {target_date}，共 {len(stocks)} 只")
                    else:
                        logger.info(f"获取全市场 A 股列表成功，日期: {target_date}，共 {len(stocks)} 只")
                    return stocks
                else:
                    if i == 0:
                         logger.warning(f"日期 {target_date} 返回 0 只股票，尝试回溯...")
            except Exception as e:
                logger.error(f"获取全市场股票列表异常 (日期 {target_date}): {e}")
        
        logger.error("Failed to fetch stock list after multiple backoff attempts")
        return self._all_a_shares_cache["data"] if self._all_a_shares_cache["data"] else []
        
    async def _login(self):
        """线程安全的登录方法 (假设外部已持有 lock)"""
        if not self._is_logged_in:
            # 在主进程也保持一个连接 (用于获取股票列表等)
            await asyncio.to_thread(bs.login)
            self._is_logged_in = True
            logger.info("BaoStock login success (Main Process)")

    async def _ensure_connection(self):
        """确保连接处于活跃状态，如果未登录则尝试登录"""
        if not self._is_logged_in:
            await self._login() # Call the async _login method
            if not self._is_logged_in:
                logger.error("无法建立 BaoStock 连接")

    async def _execute_with_retry(self, func, *args, **kwargs):
        """执行 BaoStock 查询并带有自动重试机制"""
        timeout = kwargs.pop("timeout", 20)  # 缩短至 20 秒，适配微信端
        
        async with self.lock:
            await self._ensure_connection()
            try:
                rs = await asyncio.wait_for(asyncio.to_thread(func, *args, **kwargs), timeout=timeout)
                
                # 检测连接类错误 (包含 UnicodeDecodeError 触发的异常情况)
                if rs.error_code != "0" and any(msg in rs.error_msg for msg in ["网络", "连接", "reset", "Broken pipe", "用户未登录", "未登录", "网络接收错误", "接收数据异常"]):
                    logger.warning(f"检测到连接问题或认证失效({rs.error_msg})，尝试重新登录并重试...")
                    self._is_logged_in = False
                    await self._ensure_connection()
                    rs = await asyncio.wait_for(asyncio.to_thread(func, *args, **kwargs), timeout=timeout)
                
                return rs
            except asyncio.TimeoutError:
                logger.error(f"BaoStock 查询超时 ({timeout}s)")
                self._is_logged_in = False
                raise Exception(f"BaoStock Query Timeout ({timeout}s)")
            except (UnicodeDecodeError, Exception) as e:
                # 捕获编码异常或连接重置，通常意味着 Pipe 损坏，需要重连
                if any(msg in str(e).lower() for msg in ["broken pipe", "connection", "reset", "decode", "codec"]):
                    logger.warning(f"捕获到连接或编码异常: {e}，尝试重新登录并重试...")
                    self._is_logged_in = False
                    await self._ensure_connection()
                    try:
                        return await asyncio.wait_for(asyncio.to_thread(func, *args, **kwargs), timeout=timeout)
                    except Exception as re:
                        logger.error(f"重试后依然发生异常: {re}")
                        raise re
                raise e

    async def get_stock_listing_date(self, code: str) -> Optional[str]:
        """获取股票上市日期"""
        try:
            rs = await self._execute_with_retry(bs.query_stock_basic, code=code)
            if rs.error_code != "0":
                return None
            
            row = rs.get_row_data()
            if row and len(row) > 2:
                # query_stock_basic returns: code, code_name, ipoDate, outDate, type, status
                return row[2]  # ipoDate
            return None
        except Exception as e:
            logger.warning(f"获取股票 {code} 上市日期失败: {e}")
            return None

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
        start_date: str = "1990-12-19",
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
                    db_min_date = res[0][0]
                    db_max_date = res[0][1]
                    param_start = datetime.datetime.strptime(original_start_date, "%Y-%m-%d").date()
                    today = datetime.date.today()
                    
                    # 尝试获取上市日期以优化判断
                    ipo_date_str = await self.get_stock_listing_date(code)
                    if ipo_date_str:
                         ipo_date = datetime.datetime.strptime(ipo_date_str, "%Y-%m-%d").date()
                         # 如果请求开始时间早于上市时间，则有效开始时间应为上市时间
                         if param_start < ipo_date:
                             param_start = ipo_date

                    if db_max_date >= today and db_min_date <= param_start:
                        logger.debug(f"股票 {code} 数据已是最新，无需同步")
                        return { "success": True, "count": 0, "message": "数据已是最新" }
                    
                    if param_start < db_min_date:
                        # 需要补充历史
                        start_date = original_start_date
                        logger.info(f"股票 {code} 补充历史及最新: {start_date} ~ 今天")
                    else:
                        # 仅需补充最新
                        start_date = (db_max_date + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                        logger.info(f"股票 {code} 补充最新: {start_date} ~ 今天")
                        
            except Exception as e:
                logger.warning(f"获取股票 {code} 日期范围失败: {e}")
            
        try:
            # 1. 抓取数据 (Parallel Worker)
            fetch_start = time.time()
            
            loop = asyncio.get_running_loop()
            # 使用 ThreadPoolExecutor 进行数据抓取，并加锁保证连接安全
            try:
                async with self.lock:
                    await self._ensure_connection()
                    result = await asyncio.wait_for(
                        loop.run_in_executor(
                            self.thread_pool,
                            baostock_worker.fetch_kline_data,
                            code,
                            start_date,
                            end_date if end_date else ""
                        ),
                        timeout=120
                    )
            except asyncio.TimeoutError:
                logger.error(f"股票 {code} 数据抓取超时 (120s)")
                return {"success": False, "error": "Fetch Timeout"}
            
            if not result["success"]:
                return {"success": False, "error": result["error"]}
            
            rows = result["data"]
            fetch_duration = time.time() - fetch_start
            
            if not rows:
                logger.debug(f"股票 {code} 无数据 ({start_date} ~ {end_date})")
                return {
                    "success": True, 
                    "count": 0,
                    "performance": {"fetch_ms": int(fetch_duration * 1000), "write_ms": 0, "total_ms": int(fetch_duration * 1000), "rows_count": 0}
                }
            
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
                    float(row[10]) if row[10] else 0,      # turnover (turn) index 10
                    float(row[12]) if row[12] else 0,      # pct_chg (pctChg) index 12
                    int(row[11]) if row[11] else 1,        # trade_status (tradestatus) index 11
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

    async def sync_all_stocks_kline(self, start_date: str = "1990-12-19") -> None:
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
    
        # 立即上报初始摘要
        from app.scheduler import get_scheduler_instance
        scheduler = get_scheduler_instance()
        if scheduler:
            scheduler.update_job_summary("daily_kline_sync", f"准备中: 0/{len(stocks)}")
    
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
                    status_msg = f"已处理: {i+1}/{len(stocks)}, 正在同步: {code}, 进度: {(i+1)/len(stocks)*100:.1f}%"
                    logger.info(f"全市场同步进度: {status_msg}, 已耗时: {elapsed:.2f}s")
                    
                    # 更新任务摘要 (V1.2+ 原生支持)
                    from app.scheduler import get_scheduler_instance
                    scheduler = get_scheduler_instance()
                    if scheduler:
                        scheduler.update_job_summary("daily_kline_sync", status_msg)
                
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
        await db.execute("UPDATE sync_progress SET last_index=0, status='idle'")
        self._sync_status["current"] = 0
        self._sync_status["running"] = False
        self._adjust_sync_status["current"] = 0
        self._adjust_sync_status["running"] = False
        logger.info("全市场同步进度已全部重置")

    def get_sync_status(self) -> Dict[str, Any]:
        """获取当前同步状态"""
        return self._sync_status

    def get_adjust_sync_status(self) -> Dict[str, Any]:
        """获取复权因子同步状态"""
        return self._adjust_sync_status


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
                    db_min_date = res[0][0]
                    db_max_date = res[0][1]
                    param_start = datetime.datetime.strptime(original_start_date, "%Y-%m-%d").date()
                    today = datetime.date.today()

                    # 尝试获取上市日期以优化判断
                    ipo_date_str = await self.get_stock_listing_date(code)
                    if ipo_date_str:
                         ipo_date = datetime.datetime.strptime(ipo_date_str, "%Y-%m-%d").date()
                         if param_start < ipo_date:
                             param_start = ipo_date
                    
                    if db_max_date >= today and db_min_date <= param_start:
                        logger.debug(f"股票 {code} 复权因子已是最新，无需同步")
                        return { "success": True, "count": 0, "message": "已是最新" }
                    
                    if param_start < db_min_date:
                        start_date = original_start_date
                    else:
                        start_date = (db_max_date + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                        
            except Exception as e:
                logger.warning(f"获取股票 {code} 复权因子日期范围失败: {e}")
        
        try:
            # 1. 抓取复权因子数据
            fetch_start = time.time()

            
            loop = asyncio.get_running_loop()
            try:
                async with self.lock:
                    await self._ensure_connection()
                    result = await asyncio.wait_for(
                        loop.run_in_executor(
                            self.thread_pool,
                            baostock_worker.fetch_adjust_factor_data,
                            code,
                            start_date,
                            end_date if end_date else ""
                        ),
                        timeout=120
                    )
            except asyncio.TimeoutError:
                logger.error(f"股票 {code} 复权因子抓取超时 (120s)")
                return {"success": False, "error": "Fetch Timeout"}
            
            if not result["success"]:
                return {"success": False, "error": result["error"]}
            
            rows = result["data"]
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
    
        # 立即上报初始摘要
        from app.scheduler import get_scheduler_instance
        scheduler = get_scheduler_instance()
        if scheduler:
            scheduler.update_job_summary("daily_adjust_factor_sync", f"准备中: 0/{len(stocks)}")
    
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
                    status_msg = f"已处理: {i+1}/{len(stocks)}, 正在同步: {code}, 进度: {(i+1)/len(stocks)*100:.1f}%"
                    logger.info(f"全市场复权因子同步进度: {status_msg}, 已耗时: {elapsed:.2f}s")
                    
                    from app.scheduler import get_scheduler_instance
                    scheduler = get_scheduler_instance()
                    if scheduler:
                        scheduler.update_job_summary("daily_adjust_factor_sync", status_msg)
                
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

    async def get_all_container_jobs(self) -> List[Dict[str, Any]]:
        """聚合全系统所有容器的任务列表"""
        from app.scheduler import get_scheduler_instance
        
        # 1. 获取本地任务
        all_jobs = []
        scheduler = get_scheduler_instance()
        if scheduler:
            for job in scheduler.get_jobs():
                job["container"] = "baostock-api"
                job["display_name"] = f"[BaoStock] {job['name']}"
                all_jobs.append(job)
        
        # 2. 从其他容器抓取任务
        containers = [
            {"name": "akshare-api", "url": "http://akshare-api:8000/api/v1/scheduler/jobs"},
            {"name": "pywencai-api", "url": "http://pywencai-api:8000/api/v1/scheduler/jobs"}
        ]
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            for container in containers:
                try:
                    resp = await client.get(container["url"])
                    if resp.status_code == 200:
                        remote_jobs = resp.json().get("jobs", [])
                        for rj in remote_jobs:
                            rj["container"] = container["name"]
                            rj["display_name"] = f"[{container['name'].split('-')[0].capitalize()}] {rj['name']}"
                            all_jobs.append(rj)
                except Exception as e:
                    logger.warning(f"无法抓取容器 {container['name']} 的任务: {e}")
        
        return all_jobs

    async def perform_remote_job_action(self, container: str, job_id: str, action: str) -> bool:
        """转发任务操作指令到指定容器 (适配 V1.2 端点)"""
        if container == "baostock-api":
            from app.scheduler import get_scheduler_instance
            scheduler = get_scheduler_instance()
            if not scheduler: return False
            if action == "pause": return scheduler.pause_job(job_id)
            if action == "resume": return scheduler.resume_job(job_id)
            if action == "run": return await scheduler.run_job_now(job_id)
            return False
            
        # 转发到远程容器: POST /scheduler/jobs/{id}/{action}
        url = f"http://{container}:8000/api/v1/scheduler/jobs/{job_id}/{action}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(url)
                return resp.status_code == 200
            except Exception as e:
                logger.error(f"转发操作 {action} 到 {container} 失败: {e}")
                return False

    async def proxy_container_job_logs(self, container: str, job_id: str, lines: int = 50) -> Dict[str, Any]:
        """抓取指定容器的任务日志流 (适配 V1.2)"""
        if container == "baostock-api":
            from app.scheduler import get_scheduler_instance
            scheduler = get_scheduler_instance()
            if not scheduler: return {"logs": ["调度器未初始化"], "summary": "未就绪"}
            return await scheduler.get_job_logs(job_id, limit=lines)
            
        # 转发到远程容器获取日志
        url = f"http://{container}:8000/api/v1/scheduler/jobs/{job_id}/logs?lines={lines}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    # 是否已经是 V1.2+ 的结构 (包含 summary 字段)
                    if isinstance(data, dict) and "summary" in data:
                        return data
                    # 如果不是，则手动包装 (兼容旧版本或异常格式)
                    return {
                        "logs": data.get("logs", []) if isinstance(data, dict) else [],
                        "summary": "解析成功"
                    }
                return {"logs": [f"远程获取日志失败: {resp.status_code}"], "summary": "未知"}
            except Exception as e:
                logger.error(f"代理抓取 {container} 日志失败: {e}")
                return {"logs": [f"连接远程容器失败: {e}"], "summary": "连接失败"}

    async def verify_weekly_sync_history(self) -> Dict[str, Any]:
        """获取本周数据同步历史分布式统计 (适配 V1.2) - 对比 ClickHouse 和 MySQL 数据"""
        try:
            # 获取最近 7 天的日期范围
            today = datetime.date.today()
            seven_days_ago = today - datetime.timedelta(days=7)
            
            start_str = seven_days_ago.strftime("%Y-%m-%d")
            end_str = today.strftime("%Y-%m-%d")
            
            # 1. 从执行日志获取 ClickHouse 同步数据
            clickhouse_sql = """
                SELECT DATE(execution_time) as exec_date, 
                       SUM(records_processed) as total_records,
                       MAX(execution_time) as last_exec_time
                FROM sync_execution_logs 
                WHERE task_name = 'kline_daily_sync'
                  AND DATE(execution_time) >= %s 
                  AND DATE(execution_time) <= %s
                GROUP BY DATE(execution_time)
                ORDER BY exec_date ASC
            """
            clickhouse_rows = await db.execute(clickhouse_sql, (start_str, end_str))
            
            clickhouse_history = []
            for row in clickhouse_rows:
                clickhouse_history.append({
                    "date": row[0].strftime("%Y-%m-%d 08:00:00") if isinstance(row[0], (datetime.date, datetime.datetime)) else f"{row[0]} 08:00:00",
                    "count": row[1],
                    "last_sync_time": row[2].strftime("%Y-%m-%d %H:%M:%S") if row[2] else None
                })
            
            # 2. 从 MySQL 获取实际存储的 K线数据
            mysql_sql = """
                SELECT trade_date, COUNT(DISTINCT code) as count 
                FROM stock_kline_daily USE INDEX (idx_trade_date)
                WHERE trade_date >= %s AND trade_date <= %s
                GROUP BY trade_date 
                ORDER BY trade_date ASC
            """
            mysql_rows = await db.execute(mysql_sql, (start_str, end_str))
            
            mysql_history = []
            for row in mysql_rows:
                mysql_history.append({
                    "date": f"{row[0].strftime('%Y-%m-%d')} 08:00:00" if isinstance(row[0], (datetime.date, datetime.datetime)) else f"{row[0]} 08:00:00",
                    "count": row[1]
                })
            
            # 3. 复权因子数据统计
            adjust_sql = """
                SELECT adjust_date, COUNT(DISTINCT code) as count 
                FROM stock_adjust_factor USE INDEX (idx_adjust_date)
                WHERE adjust_date >= %s AND adjust_date <= %s
                GROUP BY adjust_date 
                ORDER BY adjust_date ASC
            """
            adjust_rows = await db.execute(adjust_sql, (start_str, end_str))
            
            adjust_history = []
            for row in adjust_rows:
                adjust_history.append({
                    "date": f"{row[0].strftime('%Y-%m-%d')} 08:00:00" if isinstance(row[0], (datetime.date, datetime.datetime)) else f"{row[0]} 08:00:00",
                    "count": row[1]
                })
            
            return {
                "clickhouse": clickhouse_history,  # ClickHouse 同步的数据
                "mysql": mysql_history,            # MySQL 实际存储的数据
                "adjust_factor": adjust_history
            }
        except Exception as e:
            logger.error(f"查询周同步历史失败: {e}")
            return {"clickhouse": [], "mysql": [], "adjust_factor": [], "error": str(e)}

    async def verify_daily_data_completeness(self, target_date: str = None) -> Dict[str, Any]:
        """校验每日数据下载完整性"""
        if not target_date:
            target_date = datetime.date.today().strftime("%Y-%m-%d")
            
        try:
            # 1. 查询数据库中今日已同步的代码数量
            sql = "SELECT COUNT(DISTINCT code) FROM stock_kline_daily WHERE trade_date = %s"
            actual_res = await db.execute(sql, (target_date,))
            actual_count = actual_res[0][0] if actual_res else 0
            
            # 2. 获取市场预期总数 (活跃 A 股)
            stocks = await self.get_all_a_shares()
            expected_count = len(stocks)
            
            # 3. 计算质量指标
            completeness = round((actual_count / expected_count * 100), 2) if expected_count > 0 else 0
            
            # 基础规则：低于 95% 视为有缺失
            status = "healthy"
            if completeness < 95:
                status = "incomplete"
            if actual_count == 0:
                status = "no_data_yet" # 可能是还没到同步时间或今天不开盘
                
            # 4. 获取后台同步任务的实时进度
            sync_status = self.get_sync_status()
            adjust_status = self.get_adjust_sync_status()
            
            return {
                "date": target_date,
                "actual_count": actual_count,
                "expected_count": expected_count,
                "completeness_pct": completeness,
                "status": status,
                "msg": f"今日共同步 {actual_count} 只股票，全市场活跃 A 股预期约为 {expected_count} 只。",
                "background_tasks": {
                    "kline_sync": sync_status,
                    "adjust_factor_sync": adjust_status
                }
            }
        except Exception as e:
            logger.error(f"校验每日数据完整性异常: {e}")
            return {"error": str(e)}
