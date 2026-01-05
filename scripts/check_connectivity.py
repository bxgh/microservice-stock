
import socket
import sys
import time
import requests
import shutil

def check_port(host, port, timeout=3):
    """检测 TCP 端口连通性"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, f"Success"
    except socket.timeout:
        return False, "Timeout"
    except ConnectionRefusedError:
        return False, "Refused"
    except Exception as e:
        return False, str(e)

def check_http(url, timeout=5):
    """检测 HTTP 连通性"""
    try:
        resp = requests.get(url, timeout=timeout)
        return True, f"Status: {resp.status_code}"
    except Exception as e:
        return False, str(e)

def print_result(name, success, msg):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} | {name.ljust(30)} | {msg}")

def main():
    print("=" * 60)
    print("🔍 混合云网络连通性检查工具 (运行于内网服务器)")
    print("=" * 60)
    
    # 1. 配置您的云服务器 IP
    # 请在运行前修改此处，或通过命令行参数传入
    CLOUD_IP = sys.argv[1] if len(sys.argv) > 1 else "124.221.80.250"
    
    print(f"目标云服务器 IP: {CLOUD_IP}\n")

    # --- 第一部分: 云端基础设施连通性 ---
    print("[1. 云端基础设施检测]")
    # 检测 MySQL
    ok, msg = check_port(CLOUD_IP, 3306)
    print_result("MySQL (3306)", ok, msg)
    
    # 检测 Redis
    ok, msg = check_port(CLOUD_IP, 6379)
    print_result("Redis (6379)", ok, msg)
    
    # 检测 HTTP (Api Gateway)
    ok, msg = check_port(CLOUD_IP, 80)
    print_result("Nginx HTTP (80)", ok, msg)
    
    # 检测 SSH
    ok, msg = check_port(CLOUD_IP, 22)
    print_result("SSH (22)", ok, msg)
    print("-" * 60)

    # --- 第二部分: 外部数据源访问限制测试 ---
    print("\n[2. 外部数据源访问测试 (验证内网限制)]")
    
    # Baostock
    ok, msg = check_port("www.baostock.com", 80)
    print_result("Baostock (Web)", ok, msg)
    ok, msg = check_port("www.baostock.com", 10030)
    print_result("Baostock (TCP Data)", ok, msg)
    
    # AkShare / Eastmoney
    ok, msg = check_http("https://www.eastmoney.com")
    print_result("Eastmoney (AkShare)", ok, msg)
    
    # Wencai
    ok, msg = check_http("http://www.iwencai.com")
    print_result("iWencai (PyWencai)", ok, msg)
    print("-" * 60)

    # --- 第三部分: 建议 ---
    print("\n[3. 架构建议分析]")
    if not check_port(CLOUD_IP, 6379)[0] and not check_port(CLOUD_IP, 3306)[0]:
        print("⚠️  警告: 内网无法直连云端数据库/Redis。")
        print("   -> 必须使用 'HTTP API 中转' 方案，或者搭建 VPN/SSH 隧道。")
    elif not check_port(CLOUD_IP, 6379)[0]:
        print("⚠️  警告: 内网无法连接 Redis，但可能连上 MySQL（或都连不上）。")
        print("   -> 建议检查云服务器防火墙/安全组 6379 端口。")
    else:
        print("🎉 恭喜: 内网可以直连云端设施，架构实施将非常顺利！")

if __name__ == "__main__":
    main()
