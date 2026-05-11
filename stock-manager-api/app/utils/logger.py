import logging
import sys
import os
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
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 同时也设置父级 logger 级别，确保全局生效
    if "." in name:
        parent_name = name.split(".")[0]
        logging.getLogger(parent_name).setLevel(level)
    elif name == "stock-manager":
        # 如果设置的是 root，确保以后 get_logger 的都能继承
        pass

    # 控制台输出
    if not logger.handlers:
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
    # 确保级别继承
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger
