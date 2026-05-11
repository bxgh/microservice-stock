"""
数据校验规则配置模块 (简化版)

集中管理所有数据类型的校验阈值，实现规则与业务逻辑的解耦。
"""

class TickStandards:
    """
    分笔数据校验标准
    """
    
    class Loose:
        """
        宽松标准 - 用于采集时的快速判断
        目标: 判断数据是否"基本存在"，避免重复采集
        """
        MIN_TIME = "10:00:00"   # 首笔时间上限
        MAX_TIME = "14:30:00"   # 末笔时间下限
        MIN_COUNT = 2000        # 最小 Tick 数量
    
    class Precise:
        """
        精准审计标准 - 用于盘后或午后对账
        目标: 确保数据与基准(快照/K线)高度一致
        """
        PRICE_TOLERANCE = 0.1          # 价格绝对误差
        VOLUME_TOLERANCE = 0.005       # 成交量相对误差 0.5%
        
        # 快照质量增强指标 (Story 2.05)
        SNAPSHOT_DENSITY_THRESHOLD = 0.75  # 密度容忍度 (75%)
        SNAPSHOT_EXPECTED_COUNT = 4800     # 全天预期笔数 (3秒1笔)
        SNAPSHOT_MONOTONIC_PRICE_TOLERANCE = 0.001 # 价格界限误差 (0.1%)
        
        # 快照时间门禁指标
        SNAPSHOT_MIN_TIME_NOON = "11:30:00"
        SNAPSHOT_MIN_TIME_CLOSE = "15:00:00"
        
        # 兜底对账优先级
        REFERENCE_PRIORITY = ["snapshot", "kline"]


class KLineStandards:
    """
    K线数据校验标准 (精简版)
    """
    MIN_COVERAGE_RATE = 98.0            # 最低覆盖率 (%)
    
    # OHLC 合理性
    OHLC_RULES = {
        "high_ge_low": True,            # high >= low
        "high_ge_open": True,           # high >= open
        "high_ge_close": True,          # high >= close
        "low_le_open": True,            # low <= open
        "low_le_close": True,           # low <= close
    }
    
    # 涨跌幅阈值 (针对日K线)
    MAX_DAILY_CHANGE_RATE = 20.0        # 最大日涨跌幅 (%)
