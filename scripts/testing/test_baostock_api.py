import requests
import json
import sys

# BaoStock API 配置
BASE_URL = "http://124.221.80.250:8001/api/v1"

def test_endpoint(name, path, params=None):
    url = f"{BASE_URL}{path}"
    print(f"\n测试 {name}: {url}")
    try:
        # 显式禁用代理以避免干扰
        proxies = {"http": None, "https": None}
        resp = requests.get(url, params=params, timeout=15, proxies=proxies)
        print(f"状态码: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                print(f"返回条数: {len(data)}")
                if len(data) > 0:
                    print("示例数据:", json.dumps(data[0], indent=2, ensure_ascii=False))
            elif isinstance(data, dict):
                # 如果是指数成分股，特殊处理
                if "constituents" in data:
                    print(f"成分股数量: {len(data['constituents'])}")
                    if len(data['constituents']) > 0:
                        print("示例数据:", json.dumps(data['constituents'][0], indent=2, ensure_ascii=False))
                else:
                    print("返回数据:", json.dumps(data, indent=2, ensure_ascii=False))
            return True
        else:
            print(f"错误响应: {resp.text}")
            return False
    except Exception as e:
        print(f"请求异常: {e}")
        return False

def run_tests():
    print("=== BaoStock API 全量调试测试 ===")
    
    # 1. 健康检查
    health_url = "http://124.221.80.250:8001/health"
    try:
        r = requests.get(health_url, timeout=5, proxies={"http": None, "https": None})
        print(f"健康检查 {health_url}: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"健康检查失败: {e}")

    # 2. 历史K线测试
    test_endpoint("历史K线 (日线)", "/history/kline/600519", {"frequency": "d", "start_date": "2024-12-01"})
    
    # 3. 指数成分测试 (沪深300)
    test_endpoint("指数成分 (沪深300)", "/index/cons/sz.399300")
    
    # 4. 指数成分测试 (上证50)
    test_endpoint("指数成分 (上证50)", "/index/cons/sh.000016")
    
    # 5. 行业分类测试
    test_endpoint("行业分类", "/industry/classify")
    
    # 6. 盈利能力数据测试
    test_endpoint("盈利能力 (贵州茅台)", "/finance/profit/600519")

    # 7. 历史估值测试 (正式上线)
    test_endpoint("历史估值 (正式接口)", "/valuation/sh.600519/history", {"start_date": "2024-12-01"})

if __name__ == "__main__":
    run_tests()
