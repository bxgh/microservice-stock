"""
TDX 动态 IP 扫描器 (Scanner) - Enhanced

负责从指定网段(Priority CIDRs) 和 标准配置列表 中挖掘高质量的 TDX 行情服务器 IP。
设计原则：
1. 定向侦察: 优先扫描华为云、海通等优质网段。
2. 全面覆盖: 扫描 Mootdx 默认配置的 30+ 个节点。
3. 隐蔽行动: 使用随机延迟(Jitter)和低并发防止触发风控。
4. 严格考核: 仅录用延迟低且数据完整的节点。
"""

import asyncio
import logging
import os
import random
import socket
import struct
import time
from typing import List, Tuple, Optional
import redis.asyncio as redis
from redis.asyncio.cluster import RedisCluster
from mootdx.quotes import Quotes
from mootdx.consts import CONFIG

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("tdx-scanner")

# 优先级网段 (CIDR)
PRIORITY_NETWORKS = [
    ("124.71.187", 7709), 
    ("119.147.212", 7709),
    ("139.9.51", 7709)
]

REDIS_KEY_VERIFIED = "tdx:verified_ips"
SCAN_CONCURRENCY = 20

class IPScanner:
    def __init__(self):
        self.redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
        self.redis_port = int(os.getenv("REDIS_PORT", 6379))
        self.redis_password = os.getenv("REDIS_PASSWORD", "")
        self.redis = None

    async def initialize(self):
        if not self.redis_password:
            self.redis_password = None
            
        if os.getenv("REDIS_CLUSTER") == "true":
            self.redis = RedisCluster(
                host=self.redis_host, 
                port=self.redis_port, 
                password=self.redis_password, 
                decode_responses=True
            )
            mode = "Cluster"
        else:
            address = f"redis://:{self.redis_password or ''}@{self.redis_host}:{self.redis_port}/0"
            self.redis = redis.from_url(address, decode_responses=True)
            mode = "Standalone"

        logger.info(f"Connected to Redis at {self.redis_host}:{self.redis_port} ({mode})")

    async def close(self):
        if self.redis:
            await self.redis.close()

    def generate_ips(self, base_ip: str) -> List[str]:
        ips = []
        base_parts = base_ip.split('.')[:3]
        prefix = ".".join(base_parts)
        for i in range(1, 255):
            ips.append(f"{prefix}.{i}")
        random.shuffle(ips)
        return ips

    async def verify_ip(self, ip: str, port: int) -> Optional[Tuple[str, int, float]]:
        # Jitter
        await asyncio.sleep(random.uniform(0.1, 0.5))
        
        # Connect Test
        try:
            future = asyncio.open_connection(ip, port)
            reader, writer = await asyncio.wait_for(future, timeout=2.0)
            writer.close()
            await writer.wait_closed()
        except Exception:
            return None

        # Protocol Test
        start_time = time.time()
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
            
            latency = (time.time() - start_time) * 1000
            
            if data is not None and len(data) > 0 and latency < 300: # Relaxed to 300ms
                logger.info(f"✨ 发现优质节点: {ip}:{port} (延迟: {latency:.1f}ms)")
                return (ip, port, latency)
            else:
                return None
                
        except Exception as e:
            return None

    async def scan_network(self, base_ip: str, port: int):
        logger.info(f"开始扫描网段: {base_ip}.0/24 ...")
        ips = self.generate_ips(base_ip)
        return await self._batch_scan(ips, port)

    async def _batch_scan(self, ips: List[str], port: int):
        sem = asyncio.Semaphore(SCAN_CONCURRENCY)
        valid_ips = []
        
        async def _worker(target_ip, target_port):
            async with sem:
                result = await self.verify_ip(target_ip, target_port)
                if result:
                    valid_ips.append(result)

        tasks = [_worker(ip, port) for ip in ips]
        if tasks:
            await asyncio.gather(*tasks)
        return valid_ips

    async def run(self):
        await self.initialize()
        
        all_valid = []
        
        # 1. Subnet Scan
        for base, port in PRIORITY_NETWORKS:
            valid = await self.scan_network(base, port)
            all_valid.extend(valid)
            
        # 2. Standard List Scan
        logger.info("开始扫描标准列表 (Standard List)...")
        std_hosts = []
        # Support various config formats if necessary, assuming [Name, IP, Port]
        # CONFIG.BESTIP['TDX'] is list of lists
        for item in CONFIG.BESTIP['TDX']:
             if len(item) >= 3:
                 std_hosts.append((item[1], int(item[2])))
        
        # Filter out ones we already found or are scanning
        found_ips = {x[0] for x in all_valid}
        scan_list = [x for x in std_hosts if x[0] not in found_ips]
        
        # Batch scan list (ports may vary but standard list is mostly 7709, we'll respect config)
        sem = asyncio.Semaphore(SCAN_CONCURRENCY)
        async def _worker(ip, port):
            async with sem:
                res = await self.verify_ip(ip, port)
                if res:
                    all_valid.append(res)
        
        tasks = [_worker(ip, port) for ip, port in scan_list]
        if tasks:
            await asyncio.gather(*tasks)
            
        logger.info(f"标准列表扫描完成")

        # Save
        if all_valid:
            try:
                pipeline = self.redis.pipeline()
                await pipeline.delete(REDIS_KEY_VERIFIED)
                for ip, port, lat in all_valid:
                    await pipeline.sadd(REDIS_KEY_VERIFIED, f"{ip}:{port}")
                await pipeline.execute()
                logger.info(f"已更新 Redis {REDIS_KEY_VERIFIED}: 共 {len(all_valid)} 个节点")
            except Exception as e:
                logger.error(f"Pipeline error: {e}")
                await self.redis.delete(REDIS_KEY_VERIFIED)
                for ip, port, lat in all_valid:
                    await self.redis.sadd(REDIS_KEY_VERIFIED, f"{ip}:{port}")
        else:
            logger.warning("本次扫描未发现有效节点")

        await self.close()

if __name__ == "__main__":
    scanner = IPScanner()
    asyncio.run(scanner.run())
