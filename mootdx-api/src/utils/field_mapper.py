#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mootdx 字段映射和数据清洗工具
同步自 mootdx-source
"""

import pandas as pd

# 买卖方向映射表
BUYORSELL_MAP = {
    0: 'SELL',      # 主动卖出
    1: 'BUY',       # 主动买入
    2: 'NEUTRAL'    # 中性盘
}

def clean_tick_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    清洗和标准化分笔数据
    
    问题修复:
    1. 字段重命名: buyorsell -> type
    2. 单位转换: vol(手) -> volume(股)
    3. 方向映射: 0/1/2 -> SELL/BUY/NEUTRAL
    """
    if df.empty:
        return df
    
    df = df.copy()
    
    # 1. 字段重命名与转换
    rename_map = {}
    
    if 'vol' in df.columns:
        # 转换为股数 (1手=100股)
        df['volume'] = df['vol'] * 100
        rename_map['vol'] = 'volume_original'
    
    if 'buyorsell' in df.columns:
        # 映射买卖方向
        df['type'] = df['buyorsell'].map(BUYORSELL_MAP)
        rename_map['buyorsell'] = 'direction_original'
    
    # 2. 应用重命名
    if rename_map:
        df = df.rename(columns=rename_map)
    
    # 3. 标准化字段顺序
    standard_columns = ['time', 'price', 'volume', 'type', 'num']
    
    # 选择存在的列
    final_columns = [c for c in standard_columns if c in df.columns]
    
    return df[final_columns]

def standardize_mootdx_fields(df: pd.DataFrame, data_type: str = 'tick') -> pd.DataFrame:
    """
    统一标准化 mootdx 返回的各类数据
    """
    if df.empty:
        return df
    
    if data_type == 'tick':
        return clean_tick_data(df)
    
    if data_type == 'quotes':
        df = df.copy()
        # 识别 ETF 标的 (上海: 51, 56, 58; 深圳: 15)
        # 这里的识别逻辑可以根据需要进一步精确
        etf_prefixes = ('51', '56', '58', '15')
        
        if 'code' in df.columns:
            # 提取 IOPV: 对于 ETF，last_close 字段实际传输的是 IOPV
            # 增加 iopv 字段
            df['iopv'] = None
            
            # 使用向量化操作为符合条件的行设置 iopv
            is_etf = df['code'].str.startswith(etf_prefixes)
            if 'last_close' in df.columns:
                df.loc[is_etf, 'iopv'] = df.loc[is_etf, 'last_close']
                
        return df
    
    return df
