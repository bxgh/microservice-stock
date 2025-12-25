#!/usr/bin/env python3
"""
股票历史数据完整性验证（修正版）
验证逻辑：
1. 检查每只股票是否有足够长的历史数据（至少应该有5年以上）
2. 对于老股票，应该有2015年之前的数据
3. 统计完整度时考虑绝对时间起点
"""
import pymysql
from datetime import datetime, date

DB_CONFIG = {
    "host": "sh-cdb-h7flpxu4.sql.tencentcdb.com",
    "port": 26300,
    "user": "root",
    "password": "alwaysup@888",
    "database": "alwaysup"
}

# 验证标准
EXPECTED_START_DATE = date(2015, 1, 1)  # 老股票应该有2015年之前的数据
MIN_YEARS_REQUIRED = 5  # 至少要有5年的历史数据
MIN_RECORDS_REQUIRED = 1000  # 至少要有1000条记录（约4年）

def get_all_synced_stocks():
    """获取所有已同步的股票统计"""
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    code, 
                    COUNT(*) as count, 
                    MIN(trade_date) as min_date, 
                    MAX(trade_date) as max_date,
                    DATEDIFF(MAX(trade_date), MIN(trade_date)) as days_span
                FROM stock_kline_daily
                GROUP BY code
                ORDER BY code
            """)
            return cursor.fetchall()
    finally:
        conn.close()

def classify_stock(code, count, min_date, max_date, days_span):
    """
    对股票数据分类：
    - 完整：历史起点 <= 2015-01-01 且记录数 >= 1000
    - 不足：历史起点 > 2020-01-01 或记录数 < 500
    - 中等：介于两者之间
    """
    years_span = days_span / 365 if days_span else 0
    
    # 判断标准
    has_old_data = min_date <= EXPECTED_START_DATE
    has_enough_records = count >= MIN_RECORDS_REQUIRED
    has_enough_years = years_span >= MIN_YEARS_REQUIRED
    
    if has_old_data and has_enough_records:
        return "完整", "✅"
    elif min_date >= date(2024, 1, 1):
        return "严重不足", "❌"
    elif count < 500:
        return "记录数不足", "⚠️"
    elif years_span < 3:
        return "时间跨度不足", "⚠️"
    else:
        return "部分完整", "⚠️"

def verify_all_stocks():
    """批量验证所有股票"""
    print("="*80)
    print("股票历史数据完整性验证（修正版）")
    print("="*80)
    print(f"验证标准:")
    print(f"  ✅ 完整: 数据起点 ≤ {EXPECTED_START_DATE} 且记录数 ≥ {MIN_RECORDS_REQUIRED}")
    print(f"  ⚠️  部分: 数据起点 > {EXPECTED_START_DATE} 但有一定历史")
    print(f"  ❌ 不足: 数据起点 ≥ 2024-01-01 或记录数太少")
    print("="*80)
    
    stocks = get_all_synced_stocks()
    
    if not stocks:
        print("❌ 数据库中没有找到任何股票数据！")
        return
    
    print(f"\n📊 已同步股票: {len(stocks)} 只\n")
    
    # 分类统计
    stats = {
        "完整": [],
        "部分完整": [],
        "记录数不足": [],
        "时间跨度不足": [],
        "严重不足": []
    }
    
    for code, count, min_date, max_date, days_span in stocks:
        category, icon = classify_stock(code, count, min_date, max_date, days_span)
        stats[category].append({
            "code": code,
            "count": count,
            "min_date": min_date,
            "max_date": max_date,
            "days_span": days_span
        })
    
    # 显示统计结果
    print("\n" + "="*80)
    print("验证结果汇总")
    print("="*80)
    
    total = len(stocks)
    print(f"✅ 完整（{EXPECTED_START_DATE}之前开始）: {len(stats['完整'])} 只 ({len(stats['完整'])/total*100:.1f}%)")
    print(f"⚠️  部分完整: {len(stats['部分完整'])} 只 ({len(stats['部分完整'])/total*100:.1f}%)")
    print(f"⚠️  记录数不足: {len(stats['记录数不足'])} 只 ({len(stats['记录数不足'])/total*100:.1f}%)")
    print(f"⚠️  时间跨度不足: {len(stats['时间跨度不足'])} 只 ({len(stats['时间跨度不足'])/total*100:.1f}%)")
    print(f"❌ 严重不足（仅2024年数据）: {len(stats['严重不足'])} 只 ({len(stats['严重不足'])/total*100:.1f}%)")
    
    # 显示问题股票样本
    if stats['严重不足']:
        print(f"\n{'='*80}")
        print(f"❌ 严重不足的股票（仅显示前10只）:")
        print(f"{'-'*80}")
        for stock in stats['严重不足'][:10]:
            print(f"  {stock['code']:12} | {stock['min_date']} ~ {stock['max_date']} | {stock['count']:4} 条")
        if len(stats['严重不足']) > 10:
            print(f"  ... 还有 {len(stats['严重不足']) - 10} 只")
    
    # 显示完整的股票样本（如果有）
    if stats['完整']:
        print(f"\n{'='*80}")
        print(f"✅ 数据完整的股票（显示前5只）:")
        print(f"{'-'*80}")
        for stock in stats['完整'][:5]:
            years = stock['days_span'] / 365
            print(f"  {stock['code']:12} | {stock['min_date']} ~ {stock['max_date']} | {stock['count']:5} 条 ({years:.1f}年)")
    
    # 总体评价
    print("\n" + "="*80)
    complete_ratio = len(stats['完整']) / total
    
    if complete_ratio >= 0.90:
        grade = "优秀"
        emoji = "🎉"
        comment = "90%以上股票拥有完整历史数据"
    elif complete_ratio >= 0.70:
        grade = "良好"
        emoji = "👍"
        comment = "大部分股票有较完整的历史数据"
    elif complete_ratio >= 0.30:
        grade = "中等"
        emoji = "⚠️"
        comment = "部分股票缺少历史数据，建议补全"
    else:
        grade = "不合格"
        emoji = "❌"
        comment = "大量股票缺少历史数据，需要重新同步！"
    
    print(f"{emoji} 总体评价: {grade}")
    print(f"   {comment}")
    print("="*80)
    
    return stats

if __name__ == "__main__":
    try:
        verify_all_stocks()
    except Exception as e:
        print(f"❌ 验证过程出错: {e}")
        import traceback
        traceback.print_exc()
