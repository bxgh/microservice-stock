from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from gsd_shared.validation.standards import KLineStandards
from gsd_shared.validation.result import ValidationResult, ValidationIssue, ValidationLevel

class KLineValidator:
    """K线数据校验器"""
    
    def validate_daily_coverage(self, actual_count: int, expected_count: int, date_str: str) -> ValidationResult:
        """校验日K线覆盖率"""
        result = ValidationResult("kline", date_str)
        
        if expected_count <= 0:
            result.add_issue(ValidationIssue(
                "coverage", ValidationLevel.WARN, "Expected count is zero, cannot calculate coverage"
            ))
            return result

        rate = (actual_count / expected_count) * 100
        
        if rate < KLineStandards.MIN_COVERAGE_RATE:
            result.add_issue(ValidationIssue(
                "coverage", 
                ValidationLevel.FAIL, 
                f"Coverage {rate:.2f}% below threshold {KLineStandards.MIN_COVERAGE_RATE}% ({actual_count}/{expected_count})"
            ))
        else:
            result.add_issue(ValidationIssue(
                "coverage", ValidationLevel.PASS, f"Coverage: {rate:.2f}%"
            ))
            
        return result

    def validate_ohlc(self, open_: float, high: float, low: float, close: float, stock_code: str) -> ValidationResult:
        """校验 OHLC 价格逻辑合理性"""
        result = ValidationResult("kline", stock_code)
        
        rules = KLineStandards.OHLC_RULES
        issues = []
        
        if rules["high_ge_low"] and not (high >= low):
            issues.append("High < Low")
        if rules["high_ge_open"] and not (high >= open_):
            issues.append("High < Open")
        if rules["high_ge_close"] and not (high >= close):
            issues.append("High < Close")
        if rules["low_le_open"] and not (low <= open_):
            issues.append("Low > Open")
        if rules["low_le_close"] and not (low <= close):
            issues.append("Low > Close")
            
        if issues:
            result.add_issue(ValidationIssue(
                "ohlc_logic", 
                ValidationLevel.FAIL, 
                f"OHLC logic errors: {', '.join(issues)}",
                context={"o": open_, "h": high, "l": low, "c": close}
            ))
        
        return result
