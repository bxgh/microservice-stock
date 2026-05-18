import re
import datetime
from typing import Dict, Any, Optional, Tuple, List
from shared.extractors.rule_based.base_extractor import BaseExtractor

class LPRExtractor(BaseExtractor):
    """
    [E15-M1-T2] 贷款市场报价利率 (LPR) 加固版规则提取器
    支持全半角百分号（% / ％）与空格弹性自适应
    """
    VERSION = "v1.1"


    def extract(self, title: str, content: str) -> Optional[Dict[str, Any]]:
        # 1. 前置过滤：确认是否为 LPR 公告
        if "贷款市场报价利率" not in title and "LPR" not in title:
            return None
        if "发布" not in title and "公告" not in title:
            return None

        # 2. 利率抽取正则 (加固版: 兼容全半角百分号 % / ％ 与弹性空格)
        pattern_1y = r"1年期贷款市场报价利率\s*（?LPR）?\s*(?:为|为：)?\s*(\d+(?:\.\d+)?)\s*[%％]"
        pattern_5y = r"5年期以上\s*（?LPR）?\s*(?:为|为：)?\s*(\d+(?:\.\d+)?)\s*[%％]"
        
        # 3. 生效日期抽取
        pattern_date = r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日"

        match_1y = re.search(pattern_1y, content)
        match_5y = re.search(pattern_5y, content)
        match_date = re.search(pattern_date, content)

        if not match_1y or not match_5y:
            # 尝试简易弹性提取
            pattern_1y_alt = r"1年期.*?(\d+(?:\.\d+)?)\s*[%％]"
            pattern_5y_alt = r"5年期以上.*?(\d+(?:\.\d+)?)\s*[%％]"
            match_1y = re.search(pattern_1y_alt, content)
            match_5y = re.search(pattern_5y_alt, content)
            if not match_1y or not match_5y:
                return None

        try:
            lpr_1y = float(match_1y.group(1))
            lpr_5y = float(match_5y.group(1))
            
            if match_date:
                year = int(match_date.group(1))
                month = int(match_date.group(2))
                day = int(match_date.group(3))
                effective_date = datetime.date(year, month, day).strftime("%Y-%m-%d")
            else:
                effective_date = datetime.date.today().strftime("%Y-%m-%d")

            return {
                "lpr_1y": lpr_1y,
                "lpr_5y": lpr_5y,
                "effective_date": effective_date
            }
        except Exception:
            return None

    def generate_summary(self, extracted_data: Dict[str, Any], previous_data: Optional[Dict[str, Any]] = None) -> Tuple[List[str], int, List[Dict[str, Any]], List[Dict[str, Any]], str]:
        lpr_1y = extracted_data["lpr_1y"]
        lpr_5y = extracted_data["lpr_5y"]
        eff_date = extracted_data["effective_date"]

        # 与上一期对比 (Diff 基点计算)
        diff_1y = 0.0
        diff_5y = 0.0
        if previous_data:
            prev_1y = previous_data.get("lpr_1y", lpr_1y)
            prev_5y = previous_data.get("lpr_5y", lpr_5y)
            diff_1y = round((lpr_1y - prev_1y) * 100, 1)  # 基点 (bp)
            diff_5y = round((lpr_5y - prev_5y) * 100, 1)

        # 判定强弱与评级
        change_desc = ""
        intensity_change = "neutral"
        importance_level = 3  # 默认无变动为 3 星
        
        sectors_positive = []
        sectors_negative = []

        # 基点差描述及行业映射
        if diff_1y == 0.0 and diff_5y == 0.0:
            change_desc = "均维持不变。"
            intensity_change = "neutral"
        else:
            importance_level = 4  # 有变动升级到 4 星
            desc_parts = []
            
            # 1Y 变动
            if diff_1y > 0:
                desc_parts.append(f"1年期LPR上调 {diff_1y} 个基点")
                intensity_change = "moderately_stronger"
            elif diff_1y < 0:
                desc_parts.append(f"1年期LPR下调 {abs(diff_1y)} 个基点")
                intensity_change = "moderately_weaker"
                
            # 5Y 变动
            if diff_5y > 0:
                desc_parts.append(f"5年期以上LPR上调 {diff_5y} 个基点")
                intensity_change = "moderately_stronger"
            elif diff_5y < 0:
                desc_parts.append(f"5年期以上LPR下调 {abs(diff_5y)} 个基点")
                intensity_change = "moderately_weaker"
                
            change_desc = "发生非对称变动，" + "；".join(desc_parts) + "。"

            # 经典利率传导映射逻辑 (降息利好地产、新能源，利空银行净息差)
            if diff_1y < 0 or diff_5y < 0:
                sectors_positive = [
                    {"sector_code_sw": "801180", "sector_name": "房地产", "impact_direction": "positive", "impact_strength": 3, "representative_stocks": "000002.SZ,600048.SH", "mapping_source": "rule"},
                    {"sector_code_sw": "801180", "sector_name": "房地产开发", "impact_direction": "positive", "impact_strength": 3, "representative_stocks": "000002.SZ,600048.SH", "mapping_source": "rule"},
                    {"sector_code_sw": "801730", "sector_name": "电力设备", "impact_direction": "positive", "impact_strength": 3, "representative_stocks": "300750.SZ,002594.SZ", "mapping_source": "rule"}
                ]
                sectors_negative = [
                    {"sector_code_sw": "801780", "sector_name": "银行", "impact_direction": "negative", "impact_strength": 3, "representative_stocks": "601398.SH,601939.SH", "mapping_source": "rule"}
                ]
            else:  # 加息
                sectors_positive = [
                    {"sector_code_sw": "801780", "sector_name": "银行", "impact_direction": "positive", "impact_strength": 3, "representative_stocks": "601398.SH,601939.SH", "mapping_source": "rule"}
                ]
                sectors_negative = [
                    {"sector_code_sw": "801180", "sector_name": "房地产", "impact_direction": "negative", "impact_strength": 3, "representative_stocks": "000002.SZ,600048.SH", "mapping_source": "rule"}
                ]

        # 完美对齐 DWD 层的三句话摘要
        summary = [
            f"中国人民银行授权全国银行间同业拆借中心公布，最新贷款市场报价利率（LPR）为：1年期 {lpr_1y}%，5年期以上 {lpr_5y}%，自 {eff_date} 起执行。",
            f"本期 LPR {change_desc}相比上期，这是国家贯彻降成本或稳物价的结构性调控体现。",
            f"市场含义层面上，最新利率变动直接对地产、银行等高敏感板块的资金供给链产生传导，对实体经济信贷成本起到精准调节作用。"
        ]

        return summary, importance_level, sectors_positive, sectors_negative, intensity_change
