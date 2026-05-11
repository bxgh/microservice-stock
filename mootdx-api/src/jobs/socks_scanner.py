"""
TDX SOCKS5 IP Scanner

Tests connectivity to standard TDX servers via a local SOCKS5 proxy (SSH Tunnel).
Authentication: None (SSH -D)
Proxy: localhost:1080
"""

import socket
import socks
import time
import logging
import asyncio
from mootdx.consts import CONFIG
from mootdx.quotes import Quotes

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger("socks-scanner")

import os

# Parse SOCKS_PROXY env (e.g., "127.0.0.1:8118")
proxy_env = os.getenv("SOCKS_PROXY", "127.0.0.1:1080")
if ":" in proxy_env:
    PROXY_HOST, PROXY_PORT = proxy_env.split(":")
    PROXY_PORT = int(PROXY_PORT)
else:
    PROXY_HOST, PROXY_PORT = "127.0.0.1", 1080

def test_connection_via_proxy(ip, port):
    """
    Test TCP connection via SOCKS5 proxy
    """
    s = socks.socksocket()
    s.set_proxy(socks.SOCKS5, PROXY_HOST, PROXY_PORT)
    s.settimeout(3)
    
    start = time.time()
    try:
        s.connect((ip, port))
        latency = (time.time() - start) * 1000
        s.close()
        return True, latency
    except Exception as e:
        return False, 0

async def verify_protocol_via_proxy(ip, port):
    """
    Test TDX Protocol over Proxy (Monkeypatching socket for Mootdx)
    """
    # Monkeypatch socket globally for this process
    original_socket = socket.socket
    socket.socket = socks.socksocket
    socks.set_default_proxy(socks.SOCKS5, PROXY_HOST, PROXY_PORT)
    
    start = time.time()
    try:
        loop = asyncio.get_event_loop()
        client = await loop.run_in_executor(
            None, 
            lambda: Quotes.factory(market='std', bestip=False, server=(ip, port))
        )
        data = await loop.run_in_executor(
            None,
            lambda: client.bars(category=9, market=0, code='000001', start=0, count=1)
        )
        
        latency = (time.time() - start) * 1000
        socket.socket = original_socket # Restore
        
        if data is not None and len(data) > 0:
            return True, latency
        return False, 0
    except Exception as e:
        socket.socket = original_socket # Restore
        return False, 0

async def run():
    logger.info(f"Scanning via SOCKS5 Proxy ({PROXY_HOST}:{PROXY_PORT})...")
    
    valid_nodes = []
    
    # Get standard list
    # Hardcoded standard list for reliable testing
    std_hosts = [
        ("招商证券深圳", "119.147.212.81", 7709),
        ("中信证券武汉", "119.97.185.5", 7709),
        ("光大证券上海", "124.71.187.122", 7709),
        ("广发证券北京", "218.60.29.136", 7709),
        ("安信证券", "59.36.5.11", 7709), # Known good direct
        ("海通核心", "175.6.5.153", 7709),
        ("方正证券", "119.29.51.30", 7709),
    ]
    
    logger.info(f"Testing {len(std_hosts)} nodes from Mootdx config...")
    
    for name, ip, port in std_hosts:
        # 1. TCP Connect
        ok, lat = test_connection_via_proxy(ip, port)
        if ok:
            # 2. Protocol Check (optional, can be slow, let's trust TCP for tunnel proof)
            logger.info(f"✅ [TCP] {name} ({ip}:{port}) - {lat:.1f}ms")
            valid_nodes.append((name, ip, port, lat))
        else:
            logger.warning(f"❌ [TCP] {name} ({ip}:{port}) - Unreachable")
            
    logger.info(f"Scan Complete. Found {len(valid_nodes)} reachable nodes via Tunnel.")
    
    # Print recommended string
    if valid_nodes:
        valid_nodes.sort(key=lambda x: x[3])
        hosts_str = ",".join([f"{x[1]}:{x[2]}" for x in valid_nodes[:5]])
        logger.info(f"Top 5 via Tunnel: {hosts_str}")

if __name__ == "__main__":
    asyncio.run(run())
