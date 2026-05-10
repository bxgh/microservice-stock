import asyncio
import time
import json
import socket
import os
import sys
import logging
import random
from typing import List, Tuple, Dict
from pytdx.hq import TdxHq_API

# 确保能导入同一目录下的 tdx_pool
try:
    from .tdx_pool import current_bind_ip
except ImportError:
    import contextvars
    current_bind_ip = contextvars.ContextVar("current_bind_ip", default=None)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("tdx-discovery")

async def deep_test_node(host: str, port: int, local_ip: str = None) -> Dict:
    """协议级深度拨测：TCP 握手 + 获取数据"""
    loop = asyncio.get_event_loop()
    
    def sync_protocol_test():
        token = current_bind_ip.set(local_ip)
        try:
            api = TdxHq_API(raise_exception=True)
            # 1. 握手时间
            start_conn = time.time()
            if not api.connect(host, port, time_out=3.0):
                return False, 0, 0
            handshake_latency = (time.time() - start_conn) * 1000
            
            # 2. 深度数据获取 (获取市场 0 的证券数量)
            # 这是一个轻量级且通用的请求，能有效捕捉“幽灵节点”
            start_data = time.time()
            count = api.get_security_count(0)
            if count is None or count <= 0:
                api.close()
                return False, 0, 0
            
            data_latency = (time.time() - start_data) * 1000
            api.close()
            return True, handshake_latency, data_latency
        except Exception:
            return False, 0, 0
        finally:
            current_bind_ip.reset(token)

    try:
        success, h_lat, d_lat = await loop.run_in_executor(None, sync_protocol_test)
        if success:
            # 综合评分：数据响应权重占 70%
            weighted_score = (h_lat * 0.3) + (d_lat * 0.7)
            return {
                "host": host, "port": port, "handshake_ms": h_lat, 
                "data_ms": d_lat, "score": weighted_score,
                "success": True, "local_ip": local_ip
            }
    except Exception:
        pass
        
    return {"host": host, "port": port, "score": 99999, "success": False, "local_ip": local_ip}

async def matrix_discovery(hosts: List[Tuple], local_ips: List[str], top_n: int = 15):
    """深度矩阵扫描"""
    # 限制并发，防止因代理瓶颈导致虚高延迟
    sem = asyncio.Semaphore(10)
    
    async def limited_test(h, p, lip):
        async with sem:
            # 稍微错开启动时间
            await asyncio.sleep(random.uniform(0.1, 0.5))
            return await deep_test_node(h, p, lip)

    all_tasks = []
    for host_info in hosts:
        # 种子列表格式: [Name, Host, Port]
        h, p = host_info[1], host_info[2]
        for lip in local_ips:
            all_tasks.append(limited_test(h, p, lip))
            
    logger.info(f"🔍 Starting DEEP Discovery: {len(hosts)} nodes x {len(local_ips)} exports")
    results = await asyncio.gather(*all_tasks)
    
    # 过滤与排序
    valid = [r for r in results if r["success"]]
    valid.sort(key=lambda x: x["score"])
    
    logger.info(f"✅ Discovery Finished. Found {len(valid)} verified data-active nodes.")
    
    # 持久化 Top N
    ranked_list = []
    seen_nodes = set()
    for r in valid:
        node_id = f"{r['host']}:{r['port']}"
        if node_id not in seen_nodes:
            ranked_list.append(r)
            seen_nodes.add(node_id)
        if len(ranked_list) >= top_n:
            break
            
    output_path = "tdx_nodes_ranked.json"
    actual_path = os.path.join(os.path.dirname(__file__), output_path)
    
    with open(actual_path, 'w') as f:
        json.dump({"ranked_nodes": ranked_list, "last_update": time.ctime()}, f, indent=4)
        
    logger.info(f"💾 Ranked Top {len(ranked_list)} nodes saved to {actual_path}")
    
    for i, res in enumerate(ranked_list[:5]):
        logger.info(f"   🏆 No.{i+1} | {res['host']}:{res['port']} | Score: {res['score']:.1f}ms (Data RTT: {res['data_ms']:.1f}ms)")
        
    return ranked_list

if __name__ == "__main__":
    # 路径发现
    possible_paths = [
        "tdx_hosts_clean.json",
        "/app/src/core/tdx_hosts_clean.json",
        os.path.join(os.path.dirname(__file__), "tdx_hosts_clean.json")
    ]
    
    hosts_list = []
    for p in possible_paths:
        if os.path.exists(p):
            with open(p, 'r') as f:
                hosts_list = json.load(f).get("TDX", [])
            break
            
    lip_env = os.getenv("TDX_LOCAL_IPS", "192.168.151.41,192.168.151.47,192.168.151.49")
    ips = [ip.strip() for ip in lip_env.split(',') if ip.strip()]

    if not hosts_list:
        logger.error("No node list found.")
        sys.exit(1)

    asyncio.run(matrix_discovery(hosts_list, ips))
