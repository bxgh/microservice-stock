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
        # 每日 K 线就绪监测与自动同步 (轮询模式)
        "daily_kline_watcher": {
            "hour": "17-23",
            "minute": "*/15",
            "enabled": True,
        },
        
        # 每日增量综合同步 (流水线模式，由 watcher 触发，此处禁用定时自动触发)
        "daily_comprehensive_sync": {
            "enabled": False,
        },
        
        # 每日K线增量同步 (单体模式，已合并至流水线，禁用)
        "daily_kline_sync": {
            "enabled": False,
        },
        
        # 每日复权因子同步 (单体模式，已合并至流水线，禁用)
        "daily_adjust_factor_sync": {
            "enabled": False,
        },
        
        # 系统健康检查
        "health_check": {
            "interval_seconds": int(os.getenv("HEALTH_CHECK_INTERVAL", "3600")),  # 默认每小时
            "enabled": True,
        },
    }
}
