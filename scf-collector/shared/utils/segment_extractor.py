# -*- coding: utf-8 -*-
"""
[E14-S2-P2-T3] 政策文本长文智能切片与提取器 segment_extractor.py
避免 SCF 内存溢出与 LLM Token 计费超支，精准剥离出最具前瞻性的政策走向内容。
"""

import re
import logging

logger = logging.getLogger(__name__)

def extract_key_segment(title: str, content_text: str, policy_type: str = "other") -> str:
    """
    智能过滤与长文切片提取主入口
    
    参数:
    - title: 政策标题
    - content_text: 政策原文全文 (可能是 Markdown 或 HTML 提纯后的 Text)
    - policy_type: 政策分类
    
    返回: 裁剪提纯后的政策关键段落
    """
    if not content_text:
        return ""
        
    total_length = len(content_text)
    
    # 限制阈值：小于等于 8000 字的政策，无需切片直接返回，保留百分之百的原文丰富度
    if total_length <= 8000:
        return content_text
        
    logger.info(f"Policy content length is too long ({total_length} chars). Triggering segment extractor...")
    
    # 1. 针对货币政策报告的专项定位提取
    if policy_type == "monetary_policy_report" or re.search(r"货币政策.*报告", title):
        logger.info("Monetary policy report detected. Running anchor regex extractor...")
        
        # 匹配季度货政执行报告的最后前瞻章节标题
        # 支持：“五、下一阶段主要政策思路”、“下一阶段主要政策措施” 等形式
        start_patterns = [
            r"(下一阶段(?:主要)?(?:货币)?政策思路)",
            r"(下一阶段(?:主要)?(?:工作)?政策措施)",
            r"(下一阶段主要政策安排)"
        ]
        
        start_pos = -1
        matched_str = ""
        for pat in start_patterns:
            match = re.search(pat, content_text)
            if match:
                start_pos = match.start()
                matched_str = match.group(1)
                break
                
        if start_pos != -1:
            logger.info(f"Successfully anchored policy outlook start paragraph at position {start_pos} via '{matched_str}'.")
            outlook_content = content_text[start_pos:]
            
            # 定位结束位置：下一个同级章节标题（例如：五、 变为 六、，或者 附录、附件、声明等）
            # 通常展望段落是最后一章，但为了防范超长，寻找诸如 “六、”、“附录”、“专栏” 等同级块
            end_patterns = [
                r"(\n\s*[一二三四五六七八九十]、)",
                r"(\n\s*附录)",
                r"(\n\s*附件)",
                r"(\n\s*专栏\s*\d+)"
            ]
            
            end_pos = -1
            for pat in end_patterns:
                # 在 outlook_content 的子串中查找结束符，排除开头的匹配
                end_match = re.search(pat, outlook_content[50:])
                if end_match:
                    end_pos = end_match.start() + 50
                    break
                    
            if end_pos != -1:
                final_segment = outlook_content[:end_pos]
                logger.info(f"Outlook section sliced successfully. Length: {len(final_segment)} chars (from outlook start to next chapter).")
                # 再次做个长度保护，防止内容依然超支
                if len(final_segment) <= 8000:
                    return final_segment
                else:
                    logger.info("Outlook section still too long, falling back to dynamic crop.")
            else:
                # 没有找到下一个章节，直接从锚定位置截取到结尾，并限制最大 8000 字
                final_segment = outlook_content[:8000]
                logger.info(f" Outlook section goes to EOF. Sliced length: {len(final_segment)} chars.")
                return final_segment
                
    # 2. 针对政府工作报告等的宏观提取
    if re.search(r"政府工作报告", title):
        logger.info("Government work report detected. Anchoring macro sections...")
        match = re.search(r"(今年(?:主要)?(?:预期)?目标和宏观政策|下一步主要工作任务)", content_text)
        if match:
            start_pos = match.start()
            return content_text[start_pos:start_pos + 8000]

    # 3. 兜底策略：如果上面的正则均没有命中，或者提取出的展望章节依然超标，则执行“首 4000 字 + 尾 2000 字”智能拼接
    logger.warning(
        f"Unable to structurally anchor key sections for long policy '{title}' (length: {total_length}). "
        "Falling back to 'First 4000 + Last 2000' dynamic merge..."
    )
    
    first_part = content_text[:4000]
    last_part = content_text[-2000:]
    
    merged_text = (
        f"{first_part}\n\n"
        "========================================================\n"
        f"... [此处省略中间 {total_length - 6000} 字无关联条文、地方执行数据或表格] ...\n"
        "========================================================\n\n"
        f"{last_part}"
    )
    
    logger.info(f"Dynamic fallback merge completed. Output length: {len(merged_text)} chars.")
    return merged_text
