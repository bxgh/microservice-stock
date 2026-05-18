import re
import datetime
from typing import Dict, Any, Optional, Tuple, List
from shared.extractors.rule_based.base_extractor import BaseExtractor

class RRRExtractor(BaseExtractor):
    """
    [E15-M1-T2] 存款准备金率 (RRR) 零成本规则提取器
    支持下调/上调存款准备金率 (降准/提准) 深度数据精确匹配
    """
    VERSION = "v1.1"

    def extract(self, title: str, content: str) -> Optional[Dict[str, Any]]:
        # 1. 前置过滤：确认是否为准备金率调整公告 (加厚触发词包括全面/定向降准)
        if "存款准备金率" not in title and "存款准备金率" not in content and "降准" not in title and "降准" not in content:
            return None
        if "决定" not in title and "决定" not in content and "调整" not in content:
            return None

        # 2. 正则提取调整幅度和调整方向 (加固版: 兼容去除金融机构前缀的简称，如下调存款准备金率)
        pattern_action = r"(下调|上调)(?:金融机构)?存款准备金率"
        pattern_value = r"(?:下调|上调)(?:金融机构)?存款准备金率\s*(\d+(?:\.\d+)?)\s*(?:个百分点|[%％])"


        match_action = re.search(pattern_action, content)
        match_value = re.search(pattern_value, content)

        if not match_action or not match_value:
            return None

        try:
            action = match_action.group(1) # 下调 或 上调
            change_points = float(match_value.group(1)) # 百分点数值

            # 生效日期
            pattern_date = r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日"
            match_date = re.search(pattern_date, content)
            if match_date:
                effective_date = f"{match_date.group(1)}-{int(match_date.group(2)):02d}-{int(match_date.group(3)):02d}"
            else:
                effective_date = datetime.date.today().strftime("%Y-%m-%d")

            return {
                "action": action,
                "change_points": change_points,
                "effective_date": effective_date
            }
        except Exception:
            return None

    def generate_summary(self, extracted_data: Dict[str, Any], previous_data: Optional[Dict[str, Any]] = None) -> Tuple[List[str], int, List[Dict[str, Any]], List[Dict[str, Any]], str]:
        action = extracted_data["action"]
        change_points = extracted_data["change_points"]
        eff_date = extracted_data["effective_date"]

        importance_level = 5  # 降准/提准是最高星级政策，锁定 5 星
        
        sectors_positive = []
        sectors_negative = []

        if action == "下调":
            change_desc = f"下调金融机构存款准备金率 {change_points} 个百分点（不含已执行5%存款准备金率的金融机构）。"
            intensity_change = "weaker" # 政策边际大副宽松，在情绪指标中属于 weaker (宽信用)
            
            # 降准释放万亿级长期流动性，强力普惠利好：银行、非银金融（券商）、房地产
            sectors_positive = [
                {"sector_code_sw": "801780", "sector_name": "银行", "impact_direction": "positive", "impact_strength": 3, "representative_stocks": "601398.SH,601939.SH", "mapping_source": "rule"},
                {"sector_code_sw": "801190", "sector_name": "非银金融", "impact_direction": "positive", "impact_strength": 3, "representative_stocks": "600030.SH,601318.SH", "mapping_source": "rule"},
                {"sector_code_sw": "801180", "sector_name": "房地产开发", "impact_direction": "positive", "impact_strength": 3, "representative_stocks": "000002.SZ,600048.SH", "mapping_source": "rule"}
            ]
        else: # 上调 (提准)
            change_desc = f"上调金融机构存款准备金率 {change_points} 个百分点，收回市场长期限过剩资金。"
            intensity_change = "stronger" # 收紧流动性属于 stronger (紧信用)
            
            sectors_negative = [
                {"sector_code_sw": "801190", "sector_name": "非银金融", "impact_direction": "negative", "impact_strength": 3, "representative_stocks": "600030.SH,601318.SH", "mapping_source": "rule"},
                {"sector_code_sw": "801180", "sector_name": "房地产开发", "impact_direction": "negative", "impact_strength": 3, "representative_stocks": "000002.SZ,600048.SH", "mapping_source": "rule"}
            ]

        # 完美匹配 5 星货政宏观大摘要
        summary = [
            f"中国人民银行决定于 {eff_date} 起，正式{change_desc}此举旨在进一步优化金融机构资金结构，提升服务实体经济的长效资本能力。",
            f"作为本年度最瞩目的总量政策工具，本次调整将释放数千亿至万亿级的长期限、低成本银行体系可贷资金，显著降低商业银行负债成本。",
            f"在A股传导层面上，降准直接托底了宏观经济预期，对银行拨备及净息差改善形成实质利好，并强力点燃非银金融及高弹性顺周期板块的配置行情。"
        ]

        return summary, importance_level, sectors_positive, sectors_negative, intensity_change
