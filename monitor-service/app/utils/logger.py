import logging
import json
import os
from datetime import datetime
import pytz
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler

CST = pytz.timezone("Asia/Shanghai")

# 定义全局 ContextVar 用于存储 request_id
request_id_var: ContextVar[str] = ContextVar("request_id", default="unknown")

class JSONFormatter(logging.Formatter):
    def format(self, record):
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
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(JSONFormatter())
        logger.addHandler(console_handler)
        
        log_dir = "/app/logs"
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except:
                os.makedirs("logs", exist_ok=True)
                log_dir = "logs"
                
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, "app.log"),
            maxBytes=10*1024*1024, # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)
        
    return logger

def get_logger(name: str):
    # 简单的实现，如果 logger 没被初始化会使用默认配置
    return logging.getLogger(name)
