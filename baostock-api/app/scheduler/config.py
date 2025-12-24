"""
调度器配置
"""
import os
from typing import Dict, Any

# 调度器全局配置
SCHEDULER_CONFIG: Dict[str, Any] = {
    # 时区设置
    "timezone": os.getenv("SCHEDULER_TIMEZONE", "Asia/Shanghai"),
    
    # 是否启用调度器
    "enabled": os.getenv("SCHEDULER_ENABLED", "true").lower() == "true",
    
    # 任务配置
    "jobs": {
        # 每日K线增量同步
        "daily_kline_sync": {
            "hour": int(os.getenv("DAILY_KLINE_SYNC_HOUR", "18")),
            "minute": int(os.getenv("DAILY_KLINE_SYNC_MINUTE", "30")),
            "enabled": True,
        },
        
        # 每日复权因子同步
        "daily_adjust_factor_sync": {
            "hour": int(os.getenv("DAILY_ADJUST_SYNC_HOUR", "19")),
            "minute": int(os.getenv("DAILY_ADJUST_SYNC_MINUTE", "0")),
            "enabled": True,
        },
        
        # 系统健康检查
        "health_check": {
            "interval_seconds": int(os.getenv("HEALTH_CHECK_INTERVAL", "3600")),  # 默认每小时
            "enabled": True,
        },
    }
}
