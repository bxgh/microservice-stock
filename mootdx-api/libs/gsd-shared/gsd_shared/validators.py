"""
股票代码验证工具模块

提供 A 股代码合法性校验等通用验证函数
"""


from .config_loader import get_config

def is_valid_a_stock(code: str, include_bj: bool = True) -> bool:
    """
    判断是否为有效的 A 股代码 (含北京交易所)
    """
    if len(code) == 9 and '.' in code:
        code = code.split('.')[0]

    if not code or not isinstance(code, str) or len(code) != 6:
        return False
    
    config = get_config()
    prefixes = tuple(config.get("market_prefixes", []))
    
    return code.startswith(prefixes)

def is_valid_etf(code: str) -> bool:
    """
    判断是否为有效的 ETF 代码
    """
    if len(code) == 9 and '.' in code:
        code = code.split('.')[0]
        
    config = get_config()
    prefixes = tuple(config.get("etf_prefixes", []))
    if not prefixes:
        return False
        
    return code.startswith(prefixes)

def is_valid_index(code: str) -> bool:
    """
    判断是否为有效的指数代码 (配置驱动)
    """
    if not code:
        return False
        
    code = code.upper()
    
    # 模式识别: 在上证(SH)市场，000开头的基本都是指数 (除个别白名单外)
    # 此处处理 sh000 / 000...SH 格式
    if code.startswith('SH000') or code.endswith('.SH') and code.startswith('000'):
        return True

    if '.' in code:
        code = code.split('.')[0]
    elif code.startswith(('SH', 'SZ', 'BJ')):
        code = code[2:]
        
    if len(code) != 6:
        return False
        
    config = get_config()
    allowed_indices = set(config.get("indices", []))
    
    return code in allowed_indices
