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

### BaoStock
```python
# 自动重连 + 重试
async def _ensure_connection(self):
    async with self.lock:
        if not self._is_connected():
            await self._reconnect()
```

### AkShare
```python
# DataFrame 校验
if df.empty or "code" not in df.columns:
    raise ValueError("数据格式异常")
```

### PyWencai
```python
# 3 次指数退避重试
MAX_RETRIES = 3
RETRY_DELAY = 5  # 秒

for attempt in range(MAX_RETRIES):
    try:
        return await wencai_client.query(q)
    except CaptchaError:
        await asyncio.sleep(RETRY_DELAY * (2 ** attempt))
```

## 频率限制

| 数据源 | 限制 | 处理方式 |
|--------|------|----------|
| BaoStock | 无明确限制 | 但建议控制并发 |
| AkShare | 部分接口有限制 | 添加适当延迟 |
| PyWencai | ~10 次/分钟 | 信号量 + 冷却期 |
