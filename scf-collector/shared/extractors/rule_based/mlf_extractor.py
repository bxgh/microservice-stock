import re
import datetime
from typing import Dict, Any, Optional, Tuple, List
from shared.extractors.rule_based.base_extractor import BaseExtractor

class MLFExtractor(BaseExtractor):
    """
    [E15-M1-T2] 中期借贷便利 (MLF) 加固版规则提取器
    支持全半角百分号（% / ％）与空格弹性自适应
    """
    VERSION = "v1.1"


    def extract(self, title: str, content: str) -> Optional[Dict[str, Any]]:
        # 1. 前置过滤：确认是否为中期借贷便利操作公告
        if "中期借贷便利" not in title and "MLF" not in title and "MLF" not in content:
            return None
        if "开展" not in title and "操作情况" not in title and "公告" not in title:
            return None

        # 2. 正则提取金额、期限与利率 (加固百分号与弹性空格)
        pattern_amt = r"(\d+(?:\.\d+)?)\s*(?:亿|万亿)\s*元"
        pattern_term = r"(1\s*年|12\s*个月|3\s*个月)"
        pattern_rate = r"(?:中标利率|操作利率|利率)\s*(?:为|为：)?\s*(\d+(?:\.\d+)?)\s*[%％]"

        match_amt = re.search(pattern_amt, content)
        match_term = re.search(pattern_term, content)
        match_rate = re.search(pattern_rate, content)

        if not match_amt or not match_rate:
            return None

        try:
            amount = float(match_amt.group(1))
            if "万亿" in content and match_amt.group(0).endswith("万亿元"):
                amount *= 10000.0

            term_str = match_term.group(1) if match_term else "1年"
            rate = float(match_rate.group(1))

            # 生效日期
            pattern_date = r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日"
            match_date = re.search(pattern_date, content)
            if match_date:
                effective_date = f"{match_date.group(1)}-{int(match_date.group(2)):02d}-{int(match_date.group(3)):02d}"
            else:
                effective_date = datetime.date.today().strftime("%Y-%m-%d")

            return {
                "amount_cny_100m": amount,
                "term_desc": term_str,
                "rate": rate,
                "effective_date": effective_date
            }
        except Exception:
            return None

    def generate_summary(self, extracted_data: Dict[str, Any], previous_data: Optional[Dict[str, Any]] = None) -> Tuple[List[str], int, List[Dict[str, Any]], List[Dict[str, Any]], str]:
        amount = extracted_data["amount_cny_100m"]
        term = extracted_data["term_desc"]
        rate = extracted_data["rate"]
        eff_date = extracted_data["effective_date"]

        diff_rate = 0.0
        if previous_data:
            prev_rate = previous_data.get("rate", rate)
            diff_rate = round((rate - prev_rate) * 100, 1)

        change_desc = ""
        intensity_change = "neutral"
        importance_level = 3  # MLF 常规公布为 3 星

        sectors_positive = []
        sectors_negative = []

        if diff_rate == 0.0:
            change_desc = f"中标利率维持在 {rate}% 保持稳定。"
            intensity_change = "neutral"
        else:
            importance_level = 4  # MLF 降息/加息，升级为 4 星
            if diff_rate < 0:
                change_desc = f"中标利率下调 {abs(diff_rate)} 个基点（降至 {rate}%），引导实体经济长期信贷成本下行。"
                intensity_change = "moderately_weaker"
                
                # MLF 长期降息利好高负债资本密集型行业（如公用事业、房地产开发）
                sectors_positive = [
                    {"sector_code_sw": "801180", "sector_name": "房地产", "impact_direction": "positive", "impact_strength": 3, "representative_stocks": "000002.SZ,600048.SH", "mapping_source": "rule"},
                    {"sector_code_sw": "801160", "sector_name": "公用事业", "impact_direction": "positive", "impact_strength": 3, "representative_stocks": "600900.SH,600011.SH", "mapping_source": "rule"}
                ]
            else:
                change_desc = f"中标利率上调 {diff_rate} 个基点（升至 {rate}%），旨在控制中长期银行信用扩张速度。"
                intensity_change = "moderately_stronger"
                sectors_negative = [
                    {"sector_code_sw": "801180", "sector_name": "房地产开发", "impact_direction": "negative", "impact_strength": 3, "representative_stocks": "000002.SZ,600048.SH", "mapping_source": "rule"}
                ]

        summary = [
            f"中国人民银行于 {eff_date} 开展中期借贷便利（MLF）操作，本期操作量为 {amount} 亿元，期限为 {term}，中标利率为 {rate}%。",
            f"本期 MLF 操作{change_desc}此操作作为央行调节商业银行中长期流动性及信贷边际利率的关键政策工具，备受市场瞩目。",
            f"中期借贷便利操作的平稳落地，体现出央行维持金融系统流动性合理充裕、维持中长端国债利率基准合理波动的宏观政策导向。"
        ]

        return summary, importance_level, sectors_positive, sectors_negative, intensity_change
