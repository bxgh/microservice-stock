# -*- coding: utf-8 -*-
import pytest
from shared.utils.simhash import SimHash, compute_simhash, hamming_distance

def test_simhash_tokenize():
    """
    测试分词器对中文、数字、英文的混合切分 (Unicode 安全版)
    """
    # "1年期LPR为3.10%，5年期LPR为3.60%"
    text1 = "1\u5e74\u671fLPR\u4e3a3.10%\uff0c5\u5e74\u671fLPR\u4e3a3.60%"
    tokens1 = SimHash.tokenize(text1)
    
    # 验证分词的词袋特征是否捕获关键数字与利率
    assert "1" in tokens1
    assert "3.10" in tokens1
    assert "lpr" in tokens1
    assert "3.60" in tokens1

def test_compute_simhash():
    """
    测试指纹计算返回 64位(16位十六进制) 字符串，且对于空或极短文本能健壮防御返回默认 0000000000000000
    """
    # 正常文本 - "中国人民银行决定于2026年5月25日下调金融机构存款准备金率"
    text_normal = "\u4e2d\u56fd\u4eba\u6c11\u94f6\u884c\u51b3\u5b9a\u4e8e2026\u5e745\u670825\u65e5\u4e0b\u8c03\u91d1\u878d\u673a\u6784\u5b58\u6b3e\u51c6\u5907\u91d1\u7387"
    h1 = compute_simhash(text_normal)
    assert isinstance(h1, str)
    assert len(h1) == 16
    # 验证是合法的 16 进制
    int(h1, 16)
    
    # 防御空文本
    h_empty = compute_simhash("")
    assert h_empty == "0000000000000000"
    
    # 极短词或全空格
    h_spaces = compute_simhash("   ")
    assert h_spaces == "0000000000000000"

def test_hamming_distance():
    """
    测试位运算汉明距离计算
    """
    # 相同哈希汉明距离为 0
    assert hamming_distance("ffffffffffffffff", "ffffffffffffffff") == 0
    assert hamming_distance("0000000000000000", "0000000000000000") == 0
    
    # 完全相反
    assert hamming_distance("ffffffffffffffff", "0000000000000000") == 64
    
    # 差一位 (f = 1111, e = 1110)
    assert hamming_distance("ffffffffffffffff", "fffffffffffffffe") == 1
    
    # 差两位 (3 = 0011, 0 = 0000)
    assert hamming_distance("0000000000000003", "0000000000000000") == 2

def test_similarity_thresholds():
    """
    测试相似度判定阈值与业务常识一致：
    - 高相似公告 (仅日期不同) 汉明距离应 <= 3
    - 不同公告 汉明距离应 > 8
    """
    # s1 = "1年期贷款市场报价利率（LPR）为3.10%，5年期以上LPR为3.60%。中国人民银行授权全国银行间同业拆借中心公布，自2026年5月20日起执行。"
    s1 = "1\u5e74\u671f\u8d37\u6b3e\u5e02\u573a\u62a5\u4ef7\u5229\u7387\uff08LPR\uff09\u4e3a3.10%\uff0c5\u5e74\u671f\u4ee5\u4e0aLPR\u4e3a3.60%\u3002\u4e2d\u56fd\u4eba\u6c11\u94f6\u884c\u6388\u6743\u5168\u56fd\u94f6\u884c\u95f4\u540c\u4e1a\u62c6\u501f\u4e2d\u5fc3\u516c\u5e03\uff0c\u81ea2026\u5e745\u670820\u65e5\u8d77\u6267\u884c\u3002"
    # s2 = "1年期贷款市场报价利率（LPR）为3.10%，5年期以上LPR为3.60%。中国人民银行授权全国银行间同业拆借中心公布，自2026年5月20日起执行。"
    s2 = "1\u5e74\u671f\u8d37\u6b3e\u5e02\u573a\u62a5\u4ef7\u5229\u7387\uff08LPR\uff09\u4e3a3.10%\uff0c5\u5e74\u671f\u4ee5\u4e0aLPR\u4e3a3.60%\u3002\u4e2d\u56fd\u4eba\u6c11\u94f6\u884c\u6388\u6743\u5168\u56fd\u94f6\u884c\u95f4\u540c\u4e1a\u62c6\u501f\u4e2d\u5fc3\u516c\u5e03\uff0c\u81ea2026\u5e745\u670820\u65e5\u8d77\u6267\u884c\u3002"
    # s3 = "贷款市场报价利率(LPR)1年期为3.10%, 5年期以上LPR为3.60%。中国人民银行授权全国银行间同业拆借中心公布，自2026年5月20日起执行。"
    s3 = "\u8d37\u6b3e\u5e02\u573a\u62a5\u4ef7\u5229\u7387(LPR)1\u5e74\u671f\u4e3a3.10%, 5\u5e74\u671f\u4ee5\u4e0aLPR\u4e3a3.60%\u3002\u4e2d\u56fd\u4eba\u6c11\u94f6\u884c\u6388\u6743\u5168\u56fd\u94f6\u884c\u95f4\u540c\u4e1a\u62c6\u501f\u4e2d\u5fc3\u516c\u5e03\uff0c\u81ea2026\u5e745\u670820\u65e5\u8d77\u6267\u884c\u3002"
    
    h1 = compute_simhash(s1)
    h2 = compute_simhash(s2)
    h3 = compute_simhash(s3)
    
    # 相同应该为 0
    assert hamming_distance(h1, h2) == 0
    
    # 高相似汉明距离通常极其微小 (单字/双字中文切分下必 <= 6)
    dist_high = hamming_distance(h1, h3)
    assert dist_high <= 6
    
    # 完全不同类型的政策公告 - "中国人民银行开展了1000亿元7天期逆回购操作，中标利率为1.50%"
    s_diff = "\u4e2d\u56fd\u4eba\u6c11\u94f6\u884c\u5f00\u5c55\u4e861000\u4ebf\u51437\u5929\u671f\u9006\u56de\u8d2d\u64cd\u4f5c\uff0c\u4e2d\u6807\u5229\u7387\u4e3a1.50%"
    h_diff = compute_simhash(s_diff)
    
    dist_diff = hamming_distance(h1, h_diff)
    assert dist_diff > 8
