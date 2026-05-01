"""
股票代码标准化工具
"""

def normalize_ts_code(code: str) -> str:
    """
    将各种格式的股票代码归一化为标准的 TS_CODE (如 600519.SH)
    支持格式:
    - 600519 -> 600519.SH
    - 000001 -> 000001.SZ
    - sh.600519 -> 600519.SH
    - 600519.SH -> 600519.SH
    """
    if not code:
        return ""
    
    code = str(code).upper().strip()
    
    # 1. 处理 sh.600519 或 sz.000001 这种前缀式格式
    if "." in code:
        parts = code.split(".")
        # 如果是前缀 (SH.600519)
        if parts[0].isalpha() and len(parts[0]) <= 3:
            return f"{parts[1]}.{parts[0]}"
        # 如果已经是后缀 (600519.SH)，直接返回
        if parts[1].isalpha() and len(parts[1]) <= 3:
            return code
        # 其他特殊情况（如行业指数 881001.WI），暂时透传
        return code
    
    # 2. 处理纯数字的情况，根据规律补齐后缀
    if code.isdigit():
        # 6字头、9字头：沪市
        if code.startswith(('6', '9')):
            return f"{code}.SH"
        # 0字头、3字头：深市
        elif code.startswith(('0', '3')):
            return f"{code}.SZ"
        # 4字头、8字头：北交所
        elif code.startswith(('4', '8')):
            return f"{code}.BJ"
        # 1字头：部分基金或特殊品种（通常也是沪市）
        elif code.startswith('1'):
            return f"{code}.SH"
            
    return code

def denormalize_to_baostock(ts_code: str) -> str:
    """转换为 BaoStock 格式 (sh.600519)"""
    if "." not in ts_code:
        ts_code = normalize_ts_code(ts_code)
    parts = ts_code.split(".")
    return f"{parts[1].lower()}.{parts[0]}"

def denormalize_to_tushare(code: str) -> str:
    """转换为 Tushare 格式 (已是标准 600519.SH)"""
    return normalize_ts_code(code)
