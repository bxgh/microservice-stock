import re
import datetime
from typing import Dict, Any, Optional, Tuple, List
from shared.extractors.rule_based.base_extractor import BaseExtractor

class HolidayExtractor(BaseExtractor):
    """
    [E15-M1-T2] 节假日休市与白噪音加固版零成本过滤器
    支持可选年份匹配，实现 1 星纯行政公告零 Token 阻断
    """
    VERSION = "v1.1"

    def extract(self, title: str, content: str) -> Optional[Dict[str, Any]]:
        # 0. 货政操作核心词避让白名单：如果文本含有“操作/利率/准备金/LPR/MLF/逆回购”等实质货政，绝不拦截！
        avoidance_words = ["操作", "利率", "准备金", "逆回购", "MLF", "LPR"]
        for word in avoidance_words:
            if word in title or word in content:
                return None

        # 1. 前置过滤：确认是否为休市、放假、节假日通知
        is_holiday = False

        keywords = ["休市", "放假", "节假日", "休市安排", "放假安排", "开市时间"]
        for kw in keywords:
            if kw in title:
                is_holiday = True
                break
                
        if not is_holiday:
            return None

        try:
            # 尝试提取节假日名字 (如 清明节, 中秋节)
            holiday_name = "节假日"
            names = ["春节", "国庆", "清明", "五一", "劳动节", "中秋", "元旦", "端午"]
            for name in names:
                if name in title or name in content:
                    holiday_name = name
                    break

            # 匹配具体的休市日期段 (加固版：将年份设为可选匹配组，容纳省略当年年份的通知)
            pattern_span = r"((?:\d{4}\s*年\s*)?\d{1,2}\s*月\s*\d{1,2}\s*日\s*(?:至|起|到)\s*(?:\d{4}\s*年\s*)?\d{1,2}\s*月\s*\d{1,2}\s*日)"
            match_span = re.search(pattern_span, content)
            
            span_str = match_span.group(1) if match_span else f"{holiday_name}期间"
            
            return {
                "holiday_name": holiday_name,
                "span_str": span_str,
                "effective_date": datetime.date.today().strftime("%Y-%m-%d")
            }
        except Exception:
            return None

    def generate_summary(self, extracted_data: Dict[str, Any], previous_data: Optional[Dict[str, Any]] = None) -> Tuple[List[str], int, List[Dict[str, Any]], List[Dict[str, Any]], str]:
        holiday_name = extracted_data["holiday_name"]
        span_str = extracted_data["span_str"]
        eff_date = extracted_data["effective_date"]

        importance_level = 1  # 行政休市锁定 1 星
        intensity_change = "neutral" # 纯中性

        sectors_positive = []
        sectors_negative = []

        # 生成标准的行政安排三句话摘要
        summary = [
            f"根据国务院办公厅放假安排及各大证券交易所的常规业务规划，A股市场将于 {span_str} 暂停交易并实施休市安排。",
            f"在此期间，所有股票交易、融资融券结算以及登记过户等相关交易系统均处于非交易服务状态，并将于休市结束后首个交易日照常开市。",
            f"该公告属于交易所例行发布的行政通知，对各大行业板块皆不构成利多或利空实质传导，市场中性影响。"
        ]

        return summary, importance_level, sectors_positive, sectors_negative, intensity_change
