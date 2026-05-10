def clean_stock_code(code: str) -> str:
    """
    标准化为 TS 格式: 6位代码.市场 (如 600519.SH, 000001.SZ)
    
    支持格式:
    - 600519 -> 600519.SH (自动推断)
    - sh600519 -> 600519.SH
    - 600519.sh -> 600519.SH
    - SZ000001 -> 000001.SZ
    """
    if not code:
        return ""
    
    code = str(code).upper().strip()
    
    # 1. 识别并提取核心 6 位代码及市场信息
    market = None
    raw_code = code
    
    # 处理带点的后缀 (600519.SH)
    if '.' in code:
        parts = code.split('.')
        if len(parts[0]) == 6:
            raw_code, market = parts[0], parts[1]
        elif len(parts[-1]) == 6:
            raw_code, market = parts[-1], parts[0]
            
    # 处理前缀 (SH600519)
    elif code.startswith(('SH', 'SZ', 'BJ')):
        market = code[:2]
        raw_code = code[2:]
        
    # 处理后缀但没点 (600519SH)
    elif code.endswith(('SH', 'SZ', 'BJ')):
        market = code[-2:]
        raw_code = code[:-2]

    # 清洗 raw_code 中的非数字字符 (防御性)
    clean_numeric = "".join(filter(str.isdigit, raw_code))
    if len(clean_numeric) == 6:
        raw_code = clean_numeric

    # 2. 如果没有明确市场信息，则进行推断
    if not market or market not in ['SH', 'SZ', 'BJ']:
        if raw_code.startswith(('6', '9', '5')): # 沪市 (含 5 开头基金)
            market = 'SH'
        elif raw_code.startswith(('0', '3', '1')): # 深市 (含 1 开头基金)
            market = 'SZ'
        elif raw_code.startswith(('4', '8')): # 北交所
            market = 'BJ'
        else:
            market = 'SH' # 默认兜底
            
    return f"{raw_code}.{market}"
