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
        # 每日增量综合同步 (流水线模式)
        "daily_comprehensive_sync": {
            "hour": int(os.getenv("DAILY_SYNC_HOUR", "18")),
            "minute": int(os.getenv("DAILY_SYNC_MINUTE", "00")),
            "enabled": True,
        },
        
        # 每日K线增量同步 (单体模式，已合并至流水线，默认禁用)
        "daily_kline_sync": {
            "hour": 18,
            "minute": 30,
            "enabled": False,
        },
        
        # 每日复权因子同步 (单体模式，已合并至流水线，默认禁用)
        "daily_adjust_factor_sync": {
            "hour": 18,
            "minute": 0,
            "enabled": False,
        },
        
        # 系统健康检查
        "health_check": {
            "interval_seconds": int(os.getenv("HEALTH_CHECK_INTERVAL", "3600")),  # 默认每小时
            "enabled": True,
        },
    }
}
