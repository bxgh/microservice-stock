import logging
import pandas as pd
from typing import Tuple, Optional, Dict, Any, List
from enum import Enum
from gsd_shared.validation.standards import TickStandards

logger = logging.getLogger(__name__)

class QualityLevel(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"

class SnapshotValidator:
    """
    快照数据质量校验器 (Story 2.05 增强版)
    针对分时快照数据的深度校验，包括密度、单调性及 K 线对账。
    """
    
    @staticmethod
    def verify_density(df: pd.DataFrame) -> Tuple[QualityLevel, str]:
        """
        密度校验: 确保全天快照笔数充足
        """
        if df.empty:
            return QualityLevel.FAIL, "No snapshots found"
            
        actual_count = len(df)
        threshold = TickStandards.Precise.SNAPSHOT_DENSITY_THRESHOLD
        expected = TickStandards.Precise.SNAPSHOT_EXPECTED_COUNT
        
        if actual_count < expected * threshold:
            return QualityLevel.WARN, f"Low snapshot density: {actual_count} / {expected}"
            
        return QualityLevel.PASS, "OK"

    @staticmethod
    def verify_monotonicity(df: pd.DataFrame) -> Tuple[QualityLevel, str]:
        """
        单调性校验: 成交量和成交额必须非递减
        """
        if df.empty:
            return QualityLevel.PASS, "OK"
            
        if not df['total_volume'].is_monotonic_increasing:
            return QualityLevel.FAIL, "Non-monotonic total_volume detected"
            
        if not df['total_amount'].is_monotonic_increasing:
            return QualityLevel.FAIL, "Non-monotonic total_amount detected"
            
        return QualityLevel.PASS, "OK"

    @staticmethod
    def verify_with_kline(df: pd.DataFrame, kline_data: Dict[str, Any]) -> Tuple[QualityLevel, str]:
        """
        K 线对账: 使用官方 K 线数据作为真实边界
        kline_data: { 'high': float, 'low': float, 'volume': int, 'amount': float }
        """
        if df.empty or not kline_data:
            return QualityLevel.PASS, "No data to compare"
            
        k_high = kline_data.get('high', 0)
        k_low = kline_data.get('low', 0)
        k_vol = kline_data.get('volume', 0)
        
        # 1. 价格边界检查 (使用标准容忍度)
        snap_max = df['current_price'].max()
        snap_min = df['current_price'].min()
        
        tol = 1.0 + TickStandards.Precise.SNAPSHOT_MONOTONIC_PRICE_TOLERANCE
        inv_tol = 1.0 - TickStandards.Precise.SNAPSHOT_MONOTONIC_PRICE_TOLERANCE
        
        if k_high > 0 and snap_max > k_high * tol:
            return QualityLevel.FAIL, f"Snap High({snap_max}) exceeds K-line High({k_high})"
            
        if k_low > 0 and snap_min < k_low * inv_tol:
            return QualityLevel.FAIL, f"Snap Low({snap_min}) below K-line Low({k_low})"
            
        # 2. 最终成交量对账 (使用标准容忍度)
        if k_vol > 0:
            final_vol = df['total_volume'].iloc[-1]
            vol_diff_rate = abs(final_vol - k_vol) / k_vol
            if vol_diff_rate > 0.01: # K线对账通常允许稍大一点误差，或者也定义在标准中
                return QualityLevel.WARN, f"Volume mismatch: Snap({final_vol}) vs K-line({k_vol}), Diff: {vol_diff_rate:.2%}"
                
        return QualityLevel.PASS, "OK"

    @classmethod
    async def validate_all(cls, df: pd.DataFrame, kline_ref: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """
        一键式全量检查
        """
        # 单调性 (FAIL 级别)
        level, msg = cls.verify_monotonicity(df)
        if level == QualityLevel.FAIL:
            return False, msg
            
        # 密度 (WARN 级别)
        level, msg = cls.verify_density(df)
        if level == QualityLevel.FAIL:
            return False, msg
            
        # K 线对账 (FAIL/WARN 级别)
        if kline_ref:
            level, msg = cls.verify_with_kline(df, kline_ref)
            if level == QualityLevel.FAIL:
                return False, msg
                
        return True, "Qualified"
