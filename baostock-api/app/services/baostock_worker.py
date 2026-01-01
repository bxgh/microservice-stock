import baostock as bs
import time
import logging

# 配置 logging (worker process)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("baostock-worker")

def init_worker():
    """工作进程初始化：登录 BaoStock"""
    try:
        bs.login()
        logger.info("Worker process logged in to BaoStock")
    except Exception as e:
        logger.error(f"Worker login failed: {e}")

def query_with_retry(func, *args, **kwargs):
    """带重试机制的查询"""
    for attempt in range(2):
        try:
            rs = func(*args, **kwargs)
            # 检查连接或认证错误
            if rs.error_code != "0" and any(msg in rs.error_msg for msg in ["网络", "连接", "reset", "Broken pipe", "用户未登录", "未登录", "网络接收错误", "接收数据异常"]):
                logger.warning(f"Worker检测到连接问题或认证失效({rs.error_msg})，尝试重连...")
                bs.logout()
                lg = bs.login()
                if lg.error_code == "0":
                    continue
                else:
                    logger.error(f"Worker重重连失败: {lg.error_msg}")
                    return {"success": False, "error": f"Connection lost: {lg.error_msg}"}
            return rs
        except Exception as e:
            if any(msg in str(e).lower() for msg in ["broken pipe", "connection", "reset"]):
                logger.warning(f"Worker捕获到连接异常: {e}，尝试重连...")
                bs.logout()
                bs.login()
                continue
            raise e
    
    # 最后一次尝试
    return func(*args, **kwargs)

def fetch_kline_data(code: str, start_date: str, end_date: str) -> dict:
    """抓取 K 线数据"""
    try:
        fields = "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST"
        
        rs = query_with_retry(
            bs.query_history_k_data_plus,
            code,
            fields,
            start_date=start_date,
            end_date=end_date,
            frequency="d",
            adjustflag="3"
        )
        
        if rs.error_code != "0":
            return {"success": False, "error": rs.error_msg, "data": []}
        
        data = []
        while rs.next():
            data.append(rs.get_row_data())
            
        return {"success": True, "data": data}
        
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}

def fetch_adjust_factor_data(code: str, start_date: str, end_date: str) -> dict:
    """抓取复权因子数据"""
    try:
        rs = query_with_retry(
            bs.query_adjust_factor,
            code=code,
            start_date=start_date,
            end_date=end_date
        )
        
        if rs.error_code != "0":
            return {"success": False, "error": rs.error_msg, "data": []}
            
        data = []
        while rs.next():
            data.append(rs.get_row_data())
            
        return {"success": True, "data": data}
        
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}
