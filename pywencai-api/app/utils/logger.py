import logging
import json
from datetime import datetime
import pytz
from contextvars import ContextVar

CST = pytz.timezone("Asia/Shanghai")

# 定义全局 ContextVar 用于存储 request_id
request_id_var: ContextVar[str] = ContextVar("request_id", default="unknown")

class JSONFormatter(logging.Formatter):
    def format(self, record):
        # 优先使用 record 中的 request_id，如果没有则从 ContextVar 获取
        request_id = getattr(record, "request_id", request_id_var.get())
        
        log_record = {
            "timestamp": datetime.now(CST).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "request_id": request_id
        }
        
        if hasattr(record, "extra_data"):
            log_record.update(record.extra_data)
            
        return json.dumps(log_record, ensure_ascii=False)

def setup_logger(name: str, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        
    return logger

def get_logger(name: str):
    return logging.getLogger(name)
