# 数据源特性指南

> **用途**: AI 开发时了解各数据源的特点与处理方式

## 数据源对比

| 数据源 | 协议 | 优势 | 限制 | 适用场景 |
|--------|------|------|------|----------|
| **BaoStock** | TCP | 历史完整、支持复权 | 长连接易断、需登录 | K 线、复权因子 |
| **AkShare** | HTTP | 接口丰富、覆盖广 | 字段结构易变 | 财务、估值、龙虎榜 |
| **PyWencai** | HTTP | 语义查询强大 | 频率限制 ~10次/分 | 智能选股 |

## 数据类型推荐

| 数据类型 | 首选数据源 | 端口 |
|----------|------------|------|
| 日 K 线 | BaoStock | 8001 |
| 分钟 K 线 | BaoStock | 8001 |
| 复权因子 | BaoStock | 8001 |
| 财务报表 | AkShare | 8003 |
| 估值指标 | AkShare | 8003 |
| 龙虎榜 | AkShare | 8003 |
| 智能选股 | PyWencai | 8002 |

## 异常处理规范

### BaoStock (TCP 长连接管理)
```python
# 自动重连 + 重试机制
class BaostockClient:
    async def _ensure_connection(self):
        async with self.lock:
            # 检查连接是否存活
            if not self.bs.query_history_k_data_plus("sh.600000", ...).error_code == "0":
                logger.warning("BaoStock连接断开，尝试重连...")
                self.bs.logout()
                login_msg = self.bs.login()
                if login_msg.error_code != "0":
                    raise ConnectionError(f"重连失败: {login_msg.error_msg}")
```

### AkShare (DataFrame 校验)
```python
# 数据完整性防御
if df is None or df.empty:
    logger.warning(f"AkShare返回空数据: code={code}")
    return None

if "总市值" not in df.columns:
    logger.error(f"AkShare字段变更，缺少'总市值': columns={df.columns}")
    raise ValueError("数据格式不符合预期")
```

## 频率限制实现

### PyWencai (Token Bucket)
```python
import asyncio
from asyncio import Semaphore

class RateLimiter:
    """问财限制: ~10次/分钟"""
    def __init__(self, limit=10, period=60):
        self.sem = Semaphore(limit)
        self.period = period

    async def acquire(self):
        await self.sem.acquire()
        # 启动后台任务在周期后释放令牌
        asyncio.create_task(self._release())

    async def _release(self):
        await asyncio.sleep(self.period)
        self.sem.release()

# 使用示例
limiter = RateLimiter()
async def query(q):
    await limiter.acquire()
    return await wencai.get(q)
```

---
> **最后更新**: 2026-01-07
