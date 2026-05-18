# -*- coding: utf-8 -*-
"""
[E15-E3-S1] Pydantic V2 政策分析输出契约定义
"""

from typing import List
from pydantic import BaseModel, Field


class SectorImpact(BaseModel):
    sector_name: str = Field(description="申万二级行业名称，例如 '房地产', '银行'")
    sector_code_sw: str = Field(description="申万二级行业代码，例如 '801180', '801780'")
    impact_direction: str = Field(description="影响方向，必须是 'positive' 或 'negative'")
    rationale: str = Field(description="具体传导逻辑，字数严格控制在 50 字以内")


class ContrastDetail(BaseModel):
    topic: str = Field(description="措辞比对维度，例如 '流动性提法', '信贷投放目标'")
    previous: str = Field(description="上一期具体措辞内容")
    current: str = Field(description="本期具体措辞内容")
    change_wording: str = Field(description="核心字词变化，格式例如 '上期词 -> 本期词'")
    implication: str = Field(description="政策偏好微调及其宏观传导逻辑，字数严格控制在 50 字以内")


class GeneralSummaryOutput(BaseModel):
    summary_three_sentences: str = Field(description="政策核心内容摘要，必须严格为三句话。每句话字数不得超过 40 字。第一句陈述政策目标/背景，第二句说明核心操作工具/资金量，第三句揭示对A股市场的传导路径。")
    importance_level: int = Field(description="政策重要性评级，1 到 5 星整数，按重大宏观转折至普通例行行政安排评定。")
    key_points: List[str] = Field(default=[], description="政策核心干货提要列表，每项 ≤ 20 字，最多 3 项")
    sectors: List[SectorImpact] = Field(default=[], description="本政策利好(positive)或利空(negative)的申万二级行业列表")


class WordingContrastOutput(BaseModel):
    summary_three_sentences: str = Field(description="政策对比核心摘要，必须严格为三句话。每句话字数不得超过 40 字。第一句点出两期核心措辞差异，第二句说明政策力度倾向，第三句指出行业传导方向。")
    intensity_change: str = Field(description="政策力度相较上一期的变化。必须是 'stronger', 'moderately_stronger', 'neutral', 'moderately_weaker', 'weaker' 之一")
    contrast_details: List[ContrastDetail] = Field(default=[], description="具体的措辞对比微调维度与宏观解读")
    sectors: List[SectorImpact] = Field(default=[], description="受本次措辞变化核心利好(positive)或利空(negative)的申万二级行业列表")
