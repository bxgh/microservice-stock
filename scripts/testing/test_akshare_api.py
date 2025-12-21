#!/usr/bin/env python3
"""
AkShare API 真实数据验证测试脚本
测试所有接口是否返回有效的真实数据
"""
import requests
import time
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8001/api/v1"

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
    """测试财务数据接口"""
    endpoint = f"/finance/{code}"
    print_info(f"测试: {endpoint} (贵州茅台)")
    
    try:
        resp = requests.get(f"{BASE_URL}{endpoint}", timeout=30)
        if resp.status_code != 200:
            print_error(f"HTTP {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        expected_keys = ["total_revenue", "net_profit", "roe", "report_date", "code"]
        
        if validate_response(endpoint, data, expected_keys):
            print_success(f"财务数据: 营收={data.get('total_revenue')}, 净利润={data.get('net_profit')}, ROE={data.get('roe')}")
            return True
        return False
    except Exception as e:
        print_error(f"{endpoint}: {str(e)}")
        return False

def test_valuation_api(code: str = "600519"):
    """测试估值接口"""
    endpoint = f"/valuation/{code}"
    print_info(f"测试: {endpoint}")
    
    try:
        resp = requests.get(f"{BASE_URL}{endpoint}", timeout=30)
        if resp.status_code != 200:
            print_error(f"HTTP {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        expected_keys = ["pe", "price"]
        
        if validate_response(endpoint, data, expected_keys):
            print_success(f"估值数据: PE={data.get('pe')}, 价格={data.get('price')}")
            return True
        return False
    except Exception as e:
        print_error(f"{endpoint}: {str(e)}")
        return False

def test_valuation_history_api(code: str = "600519"):
    """测试历史估值接口"""
    endpoint = f"/valuation/{code}/history"
    print_info(f"测试: {endpoint}")
    
    try:
        resp = requests.get(f"{BASE_URL}{endpoint}?start_date=2024-01-01&end_date=2024-12-31", timeout=30)
        if resp.status_code != 200:
            print_error(f"HTTP {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        
        if validate_response(endpoint, data):
            print_success(f"历史估值数据: 共 {len(data)} 条记录")
            if len(data) > 0:
                print_info(f"  示例: 日期={data[0].get('date')}, PE={data[0].get('pe')}")
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
        resp = requests.get(f"{BASE_URL}{endpoint}", timeout=30)
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
        resp = requests.get(f"{BASE_URL}{endpoint}", timeout=30)
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
        resp = requests.get(f"{BASE_URL}{endpoint}?limit=10", timeout=30)
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
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}AkShare API 真实数据验证测试{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    # 等待服务启动
    print_info("检查服务状态...")
    max_retries = 10
    for i in range(max_retries):
        try:
            resp = requests.get(f"http://localhost:8001/health", timeout=2)
            if resp.status_code == 200:
                print_success("服务已就绪\n")
                break
        except:
            if i < max_retries - 1:
                print_info(f"等待服务启动... ({i+1}/{max_retries})")
                time.sleep(2)
            else:
                print_error("服务未启动，请先运行: cd akshare-api && uvicorn app.main:app")
                return
    
    # 运行所有测试
    tests = [
        ("财务数据", test_finance_api),
        ("实时估值", test_valuation_api),
        ("历史估值", test_valuation_history_api),
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
