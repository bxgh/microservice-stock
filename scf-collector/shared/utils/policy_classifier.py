# -*- coding: utf-8 -*-
"""
[E14-S2-P2-T2] 政策自动分类器 policy_classifier.py
标题正则匹配优先 + DeepSeek-Chat (Flash) 定向兜底分类，保障高时效性与零超支风险。
"""

import re
import logging
from typing import Optional
from shared.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

# 预设高频正则匹配字典
REGEX_CLASSIFICATION_RULES = {
    r"货币政策.*执行.*报告": "monetary_policy_report",
    r"贷款市场报价利率|LPR": "lpr_announcement",
    r"公开市场业务|逆回购|国债买入": "open_market_op",
    r"中期借贷便利|MLF": "mlf_op",
    r"国务院常务会议|国常会": "executive_meeting"
}

async def classify_policy(title: str, content: str = "") -> str:
    """
    智能政策分类主入口
    
    返回标准小写拼音类型，例如:
    'monetary_policy_report', 'lpr_announcement', 'open_market_op', 'mlf_op', 'executive_meeting', 'other'
    """
    if not title:
        return "other"
        
    # 1. 尝试标题正则过滤 (零成本，毫秒级)
    for pattern, policy_type in REGEX_CLASSIFICATION_RULES.items():
        if re.search(pattern, title, re.IGNORECASE):
            logger.info(f"Policy Classified by REGEX: '{title}' -> {policy_type}")
            return policy_type
            
    # 2. 大模型智能兜底 (Flash 极小消耗模式)
    logger.info(f"No regex matched for title: '{title}'. Routing to Flash LLM classifier...")
    
    system_prompt = (
        "You are an expert macroeconomic policy classifier. Your job is to classify the provided Chinese policy title into EXACTLY one of the following standard lowercase categories:\n"
        "- monetary_policy_report (for monetary policy reports, central bank policy directions)\n"
        "- lpr_announcement (for LPR lending rate decisions or announcements)\n"
        "- open_market_op (for open market operations, repo operations, bills)\n"
        "- mlf_op (for Medium-term Lending Facility announcements)\n"
        "- executive_meeting (for State Council executive meetings, national strategic guidelines)\n"
        "- other (for other announcements, guidelines, general macroeconomic regulations)\n\n"
        "RULES:\n"
        "1. Output ONLY the lowercase category string (e.g., 'other' or 'mlf_op').\n"
        "2. Do NOT write markdown code blocks, sentences, explanations, or extra punctuation."
    )
    
    user_prompt = f"Please classify this policy:\nTitle: {title}\nSummary: {content[:300]}"
    
    try:
        client = LLMClient()
        # 使用低延迟、省资源的 flash 模式
        result = await client.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            mode="flash",
            temperature=0.0 # 锁定确定性
        )
        
        raw_content = result.get("content", "other").strip().lower()
        
        # 强健过滤，防止 LLM 多嘴或包裹 ```
        clean_content = re.sub(r"[^a-z_]", "", raw_content)
        
        allowed_types = {
            "monetary_policy_report", "lpr_announcement", "open_market_op", 
            "mlf_op", "executive_meeting", "other"
        }
        
        if clean_content in allowed_types:
            logger.info(f"Policy Classified by Flash LLM: '{title}' -> {clean_content} (cost: ¥{result.get('cost_cny'):.6f})")
            return clean_content
            
        # 若大模型吐出非规范枚举，退化为 best-effort 正则提纯
        for t in allowed_types:
            if t in clean_content:
                logger.info(f"Fallback matched category: {t}")
                return t
                
        logger.warning(f"Flash LLM returned non-compliant type: '{raw_content}'. Fallback to 'other'.")
        return "other"
        
    except Exception as e:
        logger.error(f"Failed to classify policy via Flash LLM: {e}. Fallback to 'other'.")
        return "other"
