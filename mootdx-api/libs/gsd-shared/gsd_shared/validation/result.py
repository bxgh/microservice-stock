"""
校验结果数据模型

提供标准化的校验结果结构，支持问题聚合和级别提升。
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ValidationLevel(Enum):
    """校验结果级别"""
    PASS = "PASS"   # 通过
    WARN = "WARN"   # 警告
    FAIL = "FAIL"   # 失败


@dataclass
class ValidationIssue:
    """
    单个校验问题
    
    Attributes:
        dimension: 校验维度 (如 "time_coverage", "tick_count")
        level: 问题级别
        message: 人类可读的问题描述
        context: 附加上下文信息
    """
    dimension: str
    level: ValidationLevel
    message: str
    context: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "dimension": self.dimension,
            "level": self.level.value,
            "message": self.message,
            "context": self.context,
        }


@dataclass
class ValidationResult:
    """
    校验结果汇总
    
    Attributes:
        data_type: 数据类型 ("tick", "kline", "stock_list")
        target: 校验目标 (股票代码、日期等)
        level: 整体校验级别
        issues: 问题列表
        timestamp: 校验时间
    """
    data_type: str
    target: str
    level: ValidationLevel = ValidationLevel.PASS
    issues: List[ValidationIssue] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def add_issue(self, issue: ValidationIssue) -> None:
        """
        添加问题并自动提升整体级别
        
        级别提升规则:
        - 任何 FAIL 问题 -> 整体 FAIL
        - WARN 问题 (无 FAIL) -> 整体 WARN
        """
        self.issues.append(issue)
        if issue.level == ValidationLevel.FAIL:
            self.level = ValidationLevel.FAIL
        elif issue.level == ValidationLevel.WARN and self.level != ValidationLevel.FAIL:
            self.level = ValidationLevel.WARN
    
    def is_passed(self) -> bool:
        """是否通过校验 (无 FAIL 问题)"""
        return self.level != ValidationLevel.FAIL
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "data_type": self.data_type,
            "target": self.target,
            "level": self.level.value,
            "issues": [issue.to_dict() for issue in self.issues],
            "issue_count": len(self.issues),
            "timestamp": self.timestamp.isoformat(),
        }
    
    def __str__(self) -> str:
        status_icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}
        return f"{status_icon.get(self.level.value, '?')} [{self.data_type}] {self.target}: {self.level.value} ({len(self.issues)} issues)"
