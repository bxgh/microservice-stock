#!/usr/bin/env python3
"""
AkShare API 真实数据验证测试脚本
测试所有接口是否返回有效的真实数据
"""
import requests
import time
import json
from typing import Dict, Any

BASE_URL = "http://124.221.80.250:8003/api/v1"

# ANSI 颜色
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def print_success(msg: str):
    print(f"{GREEN}✓{RESET} {msg}")

def print_error(msg: str):
    print(f"{RED}✗{RESET} {msg}")

def print_warning(msg: str):
    print(f"{YELLOW}⚠{RESET} {msg}")

def print_info(msg: str):
    print(f"{BLUE}ℹ{RESET} {msg}")

def validate_response(endpoint: str, response: Any, expected_keys: list = None) -> bool:
    """验证响应数据是否有效"""
    if response is None:
        print_error(f"{endpoint}: 返回 None")
        return False
    
    if isinstance(response, dict):
        if "error" in response:
            print_error(f"{endpoint}: 返回错误 - {response.get('error')}")
            return False
        
        if expected_keys:
            for key in expected_keys:
                if key not in response:
                    print_error(f"{endpoint}: 缺少字段 '{key}'")
                    return False
                if response[key] is None:
                    print_warning(f"{endpoint}: 字段 '{key}' 为 None")
        
        # 检查是否有实际数据
        if not any(v for v in response.values() if v not in [None, "", [], {}]):
            print_warning(f"{endpoint}: 所有字段都为空")
            return False
    
    elif isinstance(response, list):
        if len(response) == 0:
            print_warning(f"{endpoint}: 返回空列表")
            return False
    
    return True

def test_finance_api(code: str = "600519"):
    """测试财务摘要接口"""
    endpoint = f"/finance/{code}"
    print_info(f"测试: {endpoint} (贵州茅台)")
    
    try:
        resp = requests.get(f"{BASE_URL}{endpoint}", timeout=30, proxies={"http": None, "https": None})
        if resp.status_code != 200:
            print_error(f"HTTP {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        expected_keys = ["total_revenue", "net_profit", "roe", "report_date", "code"]
        
        if validate_response(endpoint, data, expected_keys):
            print_success(f"财务摘要: 营收={data.get('total_revenue')}, 净利润={data.get('net_profit')}, ROE={data.get('roe')}")
            return True
        return False
    except Exception as e:
        print_error(f"{endpoint}: {str(e)}")
        return False

def test_finance_indicators_api(code: str = "600519"):
    """测试全量财务指标接口 (EPIC-002)"""
    endpoint = f"/finance/indicators/{code}"
    print_info(f"测试: {endpoint}")
    
    try:
        resp = requests.get(f"{BASE_URL}{endpoint}", timeout=30, proxies={"http": None, "https": None})
        if resp.status_code != 200:
            print_error(f"HTTP {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        expected_keys = ["ebitda", "fcf", "total_assets", "net_profit", "operating_income"]
        
        if validate_response(endpoint, data, expected_keys):
            print_success(f"全量财务指标: EBITDA={data.get('ebitda')}, FCF={data.get('fcf')}, 资产={data.get('total_assets')}")
            return True
        return False
    except Exception as e:
        print_error(f"{endpoint}: {str(e)}")
        return False

def test_valuation_api(code: str = "600519"):
    """测试实时估值接口"""
    endpoint = f"/valuation/{code}"
    print_info(f"测试: {endpoint}")
    
    try:
        resp = requests.get(f"{BASE_URL}{endpoint}", timeout=30, proxies={"http": None, "https": None})
        if resp.status_code != 200:
            print_error(f"HTTP {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        expected_keys = ["pe", "price"]
        
        if validate_response(endpoint, data, expected_keys):
            print_success(f"实时估值: PE={data.get('pe')}, 价格={data.get('price')}")
            return True
        return False
    except Exception as e:
        print_error(f"{endpoint}: {str(e)}")
        return False

def test_dragon_tiger_api():
    """测试龙虎榜接口"""
    endpoint = "/dragon_tiger/daily"
    print_info(f"测试: {endpoint}")
    
    try:
        resp = requests.get(f"{BASE_URL}{endpoint}", timeout=30, proxies={"http": None, "https": None})
        if resp.status_code != 200:
            print_error(f"HTTP {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        
        if validate_response(endpoint, data):
            print_success(f"龙虎榜数据: 共 {len(data)} 条记录")
            if len(data) > 0:
                print_info(f"  示例: {data[0].get('name')} ({data[0].get('code')}), 涨跌幅={data[0].get('change_pct')}%")
            return True
        return False
    except Exception as e:
        print_error(f"{endpoint}: {str(e)}")
        return False

def test_industry_api(code: str = "600519"):
    """测试个股行业信息接口"""
    endpoint = f"/industry/stock/{code}"
    print_info(f"测试: {endpoint}")
    
    try:
        resp = requests.get(f"{BASE_URL}{endpoint}", timeout=30, proxies={"http": None, "https": None})
        if resp.status_code != 200:
            print_error(f"HTTP {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        
        if validate_response(endpoint, data):
            print_success(f"行业信息: 行业={data.get('industry')}, 公司={data.get('name')}")
            return True
        return False
    except Exception as e:
        print_error(f"{endpoint}: {str(e)}")
        return False

def test_hot_rank_api():
    """测试热门排行接口"""
    endpoint = "/rank/hot"
    print_info(f"测试: {endpoint}")
    
    try:
        resp = requests.get(f"{BASE_URL}{endpoint}?limit=10", timeout=30, proxies={"http": None, "https": None})
        if resp.status_code != 200:
            print_error(f"HTTP {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        
        if validate_response(endpoint, data):
            print_success(f"热门排行: 共 {len(data)} 条记录")
            if len(data) > 0:
                print_info(f"  TOP1: {data[0].get('name')} ({data[0].get('code')}), 成交额={data[0].get('amount')}")
            return True
        return False
    except Exception as e:
        print_error(f"{endpoint}: {str(e)}")
        return False

def main():
    global BASE_URL
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}AkShare API 真实数据验证测试{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    # 确定要检查的健康检查地址
    health_url_cloud = f"{BASE_URL.replace('/api/v1', '')}/health"
    health_url_local = "http://localhost:8003/health"
    
    # 等待服务启动
    print_info(f"检查服务状态...")
    urls_to_try = [health_url_cloud, health_url_local]
    
    ready_url = None
    for url in urls_to_try:
        try:
            resp = requests.get(url, timeout=5, proxies={"http": None, "https": None})
            if resp.status_code == 200:
                ready_url = url.replace("/health", "/api/v1")
                print_success(f"服务已就绪: {url}\n")
                break
        except:
            continue
            
    if not ready_url:
        print_error("所有服务器均不可用，请检查服务是否运行")
        return

    BASE_URL = ready_url
    
    # 运行所有测试
    tests = [
        ("财务摘要", test_finance_api),
        ("全量财务指标", test_finance_indicators_api),
        ("实时估值", test_valuation_api),
        ("龙虎榜", test_dragon_tiger_api),
        ("行业信息", test_industry_api),
        ("热门排行", test_hot_rank_api),
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n{BLUE}--- {test_name} ---{RESET}")
        results[test_name] = test_func()
        time.sleep(1)  # 避免请求过快
    
    # 统计结果
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}测试结果汇总{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test_name, result in results.items():
        status = f"{GREEN}通过{RESET}" if result else f"{RED}失败{RESET}"
        print(f"  {test_name}: {status}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print(f"\n{GREEN}✓ 所有接口测试通过！{RESET}\n")
    else:
        print(f"\n{YELLOW}⚠ 部分接口测试失败，请检查日志{RESET}\n")

if __name__ == "__main__":
    main()
