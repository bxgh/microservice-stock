# -*- coding: utf-8 -*-
"""
纯 Python 文本差分辅助工具
基于 difflib.unified_diff 句子级差分，适用于中英文金融文本高保真低消耗比对。
"""

import difflib
import re
from typing import List

def clean_lines(text: str) -> List[str]:
    """
    句子级分词/清理：将输入文本按句号（。）、分号（；）或换行符（\n）拆分成独立的语义句子，
    去除前后空白，过滤空行。
    """
    if not text:
        return []
    
    # 替换换行和常见语句结束符并切分
    raw_segments = re.split(r'[。；\n\r]+', text)
    
    cleaned = []
    for seg in raw_segments:
        seg_strip = seg.strip()
        if seg_strip:
            cleaned.append(seg_strip)
    return cleaned

def generate_text_diff(prev_text: str, curr_text: str) -> str:
    """
    利用 difflib.unified_diff 对语义句子列表进行对比，过滤文件头，保留带 + 和 - 的差异内容。
    若发现无差异则返回 '【无文本差异】'。
    """
    if not prev_text:
        prev_text = ""
    if not curr_text:
        curr_text = ""
        
    prev_lines = clean_lines(prev_text)
    curr_lines = clean_lines(curr_text)
    
    diff = difflib.unified_diff(
        prev_lines, curr_lines,
        fromfile='Previous', tofile='Current',
        lineterm='', n=1
    )
    
    diff_lines = list(diff)
    
    # 剥离 header
    clean_diff = []
    for line in diff_lines:
        if line.startswith('---') or line.startswith('+++') or line.startswith('@@'):
            continue
        clean_diff.append(line)
        
    if not clean_diff:
        return "【无文本差异】"
        
    return "\n".join(clean_diff)
