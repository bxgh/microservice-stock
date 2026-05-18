import re
import datetime
from typing import Dict, Any, Optional, Tuple, List
from shared.extractors.rule_based.base_extractor import BaseExtractor

class OMOExtractor(BaseExtractor):
    """
    [E15-M1-T2] 公开市场操作 (OMO) 逆回购加固版规则提取器
    支持多 Tranches 组合操作捕捉与全半角不定长符号自适应
    """
    VERSION = "v1.1"


    def extract(self, title: str, content: str) -> Optional[Dict[str, Any]]:
        # 1. 前置过滤：确认是否为 OMO/逆回购业务交易公告
        if "公开市场" not in title and "逆回购" not in content:
            return None
        if "交易公告" not in title and "业务公告" not in title:
            return None

        tranches = []
        
        # 模式 A (连贯中文字符段落匹配)
        # 优化匹配模式：解除对尾部“逆回购”的强绑定，改用更松散的“多少亿元多少天期”进行多段抓取
        pattern_narrative = r"(\d+(?:\.\d+)?)\s*(?:亿|万亿)\s*元\s*(\d+)\s*天期?"
        matches_narr = list(re.finditer(pattern_narrative, content))
        
        # 提取全部中标利率，兼容全半角及空格：% 或 ％
        pattern_rate = r"(\d+(?:\.\d+)?)\s*[%％]"
        rates_found = [float(r.group(1)) for r in re.finditer(pattern_rate, content)]

        if matches_narr:
            for idx, match in enumerate(matches_narr):
                try:
                    raw_amt = float(match.group(1))
                    if "万亿" in match.group(0):
                        raw_amt *= 10000.0
                    term = int(match.group(2))
                    
                    # 匹配对应索引的利率，如果多 tranche 利率按顺序排在文本中
                    rate = rates_found[idx] if idx < len(rates_found) else (rates_found[0] if rates_found else 0.0)
                    
                    tranches.append({
                        "amount_cny_100m": raw_amt,
                        "term_days": term,
                        "rate": rate
                    })
                except Exception:
                    continue

        # 模式 B (表格/表格行匹配)
        if not tranches:
            pattern_grid = r"逆回购\s+(\d+)\s*天\s+(\d+(?:\.\d+)?)\s*(?:亿|万亿)\s*元\s+(\d+(?:\.\d+)?)\s*[%％]"
            matches_grid = re.finditer(pattern_grid, content)
            for match in matches_grid:
                try:
                    term = int(match.group(1))
                    raw_amt = float(match.group(2))
                    if "万亿" in match.group(0):
                        raw_amt *= 10000.0
                    rate = float(match.group(3))
                    tranches.append({
                        "amount_cny_100m": raw_amt,
                        "term_days": term,
                        "rate": rate
                    })
                except Exception:
                    continue

        if not tranches:
            return None

        # 3. 日期匹配
        pattern_date = r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日"
        match_date = re.search(pattern_date, content)
        if match_date:
            effective_date = f"{match_date.group(1)}-{int(match_date.group(2)):02d}-{int(match_date.group(3)):02d}"
        else:
            effective_date = datetime.date.today().strftime("%Y-%m-%d")

        # 返回第一条为主力，在 tranches 列表中保存完整的细节以供 generate_summary 使用
        return {
            "amount_cny_100m": tranches[0]["amount_cny_100m"],
            "term_days": tranches[0]["term_days"],
            "rate": tranches[0]["rate"],
            "effective_date": effective_date,
            "tranches": tranches
        }

    def generate_summary(self, extracted_data: Dict[str, Any], previous_data: Optional[Dict[str, Any]] = None) -> Tuple[List[str], int, List[Dict[str, Any]], List[Dict[str, Any]], str]:
        tranches = extracted_data.get("tranches", [{
            "amount_cny_100m": extracted_data["amount_cny_100m"],
            "term_days": extracted_data["term_days"],
            "rate": extracted_data["rate"]
        }])
        eff_date = extracted_data["effective_date"]

        op_descs = []
        total_amount = 0.0
        for tr in tranches:
            op_descs.append(f"{tr['term_days']}天期逆回购 {tr['amount_cny_100m']} 亿元（中标利率 {tr['rate']}%）")
            total_amount += tr['amount_cny_100m']
            
        ops_joined = "和 ".join(op_descs)

        # 降息/加息多期对比基准
        diff_rate = 0.0
        main_rate = tranches[0]["rate"]
        if previous_data:
            prev_rate = previous_data.get("rate", main_rate)
            diff_rate = round((main_rate - prev_rate) * 100, 1)

        change_desc = ""
        intensity_change = "neutral"
        importance_level = 3

        sectors_positive = []
        sectors_negative = []

        if diff_rate == 0.0:
            change_desc = f"主力中标利率维持在 {main_rate}% 保持平稳。"
            intensity_change = "neutral"
        else:
            importance_level = 4
            if diff_rate < 0:
                change_desc = f"主力中标利率下调 {abs(diff_rate)} 个基点（降至 {main_rate}%），释放出央行边际宽信用信号。"
                intensity_change = "moderately_weaker"
                sectors_positive = [
                    {"sector_code_sw": "801190", "sector_name": "非银金融", "impact_direction": "positive", "impact_strength": 3, "representative_stocks": "600030.SH,601318.SH", "mapping_source": "rule"},
                    {"sector_code_sw": "801180", "sector_name": "房地产", "impact_direction": "positive", "impact_strength": 3, "representative_stocks": "000002.SZ,600048.SH", "mapping_source": "rule"}
                ]
            else:
                change_desc = f"主力中标利率上调 {diff_rate} 个基点（升至 {main_rate}%），体现出央行适度收紧流动性防风险的意图。"
                intensity_change = "moderately_stronger"
                sectors_negative = [
                    {"sector_code_sw": "801190", "sector_name": "非银金融", "impact_direction": "negative", "impact_strength": 3, "representative_stocks": "600030.SH,601318.SH", "mapping_source": "rule"}
                ]

        summary = [
            f"中国人民银行于 {eff_date} 开展公开市场业务操作，以固定利率、数量招标方式进行了组合工具操作：其中包含 {ops_joined}，共计投放资金 {total_amount} 亿元。",
            f"本期公开市场操作{change_desc}此举旨在对冲短期财税大月集中走款、MLF到期等季节性扰动，维护银行体系流动性合理充裕。",
            f"在资本市场层面，央行多期限逆回购组合操作展现了极强的政策精细度，有助于呵护短端拆借利率及非银流动性板块景气度。"
        ]

        return summary, importance_level, sectors_positive, sectors_negative, intensity_change
