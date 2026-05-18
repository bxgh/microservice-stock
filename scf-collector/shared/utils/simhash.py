# -*- coding: utf-8 -*-
"""
纯 Python 64 位 SimHash 算法与汉明距离计算工具
不依赖第三方编译包，以保证在云环境（SCF）中的 100% 平台兼容性。
"""

import hashlib
import re
from typing import List

class SimHash:
    """
    基于核心段落文本指纹的 64 位 SimHash 计算类
    """
    
    @staticmethod
    def tokenize(text: str) -> List[str]:
        """
        高健壮分词器：将英文单词、数字(含小数)提取出来，并将中文文本拆分为单字/双字，以极大提高无词典分词下 SimHash 的哈希稳定性。
        """
        if not text:
            return []
        text = text.lower()
        
        # 1. 匹配英文单词、数字(包含小数，如 3.10 或 0.25)
        eng_num_tokens = re.findall(r'[a-zA-Z0-9]+(?:\.[0-9]+)?', text)
        
        # 2. 匹配中文并切分成单字 (Unigram) 与双字邻接对 (Bigram)
        chinese_text = "".join(re.findall(r'[\u4e00-\u9fa5]+', text))
        chinese_tokens = []
        if chinese_text:
            # 单字
            chinese_tokens.extend(list(chinese_text))
            # 双字邻接对
            for i in range(len(chinese_text) - 1):
                chinese_tokens.append(chinese_text[i:i+2])
                
        tokens = eng_num_tokens + chinese_tokens
        if not tokens:
            tokens = list(text.strip())
        return tokens

    @classmethod
    def compute(cls, text: str) -> str:
        """
        计算 64位 SimHash 值，并以 16 位十六进制小写字符串输出。
        """
        if not text or not text.strip():
            return "0000000000000000"
            
        tokens = cls.tokenize(text)
        v = [0] * 64
        
        for token in tokens:
            # 使用 hashlib.md5 计算 128 位散列值，截取前 8 字节（64位）
            h = hashlib.md5(token.encode('utf-8')).digest()[:8]
            hash_val = int.from_bytes(h, byteorder='big')
            
            # 更新 64 维特征向量
            for i in range(64):
                bit = (hash_val >> i) & 1
                if bit == 1:
                    v[i] += 1
                else:
                    v[i] -= 1
                    
        # 降维：构建最终的 64位 SimHash
        simhash_val = 0
        for i in range(64):
            if v[i] >= 0:
                simhash_val |= (1 << i)
                
        # 格式化输出为 16位十六进制小写字串
        return f"{simhash_val:016x}"

def compute_simhash(text: str) -> str:
    """
    便捷接口：计算输入文本的核心段落 SimHash 指纹。
    """
    return SimHash.compute(text)

def hamming_distance(hash1: str, hash2: str) -> int:
    """
    计算两个 16 位十六进制 SimHash 指纹之间的汉明距离（Hamming Distance）。
    """
    if not hash1 or not hash2:
        return 64
        
    try:
        val1 = int(hash1, 16)
        val2 = int(hash2, 16)
    except ValueError:
        # 异常数据防死锁兜底
        return 64
        
    xor_val = val1 ^ val2
    # 统计异或值中 1 的 bit 数量
    return bin(xor_val).count('1')
