import requests
import json
import time

# PyWencai API 配置
BASE_URL = "http://124.221.80.250:8002/api/v1"

def test_endpoint(name, method, path, data=None, params=None):
    url = f"{BASE_URL}{path}"
    print(f"\n测试 {name}: {url}")
    try:
        proxies = {"http": None, "https": None}
        if method.upper() == "POST":
            resp = requests.post(url, json=data, timeout=30, proxies=proxies)
        else:
            resp = requests.get(url, params=params, timeout=30, proxies=proxies)
            
        print(f"状态码: {resp.status_code}")
        if resp.status_code == 200:
            result = resp.json()
            if isinstance(result, dict):
                if "data" in result:
                    print(f"数据条数: {len(result['data'])}")
                    if len(result['data']) > 0:
                        print("示例数据:", json.dumps(result['data'][0], indent=2, ensure_ascii=False))
                else:
                    print("结果:", json.dumps(result, indent=2, ensure_ascii=False))
            elif isinstance(result, list):
                print(f"列表长度: {len(result)}")
                if len(result) > 0:
                    print("示例数据:", json.dumps(result[0], indent=2, ensure_ascii=False))
            return True
        else:
            print(f"错误响应: {resp.text}")
            return False
    except Exception as e:
        print(f"请求异常: {e}")
        return False

def run_tests():
    print("=== PyWencai API 全量调试测试 ===")
    
    # 1. 健康检查
    health_url = "http://124.221.80.250:8002/health"
    try:
        r = requests.get(health_url, timeout=5, proxies={"http": None, "https": None})
        print(f"健康检查 {health_url}: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"健康检查失败: {e}")

    # 2. 自然语言选股测试
    test_endpoint("自然语言选股 (今日涨停)", "POST", "/query", data={"q": "今日涨停", "perpage": 10})
    
    # 3. 热门板块测试
    test_endpoint("热门板块", "GET", "/sector/hot", params={"limit": 10})

if __name__ == "__main__":
    run_tests()
