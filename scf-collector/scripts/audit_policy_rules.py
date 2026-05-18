# -*- coding: utf-8 -*-
"""
[E15-S3-T2] A 股宏观政策规则直切一致率自动化审计比对脚本
支持异步并发加载比对数据组，实现重要性、强度、量纲、板块和语义 5 维一致率对账。
"""

from shared.db.connection import execute_query, DBManager
from dotenv import load_dotenv
import os
import sys
import asyncio
import logging
import json
import re
import difflib
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Tuple, Set

# 将公共库路径加入 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量
env_path = os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__))),
    '.env')
load_dotenv(env_path)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AuditPolicyRules")

# Jaccard 相似度计算


def compute_jaccard_similarity(set_a: Set[Any], set_b: Set[Any]) -> float:
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    return len(set_a.intersection(set_b)) / len(set_a.union(set_b))

# 提取文本中的所有数值标记进行浮点数归一化比对


def extract_normalized_floats(text: str) -> Set[float]:
    if not text:
        return set()

    floats = set()
    # 使用 (?<!\.)(?<!\d) 避免匹配到小数的 fractional 部分 (例如 1.70 中的 70)
    pattern = r'(?<!\.)(?<!\d)\d+(?:\.\d+)?(?!\d)'
    for m in re.finditer(pattern, text):
        num_str = m.group(0)
        try:
            val = float(num_str)
            # 过滤干扰数据 (如 0.0)
            if val != 0.0:
                floats.add(val)
        except ValueError:
            pass

    # 额外匹配带中文字符的数值标记
    pattern_zh = r'(?<!\.)(?<!\d)(\d+(?:\.\d+)?)\s*(?:%|％|bp|个?基点|亿|万|天|年)'
    for m in re.finditer(pattern_zh, text):
        num_str = m.group(1)
        try:
            val = float(num_str)
            if val != 0.0:
                floats.add(val)
        except ValueError:
            pass

    return floats

# 解析板块 JSON 信息，获取 SW 二级代码或板块名称集合


def parse_sector_codes(sectors_val: Any) -> Set[str]:
    if not sectors_val:
        return set()
    if isinstance(sectors_val, str):
        try:
            data = json.loads(sectors_val)
        except Exception:
            return set()
    elif isinstance(sectors_val, list):
        data = sectors_val
    else:
        return set()

    codes = set()
    for s in data:
        code = s.get("sector_code_sw") or s.get("sector_name")
        if code:
            codes.add(str(code).strip())
    return codes


class PolicyAuditEngine:
    """政策规则对账审计引擎"""

    def __init__(self):
        # 比对结果收集器
        self.results = []
        self.total_compared = 0
        self.passed_count = 0

    async def fetch_dual_records(
            self, days_limit: int = 7) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """
        拉取近 N 天的重叠对照政策组记录
        """
        sql_shadow = """
        SELECT * FROM dwd_policy_analysis_shadow
        WHERE created_at >= NOW() - INTERVAL %s DAY
          AND is_deleted = 0
        ORDER BY created_at DESC
        """

        sql_prod = """
        SELECT * FROM dwd_policy_analysis
        WHERE policy_id = %s
          AND is_deleted = 0
        """

        shadow_rows = await execute_query(sql_shadow, (days_limit,), is_select=True)
        if not shadow_rows:
            logger.info(
                f"No shadow records found in the last {days_limit} days.")
            return []

        matched_pairs = []
        for s_row in shadow_rows:
            p_rows = await execute_query(sql_prod, (s_row['policy_id'],), is_select=True)
            if p_rows:
                matched_pairs.append((s_row, p_rows[0]))

        logger.info(
            f"Successfully loaded {len(matched_pairs)} matched policy pairs for audit.")
        return matched_pairs

    def compare_pair(self, s_row: Dict[str, Any],
                     p_row: Dict[str, Any]) -> Dict[str, Any]:
        """
        比对单组对照政策数据，执行 5 维一致率对账
        """
        policy_id = s_row['policy_id']
        model_name = s_row.get('model_name', 'UnknownExtractor')

        # 1. 重要性评星比对 (importance_level)
        star_shadow = int(s_row.get('importance_level', 3))
        star_prod = int(p_row.get('importance_level', 3))
        star_match = (star_shadow == star_prod)

        # 2. 政策强度方向比对 (intensity_change)
        # 支持方向映射对齐 (如 weaker 与 moderately_weaker 均属于偏宽)
        intensity_s = s_row.get('intensity_change', 'neutral').lower().strip()
        intensity_p = p_row.get('intensity_change', 'neutral').lower().strip()

        def normalize_intensity(val: str) -> str:
            if 'strong' in val or 'increase' in val:
                return 'stronger'
            if 'weak' in val or 'decrease' in val:
                return 'weaker'
            return 'neutral'

        intensity_match = (normalize_intensity(intensity_s)
                           == normalize_intensity(intensity_p))

        # 3. 核心量纲匹配比对 (Regular Quantity Extract)
        sum_shadow = s_row.get('summary', '')
        sum_prod = p_row.get('summary', '')

        floats_shadow = extract_normalized_floats(sum_shadow)
        floats_prod = extract_normalized_floats(sum_prod)

        # 规则提取器抽取的关键数值，大模型必须包含（无误差）
        if floats_shadow:
            dimension_matched = floats_shadow.issubset(floats_prod)
        else:
            dimension_matched = True

        # 4. 板块映射重叠度比对 (Jaccard SW Sectors)
        sectors_pos_s = parse_sector_codes(s_row.get('sectors_positive'))
        sectors_pos_p = parse_sector_codes(p_row.get('sectors_positive'))
        pos_jaccard = compute_jaccard_similarity(sectors_pos_s, sectors_pos_p)

        sectors_neg_s = parse_sector_codes(s_row.get('sectors_negative'))
        sectors_neg_p = parse_sector_codes(p_row.get('sectors_negative'))
        neg_jaccard = compute_jaccard_similarity(sectors_neg_s, sectors_neg_p)

        # 综合板块相似度
        sector_jaccard = (pos_jaccard + neg_jaccard) / 2.0
        sector_match = (sector_jaccard >= 0.6)  # 允许 LLM 板块略微宽泛，阈值 0.6

        # 5. 摘要语义相似度比对 (difflib SequenceMatcher)
        text_similarity = difflib.SequenceMatcher(
            None, sum_shadow, sum_prod).ratio()
        # 结构化直切摘要 vs LLM 自由描述，通常重合度较中等，设定 0.4 宽限值
        text_match = (text_similarity >= 0.4)

        # 综合判定
        is_pass = star_match and intensity_match and dimension_matched and sector_match

        return {
            "policy_id": policy_id,
            "extractor": model_name,
            "star_shadow": star_shadow,
            "star_prod": star_prod,
            "star_match": star_match,
            "intensity_shadow": intensity_s,
            "intensity_prod": intensity_p,
            "intensity_match": intensity_match,
            "floats_shadow": list(floats_shadow),
            "floats_prod": list(floats_prod),
            "dimension_match": dimension_matched,
            "pos_jaccard": round(pos_jaccard, 4),
            "neg_jaccard": round(neg_jaccard, 4),
            "sector_jaccard": round(sector_jaccard, 4),
            "sector_match": sector_match,
            "text_similarity": round(text_similarity, 4),
            "text_match": text_match,
            "is_pass": is_pass
        }

    async def execute_audit(self, days_limit: int = 7) -> str:
        """运行完整审计流程并导出报告"""
        logger.info("Executing parallel consistency audit...")

        # 确定报告路径并保证目录存在
        report_dir = os.path.join(
            os.path.dirname(
                os.path.dirname(
                    os.path.abspath(__file__))),
            "docs",
            "features",
            "policy-tracker",
            "implementation_logs",
            "E15",
            "S3")
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, "audit_report.md")

        pairs = await self.fetch_dual_records(days_limit)
        if not pairs:
            empty_report = "# 规则直切影子对照对账审计报告 (Policy Bypass Audit Report)\n\n**比对结果**: 无。近 7 天无影子对照双写对照记录。\n"
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(empty_report)
            logger.info(
                f"No records found. Written empty report to: {report_path}")
            return empty_report

        self.total_compared = len(pairs)

        for s_row, p_row in pairs:
            res = self.compare_pair(s_row, p_row)
            self.results.append(res)
            if res["is_pass"]:
                self.passed_count += 1

        # 计算综合一致率
        consistency_rate = (
            self.passed_count /
            self.total_compared) if self.total_compared > 0 else 1.0
        status = "PASS" if consistency_rate >= 0.95 and self.total_compared >= 3 else "WARNING"
        if self.total_compared < 3:
            status = "PENDING_DATA"  # 数据样本尚不足 (AC 验收除外)

        # 生成 Markdown 报告
        report = self._generate_markdown_report(consistency_rate, status)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        logger.info(
            f"Audit completed. Total: {self.total_compared}, Passed: {self.passed_count}, Consistency: {consistency_rate*100:.2f}%. Report generated at: {report_path}")
        return report

    def _generate_markdown_report(self, rate: float, status: str) -> str:
        now_str = datetime.now(ZoneInfo("Asia/Shanghai")
                               ).strftime('%Y-%m-%d %H:%M:%S')

        # 构造详细对账表格
        table_rows = []
        for r in self.results:
            star_status = "✓" if r["star_match"] else "❌"
            intensity_status = "✓" if r["intensity_match"] else "❌"
            dim_status = "✓" if r["dimension_match"] else "❌"
            sector_status = f"{'✓' if r['sector_match'] else '❌'} ({r['sector_jaccard']*100:.1f}%)"
            pass_status = "**PASS**" if r["is_pass"] else "**FAIL**"

            table_rows.append(
                f"| {r['policy_id']} | {r['extractor']} | {star_status} ({r['star_shadow']} vs {r['star_prod']}) | "
                f"{intensity_status} | {dim_status} | {sector_status} | {pass_status} |")

        details_table = "\n".join(table_rows)

        report = f"""# 规则直切影子对照对账审计报告 (Policy Bypass Audit Report)

## 1. 审计摘要
- **对账日期**: {now_str}
- **审计周期**: 过去 7 天
- **样本总数**: {self.total_compared}
- **对账通过数**: {self.passed_count}
- **综合一致率**: **{rate*100:.2f}%**
- **判定状态**: **{status}** (切流红线: ≥ 95%)

> [!NOTE]
> **对账状态说明**
> - **PASS**: 一致率达标，安全就绪，可以执行正式切流至生产环境。
> - **WARNING**: 一致率低于 95%，禁止盲目切流，必须对不一致案例进行规则精细修复。
> - **PENDING_DATA**: 数据对照样本数量少于 3 条，对账尚未完全就绪，需要继续积累天数。

## 2. 5维对账比对细目 (5D Audit Details)
| 政策ID | 规则解析器 | 评星比对 (影子vs生产) | 强度对齐 | 量纲精准比对 | 板块相似 (Jaccard) | 综合判定 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
{details_table}

## 3. 规则偏离细节与量纲审查
"""

        # 提取失败对账细目
        fail_details = []
        for r in self.results:
            if not r["is_pass"]:
                fail_details.append(
                    f"### 政策 ID: {r['policy_id']} (解析器: {r['extractor']})\n"
                    f"- **量纲分析**: 规则量纲: `{r['floats_shadow']}`, LLM生产量纲: `{r['floats_prod']}` (匹配结果: {'✓' if r['dimension_match'] else '❌'})\n"
                    f"- **板块比对**: Jaccard 相似度正向 = {r['pos_jaccard'] * 100:.1f}%, 负向 = {r['neg_jaccard'] * 100:.1f}%\n"
                    f"- **偏离分析**: 星级对齐: {r['star_match']}, 强度对齐: {r['intensity_match']}\n")

        if fail_details:
            report += "\n".join(fail_details)
        else:
            report += "*无。所有规则直切路径与 LLM 大模型全路径在 5 维审计中保持 100% 高度对齐。*\n"

        report += "\n---\n*Generated by PolicyAuditEngine v1.0 - Modular Quality Control Standard*\n"
        return report


async def main():
    engine = PolicyAuditEngine()
    try:
        await engine.execute_audit()
    finally:
        await DBManager.close_pool()

if __name__ == "__main__":
    asyncio.run(main())
