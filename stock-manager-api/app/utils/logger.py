import logging
import sys
from contextvars import ContextVar
from pythonjsonlogger import jsonlogger

# 全局 request_id 上下文变量
request_id_var: ContextVar[str] = ContextVar('request_id', default='system')

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """自定义 JSON 日志格式"""
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['request_id'] = request_id_var.get()
        log_record['service'] = 'stock-manager'

def setup_logger(name: str) -> logging.Logger:
    """配置日志器"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 控制台输出
    handler = logging.StreamHandler(sys.stdout)
    formatter = CustomJsonFormatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """获取日志器"""
    return logging.getLogger(name)
