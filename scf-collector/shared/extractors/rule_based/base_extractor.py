from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, List

class BaseExtractor(ABC):
    """
    [E15-M1-T2] 规则提取器抽象基类
    定义了零成本提取结构化政策的核心接口，强制保障与 LLM 分析路径在输出 schema 上完全对齐。
    """
    VERSION = "v1.0"


    @abstractmethod
    def extract(self, title: str, content: str) -> Optional[Dict[str, Any]]:
        """
        尝试从标题与正文中用确定性正则匹配提取出核心业务字段。
        若匹配失败（不符合模板或关键数值缺失），必须返回 None。
        """
        pass

    @abstractmethod
    def generate_summary(self, extracted_data: Dict[str, Any], previous_data: Optional[Dict[str, Any]] = None) -> Tuple[List[str], int, List[Dict[str, Any]], List[Dict[str, Any]], str]:
        """
        依据提取出的结构化数据（以及可选的上一期对比数据），生成对齐 DWD 层的各项分析成果：
        返回五元组:
        (
            summary: List[str] (三句话摘要),
            importance_level: int (重要性评级 1-5),
            sectors_positive: List[Dict[str, Any]] (受益板块JSON),
            sectors_negative: List[Dict[str, Any]] (受损板块JSON),
            intensity_change: str (强度变化: 增强/持平/减弱/不适用)
        )
        """
        pass
