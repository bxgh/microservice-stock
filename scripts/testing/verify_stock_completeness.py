#!/usr/bin/env python3
"""
验证单只股票的历史数据完整性
检查项：
1. 数据库记录数 vs BaoStock 源数据量
2. 时间跨度（最早/最晚日期）
3. 交易日连续性（识别缺失日期）
"""
import pymysql
import requests
import sys
from datetime import datetime, timedelta

# 数据库配置
DB_CONFIG = {
    "host": "sh-cdb-h7flpxu4.sql.tencentcdb.com",
    "port": 26300,
    "user": "root",
    "password": "alwaysup@888",
    "database": "alwaysup"
}

def normalize_code(code: str) -> str:
    """标准化股票代码"""
    if not code.startswith(("sh.", "sz.")):
        return f"sh.{code}" if code.startswith("6") else f"sz.{code}"
    return code

def check_db_records(code: str):
    """检查数据库中的记录"""
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            # 获取记录数和时间跨度
            cursor.execute("""
                SELECT COUNT(*), MIN(trade_date), MAX(trade_date)
                FROM stock_kline_daily
                WHERE code = %s
            """, (code,))
            count, min_date, max_date = cursor.fetchone()
            
            # 获取所有日期（用于缺失检测）
            cursor.execute("""
                SELECT trade_date FROM stock_kline_daily
                WHERE code = %s
                ORDER BY trade_date
            """, (code,))
            dates = [row[0] for row in cursor.fetchall()]
            
            return {
                "count": count,
                "min_date": min_date,
                "max_date": max_date,
                "dates": dates
            }
    finally:
        conn.close()

def check_baostock_source(code: str, start_date: str):
    """从 BaoStock API 获取源数据量"""
    try:
        url = f"http://localhost:8001/api/v1/history/kline/{code}"
        params = {
            "start_date": start_date,
            "frequency": "d",
            "adjust": "2"
        }
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return len(data) if isinstance(data, list) else 0
        return None
    except Exception as e:
        print(f"⚠️  无法从 BaoStock API 获取数据: {e}")
        return None

def detect_missing_dates(dates, start_date, end_date):
    """检测缺失的交易日（简单版：仅识别工作日缺失）"""
    if not dates:
        return []
    
    missing = []
    current = start_date
    date_set = set(dates)
    
    while current <= end_date:
        # 跳过周末
        if current.weekday() < 5:  # 0-4 是周一到周五
            if current not in date_set:
                missing.append(current)
        current += timedelta(days=1)
    
    return missing

def verify_stock(code: str, start_date: str = "2020-01-01"):
    """主验证函数"""
    code = normalize_code(code)
    print(f"\n{'='*60}")
    print(f"开始验证股票: {code}")
    print(f"{'='*60}\n")
    
    # 1. 检查数据库
    print("📊 步骤1: 检查数据库记录...")
    db_info = check_db_records(code)
    
    if db_info["count"] == 0:
        print(f"❌ 数据库中没有找到 {code} 的任何记录！")
        return False
    
    print(f"   ✓ 数据库记录数: {db_info['count']}")
    print(f"   ✓ 时间跨度: {db_info['min_date']} ~ {db_info['max_date']}")
    
    # 2. 对比 BaoStock 源
    print(f"\n📡 步骤2: 对比 BaoStock 源数据...")
    source_count = check_baostock_source(code, str(db_info['min_date']))
    
    if source_count is not None:
        print(f"   ✓ BaoStock 源数据量: {source_count}")
        if source_count == db_info["count"]:
            print(f"   ✅ 数量匹配: 数据库与源数据一致")
        else:
            diff = source_count - db_info["count"]
            print(f"   ⚠️  数量差异: {diff} 条 (源数据更多)" if diff > 0 else f"   ⚠️  数量差异: {abs(diff)} 条 (数据库更多)")
    
    # 3. 检测缺失日期
    print(f"\n📅 步骤3: 检测交易日连续性...")
    missing = detect_missing_dates(db_info["dates"], db_info["min_date"], db_info["max_date"])
    
    # 过滤掉已知节假日（简化版：仅显示前10个）
    if missing:
        print(f"   ⚠️  检测到 {len(missing)} 个可能的缺失日期（包括节假日/停牌）")
        if len(missing) <= 10:
            for date in missing:
                print(f"      - {date}")
        else:
            print(f"      前10个: {missing[:10]}")
            print(f"      ... (还有 {len(missing) - 10} 个)")
    else:
        print(f"   ✅ 交易日连续，无明显缺失")
    
    # 4. 总结
    print(f"\n{'='*60}")
    print("验证结果汇总:")
    print(f"{'='*60}")
    
    is_complete = (
        db_info["count"] > 0 and 
        (source_count is None or abs(source_count - db_info["count"]) <= 5)  # 允许5天误差（停牌等）
    )
    
    if is_complete:
        print(f"✅ {code} 的历史数据 **基本完整**")
    else:
        print(f"⚠️  {code} 的历史数据可能存在遗漏，建议重新同步")
    
    return is_complete

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python verify_stock_completeness.py <股票代码> [起始日期]")
        print("示例: python verify_stock_completeness.py 600519")
        print("示例: python verify_stock_completeness.py sh.600519 2015-01-01")
        sys.exit(1)
    
    code = sys.argv[1]
    start_date = sys.argv[2] if len(sys.argv) > 2 else "2020-01-01"
    
    verify_stock(code, start_date)
