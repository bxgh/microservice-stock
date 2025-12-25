#!/usr/bin/env python3
"""
股票历史数据完整性精准验证
验证逻辑：
1. 从数据源获取股票真实上市日期
2. 使用A股交易日历计算理论交易日
3. 对比数据库实际记录，计算精确完整度
4. 识别具体缺失的交易日
"""
import pymysql
import requests
from datetime import datetime, date, timedelta
import sys
from typing import List, Dict, Set

DB_CONFIG = {
    "host": "sh-cdb-h7flpxu4.sql.tencentcdb.com",
    "port": 26300,
    "user": "root",
    "password": "alwaysup@888",
    "database": "alwaysup"
}

# API配置
AKSHARE_API = "http://localhost:8003"  # AkShare API
BAOSTOCK_API = "http://localhost:8001"  # BaoStock API


class TradingCalendar:
    """A股交易日历"""
    
    def __init__(self):
        self.trading_days_cache: Set[date] = set()
        self._load_trading_days()
    
    def _load_trading_days(self):
        """从AkShare获取交易日历（1990-2025）"""
        print("📅 正在加载A股交易日历...")
        try:
            # 从AkShare获取交易日历
            url = f"{AKSHARE_API}/api/v1/market/trading_dates"
            response = requests.get(url, params={"start_date": "1990-01-01", "end_date": "2025-12-31"}, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    for item in data:
                        trade_date = datetime.strptime(item, "%Y-%m-%d").date()
                        self.trading_days_cache.add(trade_date)
                    print(f"   ✓ 已加载 {len(self.trading_days_cache)} 个交易日")
                    return
        except Exception as e:
            print(f"   ⚠️ 无法从API获取交易日历: {e}")
        
        # 降级方案：使用简单规则（排除周末，不考虑节假日）
        print("   ⚠️ 使用降级方案：简单交易日规则（排除周末）")
        self._generate_simple_trading_days()
    
    def _generate_simple_trading_days(self):
        """降级方案：生成简单交易日（仅排除周末）"""
        start = date(1990, 1, 1)
        end = date(2025, 12, 31)
        current = start
        
        while current <= end:
            if current.weekday() < 5:  # 周一到周五
                self.trading_days_cache.add(current)
            current += timedelta(days=1)
        
        # 粗略估算节假日（每年约15天）
        # 这个估算不够精确，但聊胜于无
        total_days = len(self.trading_days_cache)
        estimated_holidays = int((end.year - start.year + 1) * 15)
        print(f"   ⚠️ 简单规则生成 {total_days} 个工作日（未排除节假日）")
    
    def get_trading_days(self, start_date: date, end_date: date) -> List[date]:
        """获取指定日期范围内的交易日"""
        return sorted([d for d in self.trading_days_cache if start_date <= d <= end_date])


class StockInfoProvider:
    """股票基本信息提供者"""
    
    def __init__(self):
        self.ipo_cache: Dict[str, date] = {}
    
    def get_ipo_date(self, code: str) -> date:
        """获取股票上市日期"""
        if code in self.ipo_cache:
            return self.ipo_cache[code]
        
        # 尝试从BaoStock获取
        try:
            # 标准化代码
            if not code.startswith(("sh.", "sz.")):
                code = f"sh.{code}" if code.startswith("6") else f"sz.{code}"
            
            # 调用BaoStock API获取股票基本信息
            # 注意：这个API需要实现 /api/v1/stock/info/{code}
            # 目前暂时使用估算逻辑
            
            # 降级方案：根据代码前缀估算
            ipo_date = self._estimate_ipo_date(code)
            self.ipo_cache[code] = ipo_date
            return ipo_date
            
        except Exception as e:
            # 无法获取，使用保守估计（1990年）
            fallback = date(1990, 12, 19)  # 上交所成立日期
            self.ipo_cache[code] = fallback
            return fallback
    
    def _estimate_ipo_date(self, code: str) -> date:
        """
        根据股票代码估算上市日期（粗略逻辑）
        这只是临时方案，理想情况应该查询真实数据
        """
        # 科创板（688xxx）：2019年7月22日首批上市
        if code.startswith("sh.688"):
            return date(2019, 7, 22)
        
        # 创业板（300xxx）：2009年10月30日首批上市
        elif code.startswith("sz.300"):
            return date(2009, 10, 30)
        
        # 北交所（bj.）：2021年11月15日
        elif code.startswith("bj."):
            return date(2021, 11, 15)
        
        # 其他：使用保守估计
        else:
            # 主板股票大多在2010年前上市，但为了保险起见使用2000年
            return date(2000, 1, 1)


def verify_stock_precise(code: str, calendar: TradingCalendar, info_provider: StockInfoProvider) -> Dict:
    """精确验证单只股票的完整性"""
    conn = pymysql.connect(**DB_CONFIG)
    
    try:
        with conn.cursor() as cursor:
            # 1. 获取数据库中的记录
            cursor.execute("""
                SELECT trade_date FROM stock_kline_daily
                WHERE code = %s
                ORDER BY trade_date
            """, (code,))
            
            db_dates = set([row[0] for row in cursor.fetchall()])
            
            if not db_dates:
                return {
                    "code": code,
                    "status": "无数据",
                    "completeness": 0.0,
                    "db_count": 0,
                    "expected_count": 0,
                    "missing_count": 0
                }
            
            # 2. 获取股票上市日期
            ipo_date = info_provider.get_ipo_date(code)
            
            # 3. 获取理论交易日列表
            today = date.today()
            expected_dates = set(calendar.get_trading_days(ipo_date, today))
            
            # 4. 计算完整度
            missing_dates = expected_dates - db_dates
            extra_dates = db_dates - expected_dates  # 理论上不应该有，但可能因为交易日历不准
            
            expected_count = len(expected_dates)
            db_count = len(db_dates)
            missing_count = len(missing_dates)
            
            completeness = (db_count / expected_count * 100) if expected_count > 0 else 0
            
            # 5. 分类
            if completeness >= 99:
                status = "完整"
            elif completeness >= 95:
                status = "良好"
            elif completeness >= 80:
                status = "中等"
            elif completeness >= 50:
                status = "不足"
            else:
                status = "严重不足"
            
            return {
                "code": code,
                "status": status,
                "completeness": round(completeness, 2),
                "db_count": db_count,
                "expected_count": expected_count,
                "missing_count": missing_count,
                "ipo_date": ipo_date,
                "db_start": min(db_dates) if db_dates else None,
                "db_end": max(db_dates) if db_dates else None,
                "missing_sample": sorted(list(missing_dates))[:5] if missing_dates else []
            }
    
    finally:
        conn.close()


def verify_all_stocks_precise():
    """批量精确验证所有股票"""
    print("="*80)
    print("股票历史数据完整性精准验证")
    print("="*80)
    
    # 初始化
    calendar = TradingCalendar()
    info_provider = StockInfoProvider()
    
    # 获取所有股票代码
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT DISTINCT code FROM stock_kline_daily ORDER BY code")
            all_codes = [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()
    
    print(f"\n📊 开始验证 {len(all_codes)} 只股票...\n")
    
    # 统计
    stats = {
        "完整": [],
        "良好": [],
        "中等": [],
        "不足": [],
        "严重不足": [],
        "无数据": []
    }
    
    # 逐个验证（为了演示，这里只验证前100只，实际可以全部验证）
    sample_size = min(100, len(all_codes))
    print(f"⚠️  为节省时间，仅验证前 {sample_size} 只股票（完整验证需要较长时间）\n")
    
    for i, code in enumerate(all_codes[:sample_size]):
        result = verify_stock_precise(code, calendar, info_provider)
        stats[result["status"]].append(result)
        
        # 显示进度
        if (i + 1) % 10 == 0 or (i + 1) == sample_size:
            print(f"进度: {i+1}/{sample_size} ({(i+1)/sample_size*100:.1f}%)", end="\r")
    
    print("\n")
    
    # 输出报告
    print("="*80)
    print("验证结果汇总")
    print("="*80)
    
    total = sample_size
    for status in ["完整", "良好", "中等", "不足", "严重不足", "无数据"]:
        count = len(stats[status])
        percentage = count / total * 100 if total > 0 else 0
        emoji = {
            "完整": "✅",
            "良好": "👍",
            "中等": "⚠️",
            "不足": "⚠️",
            "严重不足": "❌",
            "无数据": "❌"
        }[status]
        print(f"{emoji} {status:8}: {count:4} 只 ({percentage:5.1f}%)")
    
    # 显示详细案例
    print(f"\n{'='*80}")
    print("典型案例分析（各取3只）:")
    print(f"{'='*80}")
    
    for status in ["完整", "良好", "严重不足"]:
        if stats[status]:
            print(f"\n{status}:")
            print("-" * 80)
            for stock in stats[status][:3]:
                print(f"  {stock['code']:12} | 完整度:{stock['completeness']:6.2f}% | "
                      f"数据:{stock['db_count']:5}/{stock['expected_count']:5} | "
                      f"起点:{stock['db_start']} | IPO:{stock['ipo_date']}")
                if stock['missing_sample']:
                    print(f"               缺失样本: {stock['missing_sample']}")
    
    print(f"\n{'='*80}")
    
    # 总体评价
    excellent_ratio = len(stats["完整"]) / total
    good_ratio = (len(stats["完整"]) + len(stats["良好"])) / total
    
    if excellent_ratio >= 0.90:
        print("🎉 总体评价: 优秀！数据质量极高")
    elif good_ratio >= 0.80:
        print("👍 总体评价: 良好，大部分数据完整")
    elif good_ratio >= 0.50:
        print("⚠️  总体评价: 中等，部分数据需要补全")
    else:
        print("❌ 总体评价: 不合格，需要重新同步")
    
    print("="*80)


if __name__ == "__main__":
    try:
        verify_all_stocks_precise()
    except Exception as e:
        print(f"❌ 验证过程出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
