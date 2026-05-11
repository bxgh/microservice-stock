"""
TDX 多节点连接池

使用 asyncio.Queue 实现独占式资源管理，确保并发安全。
提供多节点支持，将请求分散到多个 TDX 服务器以突破单节点并发限制。
"""

import asyncio
import logging
import random
import socket
import os
import sys
import json
import contextvars
from typing import List, Optional, Tuple
from mootdx.quotes import Quotes
from mootdx.utils import to_data, get_stock_market, get_frequency
from pytdx.hq import TdxHq_API

# --- Context Variable for Source IP Binding ---
# 允许在并发创建连接时通过 contextvars 指定特定的源 IP
current_bind_ip = contextvars.ContextVar("current_bind_ip", default=None)

# --- Monkey Patch: Force Source IP for TDX Traffic ---
_OriginalSocket = socket.socket

class _BoundSocket(_OriginalSocket):
    def connect(self, address):
        # 1. 识别 TDX 流量
        is_tdx = isinstance(address, tuple) and len(address) >= 2 and (address[1] in [7701, 7709, 7711, 7727, 7719])
        
        # 2. 获取目标绑定 IP
        bind_ip = current_bind_ip.get() or os.getenv("TDX_BIND_IP")
        
        if is_tdx and bind_ip:
            try:
                # 检查是否已经绑定了地址 (getsockname 如果非 0.0.0.0 则说明已绑)
                # 注意: 在某些系统或 Python 版本中，未绑定的 socket getsockname 会报错或返回 0.0.0.0
                try:
                    curr_name = self.getsockname()
                    already_bound = curr_name and curr_name[0] != "0.0.0.0"
                except:
                    already_bound = False
                
                if not already_bound:
                    self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    self.bind((bind_ip, 0))
            except Exception as e:
                # 只在真实发生错误（非已绑定错误）时记录
                if "[Errno 22]" not in str(e):
                    sys.stderr.write(f"MonkeyPatch: Bind {bind_ip} FAILED: {e}\n")
        
        super().connect(address)

# 全局覆盖
socket.socket = _BoundSocket

# 检查 TrafficStatSocket 的导出情况
try:
    import pytdx.base_socket_client
    # 强制让 pytdx.base_socket_client 看到最新的 socket.socket
    pytdx.base_socket_client.socket.socket = _BoundSocket
except:
    pass

# --- End Monkey Patch ---

logger = logging.getLogger("tdx-pool")

class RobustQuotes:
    """
    Robust wrapper for TdxHq_API to bypass mootdx initialization issues and provide standardized interface.
    Implements mootdx Quotes interface via composition over PyTDX.
    """
    def __init__(self, server=None, timeout=15, **kwargs):
        self.server = server
        self.timeout = timeout
        ip, port = self.server
        
        # Direct initialization of TdxHq_API
        self.client = TdxHq_API(auto_retry=True, raise_exception=True)
        try:
            self.client.connect(ip, int(port), time_out=timeout)
        except Exception as e:
            logger.error(f"RobustQuotes connect failed to {ip}:{port} : {e}")
            raise

    def close(self):
        try:
            if hasattr(self, 'client') and self.client:
                self.client.close()
        except Exception:
            # Ignore errors during close (e.g. TdxConnectionError if already disconnected)
            pass

    def __del__(self):
        self.close()

    @property
    def api(self):
         # Helper for watchdog logging
         return self.client.api if hasattr(self.client, 'api') else None

    # --- Mootdx Interface Implementation ---

    def quotes(self, symbol=None):
        symbol = symbol or []
        if isinstance(symbol, str):
             symbol = [symbol]

        params = []
        for s in symbol:
             m, c = self._clean_symbol(s)
             # PyTDX 在批量请求中如果遇到无法识别的市场 (如北交所的 2)，会导致整批请求崩溃并返回 None
             if m not in (0, 1):
                 continue
             params.append((m, c))

        def _reboot_client() -> bool:
            try:
                ip, port = self.server
                self.client.close()
                self.client = type(self.client)(auto_retry=True, raise_exception=True)
                # 使用短超时防止重连死节点造成的严重拥堵
                if self.client.connect(ip, int(port), time_out=2):
                    return True
                return False
            except Exception:
                return False

        # 通达信协议单次最多支持 80 只，超过需分批请求后合并
        BATCH_LIMIT = 80
        all_data = []
        for i in range(0, len(params), BATCH_LIMIT):
            batch = params[i:i + BATCH_LIMIT]
            try:
                batch_result = self.client.get_security_quotes(batch)
            except Exception:
                batch_result = None
                
            if batch_result:
                all_data.extend(batch_result)
            else:
                if not _reboot_client():
                    logger.warning(f"TDX Node {self.server} is dead, skipping poison pill fallback.")
                    break
                    
                # Poison Pill 降级策略
                sub_size = 6
                for j in range(0, len(batch), sub_size):
                    sub_batch = batch[j:j+sub_size]
                    try:
                        sub_res = self.client.get_security_quotes(sub_batch)
                        if sub_res:
                            all_data.extend(sub_res)
                    except Exception:
                        if not _reboot_client():
                            break

        return to_data(all_data, symbol=symbol, client=self)
        
    def _clean_symbol(self, symbol):
        s = str(symbol).upper()
        
        # 1. 优先从前后缀提取市场 ID (1=上海, 0=深圳, 2=北京)
        m = None
        if '.SH' in s or s.startswith('SH'):
            m = 1
        elif '.SZ' in s or s.startswith('SZ'):
            m = 0
        elif '.BJ' in s or s.startswith('BJ'):
            m = 2
            
        # 2. 提取 6 位纯数字代码
        c = s.split('.')[0] if '.' in s else s
        c = c[2:] if c.startswith(('SH','SZ','BJ')) else c
        # 防御性：确保 c 是纯数字并补齐 6 位
        c = "".join(filter(str.isdigit, c))
        if len(c) < 6:
            c = c.zfill(6)
            
        # 3. 如果没能从前后缀识别，则使用 mootdx 原生逻辑推断
        if m is None:
            m = get_stock_market(c)
            
        return m, c

    def transaction(self, symbol, start=0, offset=800, **kwargs):
        m, c = self._clean_symbol(symbol)
        data = self.client.get_transaction_data(m, c, start, offset)
        return to_data(data, symbol=symbol, client=self)

    def transactions(self, symbol, date, start=0, offset=800, **kwargs):
        m, c = self._clean_symbol(symbol)
        data = self.client.get_history_transaction_data(m, c, start, offset, int(date))
        return to_data(data, symbol=symbol, client=self)
        
    def bars(self, frequency, symbol, start=0, offset=800, **kwargs):
        if isinstance(frequency, str):
             frequency = get_frequency(frequency)
        m, c = self._clean_symbol(symbol)
        
        # PyTDX uses get_security_bars for standard market
        data = self.client.get_security_bars(frequency, m, c, start, offset)
        return to_data(data, symbol=symbol, client=self)
        
    def index_bars(self, symbol, frequency, start=0, offset=800, **kwargs):
        if isinstance(frequency, str):
             frequency = get_frequency(frequency)
        m, c = self._clean_symbol(symbol)
        
        # PyTDX index_bars parameters: (category, market, code, start, count)
        data = self.client.get_index_bars(frequency, m, c, start, offset)
        return to_data(data, symbol=symbol, client=self)

    def finance(self, symbol):
         m, c = self._clean_symbol(symbol)
         data = self.client.get_finance_info(m, c)
         return to_data(data, symbol=symbol, client=self)

    def xdxr(self, symbol):
         m, c = self._clean_symbol(symbol)
         data = self.client.get_xdxr_info(m, c)
         return to_data(data, symbol=symbol, client=self)
         
    def stocks(self, market=None):
        # Limited implementation: PyTDX requires iteration to fetch all.
        # Check standard mootdx implementation if critical.
        # For now return empty or simple list if market specific.
        return None 

class TDXClientPool:
    """
    TDX 多节点连接池 (Thread-Safe Queue Implementation)
    
    使用 asyncio.Queue 管理连接资源，确保每个客户端同一时间只能被一个任务独占使用。
    支持多源 IP (Multiple NICs) 绑定，实现最大化外网并发能力。
    """
    
    def __init__(self, size: int = 3):
        self.size = size
        self.queue = asyncio.Queue() # 资源池
        self._lock = asyncio.Lock()
        self._initialized = False
        self._all_clients = [] 
        self._watchdog_task = None
        
        # 服务器与源 IP 配置
        self.target_servers = []
        self.local_ips = []
        self.target_server_strategy = 'list'
    
    async def initialize(self) -> None:
        if self._initialized:
            return
        
        async with self._lock:
            if self._initialized:
                return
            
            # 1. 获取本地多网卡 IP 配置
            env_local_ips = os.getenv("TDX_LOCAL_IPS", "")
            if env_local_ips:
                self.local_ips = [ip.strip() for ip in env_local_ips.split(',')]
            else:
                # 回退到单 IP 环境变量
                single_ip = os.getenv("TDX_BIND_IP")
                self.local_ips = [single_ip] if single_ip else []
            
            logger.info(f"正在初始化 TDX 连接池 (Size={self.size}, Locals={self.local_ips or 'AUTO'})")
            
            # 2. 获取目标服务器配置 (优先加载高评分节点)
            ranked_servers = self._load_ranked_nodes()
            
            auto_discover = os.getenv("TDX_AUTO_DISCOVER", "false").lower() == "true"
            env_hosts = os.getenv("TDX_HOSTS", "")
            
            if ranked_servers:
                self.target_servers = ranked_servers
                self.target_server_strategy = 'ranked'
                logger.info(f"✨ 已加载 {len(ranked_servers)} 个高评分节点作为首选池")
            elif auto_discover:
                self.target_server_strategy = 'auto'
            elif env_hosts:
                parsed_servers = []
                for s in env_hosts.split(','):
                    parts = s.strip().split(':')
                    if len(parts) == 2:
                        parsed_servers.append((parts[0], int(parts[1])))
                self.target_servers = parsed_servers
                self.target_server_strategy = 'list'
            else:
                # 默认高分节点 (2026 湖南电信集群)
                self.target_servers = [
                    ('175.6.5.153', 7709), ('175.6.5.154', 7709), ('175.6.5.155', 7709),
                    ('175.6.5.156', 7709), ('175.6.5.150', 7709), ('175.6.5.151', 7709)
                ]
                self.target_server_strategy = 'list'

            # 3. 建立连接并存入池中
            successful_count = 0
            for i in range(self.size):
                # 决定该连接使用的本地 IP (轮询)
                bind_ip = self.local_ips[i % len(self.local_ips)] if self.local_ips else None
                
                # 设置 ContextVars 并在线程池中创建客户端
                token = current_bind_ip.set(bind_ip)
                try:
                    client = await self._create_client_with_retry(i)
                    if client:
                        self.queue.put_nowait(client)
                        self._all_clients.append(client)
                        successful_count += 1
                        if bind_ip:
                            logger.debug(f"  ✓ Connection {i} bound to {bind_ip}")
                finally:
                    current_bind_ip.reset(token)
            
            if successful_count == 0:
                logger.error("Pool init failed: 0 connections available")
            
            # 启动健康巡检
            self._watchdog_task = asyncio.create_task(self._watchdog_loop())
            
            self._initialized = True
            logger.info(f"✓ TDX Pool Ready ({successful_count}/{self.size} available)")

    async def _create_client_with_retry(self, index: int) -> Optional[RobustQuotes]:
        """创建单个 TDX 客户端，带策略路由"""
        loop = asyncio.get_event_loop()
        try:
            if self.target_server_strategy == 'auto':
                # Auto strategy uses mootdx internal bestip logic
                client = await loop.run_in_executor(
                    None, lambda: Quotes.factory(market='std', bestip=True)
                )
            else:
                # 'list' 或 'ranked' 策略：循环使用已知节点
                server = self.target_servers[index % len(self.target_servers)]
                client = await loop.run_in_executor(
                    None, lambda: RobustQuotes(server=server, timeout=4)
                )
            return client
        except Exception as e:
            logger.warning(f"  Node {index + 1} init failed: {e}")
            return None

    async def _watchdog_loop(self):
        """盘中巡检协程：保持连接热度，自动替换坏死连接"""
        logger.info("📡 TDX Pool Watchdog STARTED")
        await asyncio.sleep(30) # 启动后延迟 30s 开始巡检
        
        while True:
            try:
                # 1. 估算巡检窗口
                # 我们逐个检查队列里的空闲客户端
                qsize = self.queue.qsize()
                if qsize > 0:
                    logger.debug(f"🔍 Watchdog: 正在检查 {qsize} 个空闲连接...")
                    
                    for _ in range(qsize):
                        try:
                            # 尝试非阻塞获取，如果获取不到说明正在被使用
                            client = self.queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                            
                        # 执行轻量级健康检查 (get_security_count)
                        is_healthy = await self._check_client_health(client)
                        
                        if is_healthy:
                            self.queue.put_nowait(client)
                        else:
                            host = getattr(getattr(client, 'client', None), 'api', None)
                            host_str = f"{getattr(host, 'host', 'unknown')}:{getattr(host, 'port', '0')}"
                            logger.warning(f"♻️ Watchdog: 检测到坏死或响应慢连接 ({host_str}), 正在替换...")
                            
                            # 关闭旧连接
                            try: client.client.close()
                            except: pass
                            
                            async with self._lock:
                                if client in self._all_clients:
                                    self._all_clients.remove(client)
                                    
                            # 2. 选择一个本地 IP 进行替换
                            bind_ip = self.local_ips[random.randint(0, len(self.local_ips)-1)] if self.local_ips else None
                            token = current_bind_ip.set(bind_ip)
                            
                            try:
                                # 随机等待 1-3s 避让，然后建立新连接
                                await asyncio.sleep(random.uniform(1, 3))
                                new_client = await self._create_client_with_retry(random.randint(0, 100))
                                
                                if new_client:
                                    async with self._lock:
                                        self.queue.put_nowait(new_client)
                                        self._all_clients.append(new_client)
                                    logger.info(f"✅ Watchdog: 已成功替换坏死连接 (Bound: {bind_ip})")
                                else:
                                    logger.error(f"❌ Watchdog: 替换连接失败，池容量降低")
                            finally:
                                current_bind_ip.reset(token)
                
            except Exception as e:
                logger.error(f"⚠️ Watchdog Loop Error: {e}")
            
            # 每 60 秒轮询一次
            await asyncio.sleep(60)

    async def _check_client_health(self, client: Quotes) -> bool:
        """执行轻量级健康检查，返回是否合格"""
        loop = asyncio.get_event_loop()
        start_t = asyncio.get_running_loop().time()
        try:
            # 使用 get_security_count 作为心跳负载
            count = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: client.client.get_security_count(0)),
                timeout=2.0 # 2秒超时即视为不健康（可能被限流或网络抖动）
            )
            elapsed = (asyncio.get_running_loop().time() - start_t) * 1000
            
            if count and count > 0:
                if elapsed > 1000:
                    logger.warning(f"🐢 Watchdog: 节点响应缓慢 ({elapsed:.0f}ms)")
                    # 响应时间超过 1s 的节点虽然能用，但建议后续替换（目前仍判为 True 可视需求调整）
                return True
            return False
        except Exception:
            return False

    async def acquire(self) -> Quotes:
        """从池中获取一个独占客户端"""
        if not self._initialized:
            await self.initialize()
            
        return await self.queue.get()

    async def release(self, client: Quotes):
        """归还客户端到池中"""
        await self.queue.put(client)

    async def close(self):
        async with self._lock:
            if self._watchdog_task:
                self._watchdog_task.cancel()
                try: await self._watchdog_task
                except asyncio.CancelledError: pass
                
            self._initialized = False
            self.queue = asyncio.Queue() # Reset
            
            # 关闭所有活跃连接
            for client in self._all_clients:
                try: client.client.close()
                except: pass
            self._all_clients = []
            
            logger.info("TDX Pool Closed")

    async def add_client(self, server: Tuple[str, int], bind_ip: Optional[str] = None) -> bool:
        """动态增加一个连接到池中 (热扩容)"""
        # 自动轮询选择绑定 IP
        if not bind_ip and self.local_ips:
            bind_ip = self.local_ips[random.randint(0, len(self.local_ips)-1)]
            
        token = current_bind_ip.set(bind_ip)
        try:
            loop = asyncio.get_event_loop()
            client = await loop.run_in_executor(
                None, lambda: RobustQuotes(server=server, timeout=10)
            )
            
            async with self._lock:
                self._all_clients.append(client)
                self.queue.put_nowait(client)
                self.size += 1
                
            logger.info(f"➕ 已动态扩容连接: {server[0]}:{server[1]} (Bound: {bind_ip}) | Current Size: {self.size}")
            return True
        except Exception as e:
            logger.error(f"❌ 动态扩容失败: {server[0]}:{server[1]} -> {e}")
            return False
        finally:
            current_bind_ip.reset(token)

    async def remove_client(self, client: Quotes):
        """从池中永久移除一个客户端"""
        async with self._lock:
            if client in self._all_clients:
                self._all_clients.remove(client)
                self.size -= 1
                try:
                    client.close()
                except:
                    pass
                logger.info(f"➖ 已移除连接，当前池容量: {self.size}")

    def update_targets(self, servers: List[Tuple[str, int]]):
        """动态更新候选服务器列表"""
        self.target_servers = servers
        self.target_server_strategy = 'list'
        logger.info(f"🎯 已更新候选服务器列表，总量: {len(servers)}")

    def get_status(self) -> dict:
        return {
            "pool_size": self.size,
            "available": self.queue.qsize(),
            "initialized": self._initialized,
            "local_ips": self.local_ips,
            "targets_count": len(self.target_servers),
            "strategy": self.target_server_strategy
        }

    def _load_ranked_nodes(self) -> List[Tuple[str, int]]:
        """从持久化文件加载高评分节点"""
        ranked_file = os.path.join(os.path.dirname(__file__), "tdx_nodes_ranked.json")
        if os.path.exists(ranked_file):
            try:
                with open(ranked_file, 'r') as f:
                    data = json.load(f)
                    nodes = data.get("ranked_nodes", [])
                    if nodes:
                        return [(n['host'], n['port']) for n in nodes]
            except Exception as e:
                logger.error(f"Failed to load ranked nodes: {e}")
        return []

def get_pool_size() -> int:
    return int(os.getenv("TDX_POOL_SIZE", "3"))
