
import asyncio
from mootdx.quotes import Quotes
import logging

# 配置日志以便看到 mootdx 内部的警告或错误
logging.basicConfig(level=logging.DEBUG)

def test_mootdx_transaction():
    client = Quotes.factory(market='std')
    
    # 测试 1: 上海主板 (600519 贵州茅台) - 无前缀
    print("\n--- Test 1: 600519 (No Prefix) ---")
    try:
        res1 = client.transaction(symbol='600519', start=0, offset=10)
        print(f"Result count: {len(res1) if res1 is not None else 0}")
        if res1 is not None and not res1.empty:
            print(res1.head(1).to_string())
    except Exception as e:
        print(f"Error: {e}")

    # 测试 2: 上海主板 (sh600519) - 带前缀
    print("\n--- Test 2: sh600519 (With Prefix) ---")
    try:
        res2 = client.transaction(symbol='sh600519', start=0, offset=10)
        print(f"Result count: {len(res2) if res2 is not None else 0}")
        if res2 is not None and not res2.empty:
            print(res2.head(1).to_string())
    except Exception as e:
        print(f"Error: {e}")

    # 测试 3: 深圳主板 (000001 平安银行) - 无前缀
    print("\n--- Test 3: 000001 (No Prefix) ---")
    try:
        res3 = client.transaction(symbol='000001', start=0, offset=10)
        print(f"Result count: {len(res3) if res3 is not None else 0}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_mootdx_transaction()
