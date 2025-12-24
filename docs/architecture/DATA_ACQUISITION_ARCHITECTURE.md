# Get-StockData 数据获取架构与开发指南

**版本**: 2.0 (EPIC-008 混合架构)  
**更新日期**: 2025-12-21  
**适用范围**: 新数据源集成、数据服务开发

---

## 📐 最新架构概览

### 三层架构

```
┌─────────────────────────────────────────────────────────┐
│                   应用层 (API Routes)                     │
│  /api/v1/quotes  /api/v1/finance  /api/v1/valuation    │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              数据服务层 (Data Services)                   │
│  QuotesService  FinancialService  ValuationService      │
│  - 业务逻辑封装                                           │
│  - 缓存管理                                              │
│  - 数据聚合                                              │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│            数据源层 (Data Providers)                      │
│  ┌──────────────┐  ┌──────────────┐                     │
│  │  本地源      │  │  云端源      │                     │
│  │  Mootdx      │  │  AkShare API │                     │
│  │  (TCP直连)   │  │  Baostock    │                     │
│  └──────────────┘  └──────────────┘                     │
│         ▲                  ▲                             │
│         │                  │                             │
│    Host Network    Squid Proxy (3128)                   │
└─────────────────────────────────────────────────────────┘
```

---

## 🏗️ 核心组件详解

### 1. 数据源层 (Provider Pattern)

#### 基类: `DataProvider`
**位置**: `src/data_sources/base.py`

```python
class DataProvider(ABC):
    """数据提供者抽象基类"""
    
    @abstractmethod
    async def fetch(self, data_type: DataType, **kwargs) -> DataResult:
        """获取数据的统一接口"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass
```

#### 已实现的 Provider

| Provider | 数据源 | 网络模式 | 用途 |
|----------|--------|----------|------|
| **MootdxProvider** | 通达信服务器 | TCP 直连 (Host) | 实时行情、分笔数据 |
| **AkshareProvider** | 云端 AkShare API | HTTP + Proxy | 榜单、财务、估值 |
| **BaostockProvider** | 云端 Baostock API | HTTP + Proxy | 历史K线、财务数据 |
| **EasyquotationProvider** | 新浪/腾讯 | HTTP | 实时行情备选 |
| **PywencaiProvider** | 云端问财 API | HTTP + Proxy | 板块、选股 |

---

### 2. 数据服务层 (Service Pattern)

#### 核心服务

**位置**: `src/data_services/`

| 服务 | 功能 | 依赖 Provider |
|------|------|---------------|
| **QuotesService** | 实时行情 | Mootdx, Easyquotation |
| **FinancialService** | 财务报表 | AkShare, Baostock |
| **ValuationService** | 估值数据 | AkShare |
| **IndustryService** | 行业数据 | AkShare, Pywencai |
| **HistoryService** | 历史K线 | Baostock, Mootdx |

**服务特性**:
- 统一的缓存管理
- 数据源降级机制
- 时段感知策略
- 并发安全保护

---

### 3. API 路由层

**位置**: `src/api/`

**职责**:
- HTTP 请求处理
- 参数验证
- 响应格式化
- 错误处理

---

## 🔄 数据流转流程

### 典型请求流程

```
1. API 请求
   ↓
   GET /api/v1/finance/indicators/600519
   
2. 路由层 (finance_routes.py)
   ↓
   - 参数验证
   - 获取 FinancialService 实例
   
3. 服务层 (FinancialService)
   ↓
   - 检查缓存
   - 调用 Provider
   - 数据聚合
   - 更新缓存
   
4. 数据源层 (AkshareProvider)
   ↓
   - HTTP 请求 (通过代理)
   - 数据解析
   - 返回 DataResult
   
5. 响应返回
   ↓
   JSON 格式数据
```

---

## 🌐 混合架构配置

### 网络配置 (EPIC-008)

```yaml
# docker-compose.dev.yml
services:
  get-stockdata:
    network_mode: host  # 必须！用于 Mootdx TCP 连接
    environment:
      # 云端代理 (统一网关)
      PROXY_URL: "http://192.168.151.18:3128"
      
      # 云端 API 地址
      AKSHARE_API_URL: "http://124.221.80.250:8003"
      STOCK_DICT_API_URL: "http://124.221.80.250:8000"
      BAOSTOCK_API_URL: "http://124.221.80.250:8001"
      
      # 禁用 proxychains (使用 aiohttp 原生代理)
      ENABLE_PROXY_CHAINS: "false"
```

### 代理使用规则

| 数据源 | 代理 | 说明 |
|--------|------|------|
| Mootdx (TCP) | ❌ 不使用 | 直连通达信服务器 |
| 云端 API | ✅ 使用 3128 | 所有 HTTP 云端请求 |
| 本地 AkShare | ⚠️ 可选 | 访问国外数据源时需要 |

---

## 📝 新增数据源开发指南

### Step 1: 创建 Provider 类

**文件**: `src/data_sources/providers/your_provider.py`

```python
# -*- coding: utf-8 -*-
"""
Your Provider 数据提供者
"""
import logging
from typing import Dict, Optional
import aiohttp

from .base import DataProvider, DataResult, DataType

logger = logging.getLogger(__name__)


class YourProvider(DataProvider):
    """Your 数据提供者"""
    
    def __init__(
        self,
        priority: Optional[Dict[DataType, int]] = None,
        api_url: Optional[str] = None,
        proxy_url: Optional[str] = None
    ):
        """初始化
        
        Args:
            priority: 数据类型优先级
            api_url: API 地址
            proxy_url: 代理地址 (如需要)
        """
        self._api_url = api_url or "http://your-api.com"
        self._proxy = proxy_url
        self._session: Optional[aiohttp.ClientSession] = None
        self._priority = priority or {}
        
    @property
    def name(self) -> str:
        return "your_provider"
    
    @property
    def capabilities(self) -> list[DataType]:
        """支持的数据类型"""
        return [
            DataType.FINANCE,  # 财务数据
            DataType.VALUATION,  # 估值数据
        ]
    
    @property
    def priority_map(self) -> Dict[DataType, int]:
        """优先级映射"""
        return {
            DataType.FINANCE: self._priority.get(DataType.FINANCE, 2),
            DataType.VALUATION: self._priority.get(DataType.VALUATION, 2),
        }
    
    async def initialize(self):
        """初始化 HTTP 会话"""
        if not self._session:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
            logger.info(f"{self.name} initialized")
    
    async def close(self):
        """关闭会话"""
        if self._session:
            await self._session.close()
            self._session = None
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            async with self._session.get(
                f"{self._api_url}/health",
                proxy=self._proxy
            ) as resp:
                return resp.status == 200
        except Exception as e:
            logger.warning(f"{self.name} health check failed: {e}")
            return False
    
    async def fetch(self, data_type: DataType, **kwargs) -> DataResult:
        """获取数据"""
        if data_type == DataType.FINANCE:
            return await self._fetch_finance(**kwargs)
        elif data_type == DataType.VALUATION:
            return await self._fetch_valuation(**kwargs)
        else:
            return DataResult(
                success=False,
                error=f"Unsupported data type: {data_type}"
            )
    
    async def _fetch_finance(self, symbol: str = "", **kwargs) -> DataResult:
        """获取财务数据"""
        try:
            async with self._session.get(
                f"{self._api_url}/finance/{symbol}",
                proxy=self._proxy
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return DataResult(
                        success=True,
                        data=data,
                        source=self.name
                    )
                else:
                    return DataResult(
                        success=False,
                        error=f"HTTP {resp.status}"
                    )
        except Exception as e:
            logger.error(f"Fetch finance failed: {e}")
            return DataResult(success=False, error=str(e))
    
    async def _fetch_valuation(self, symbol: str = "", **kwargs) -> DataResult:
        """获取估值数据"""
        # 类似实现
        pass
```

---

### Step 2: 注册 Provider 到工厂

**文件**: `src/data_sources/factory.py`

```python
from .providers.your_provider import YourProvider

class DataSourceFactory:
    @staticmethod
    async def create_provider(provider_type: str, **kwargs) -> DataProvider:
        """创建数据提供者"""
        providers = {
            "mootdx": MootdxProvider,
            "akshare": AkshareProvider,
            "baostock": BaostockProvider,
            "your_provider": YourProvider,  # 添加这行
        }
        
        provider_class = providers.get(provider_type.lower())
        if not provider_class:
            raise ValueError(f"Unknown provider: {provider_type}")
        
        provider = provider_class(**kwargs)
        await provider.initialize()
        return provider
```

---

### Step 3: 创建或扩展 Service

**选项 A: 扩展现有 Service**

```python
# src/data_services/financial_service.py

class FinancialService:
    def __init__(self, ...):
        # 添加新的 provider
        self.your_provider = YourProvider(
            api_url=os.getenv("YOUR_API_URL"),
            proxy_url=os.getenv("PROXY_URL")
        )
    
    async def get_financial_indicators(self, code: str):
        """获取财务指标"""
        # 尝试主数据源
        try:
            data = await self.akshare_provider.fetch(
                DataType.FINANCE, 
                symbol=code
            )
            if data.success:
                return data.data
        except Exception as e:
            logger.warning(f"Primary source failed: {e}")
        
        # 降级到新数据源
        try:
            data = await self.your_provider.fetch(
                DataType.FINANCE,
                symbol=code
            )
            if data.success:
                return data.data
        except Exception as e:
            logger.error(f"Fallback source failed: {e}")
        
        return None
```

**选项 B: 创建新 Service**

```python
# src/data_services/your_service.py

class YourService:
    """Your 数据服务"""
    
    def __init__(self, cache_manager=None):
        self.provider = YourProvider(...)
        self.cache = cache_manager
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        await self.provider.initialize()
    
    async def close(self):
        await self.provider.close()
    
    async def get_data(self, code: str):
        """获取数据"""
        # 1. 检查缓存
        cache_key = f"your_data:{code}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        # 2. 获取数据
        result = await self.provider.fetch(
            DataType.FINANCE,
            symbol=code
        )
        
        if not result.success:
            raise Exception(result.error)
        
        # 3. 更新缓存
        await self.cache.set(cache_key, result.data, ttl=3600)
        
        return result.data
```

---

### Step 4: 添加 API 路由

**文件**: `src/api/your_routes.py`

```python
from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/v1/your", tags=["Your数据"])

def get_your_service(request: Request):
    """获取服务实例"""
    service = getattr(request.app.state, "your_service", None)
    if not service:
        raise HTTPException(503, "Service not initialized")
    return service

@router.get("/data/{stock_code}")
async def get_your_data(stock_code: str, request: Request):
    """获取 Your 数据"""
    service = get_your_service(request)
    data = await service.get_data(stock_code)
    
    if not data:
        raise HTTPException(404, f"No data for {stock_code}")
    
    return {"success": True, "data": data}
```

---

### Step 5: 注册到主应用

**文件**: `src/main.py`

```python
from api.your_routes import router as your_router
from data_services.your_service import YourService

# 创建服务实例
app.state.your_service = YourService(cache_manager=cache_manager)

# 注册路由
app.include_router(your_router)

# 生命周期管理
@app.on_event("startup")
async def startup():
    await app.state.your_service.initialize()

@app.on_event("shutdown")
async def shutdown():
    await app.state.your_service.close()
```

---

### Step 6: 配置环境变量

```bash
# .env
YOUR_API_URL=http://your-api.com
PROXY_URL=http://192.168.151.18:3128  # 如需代理
```

---

### Step 7: 编写测试

**文件**: `tests/test_your_service.py`

```python
import pytest
from data_services.your_service import YourService

@pytest.mark.asyncio
async def test_get_data():
    """测试数据获取"""
    service = YourService()
    await service.initialize()
    
    try:
        data = await service.get_data("600519")
        assert data is not None
        assert "revenue" in data  # 根据实际字段调整
    finally:
        await service.close()

@pytest.mark.asyncio
async def test_concurrent_access():
    """测试并发安全"""
    service = YourService()
    await service.initialize()
    
    try:
        tasks = [service.get_data("600519") for _ in range(10)]
        results = await asyncio.gather(*tasks)
        assert all(r is not None for r in results)
    finally:
        await service.close()
```

---

## ✅ 开发检查清单

### Provider 层
- [ ] 继承 `DataProvider` 基类
- [ ] 实现所有抽象方法
- [ ] 添加健康检查
- [ ] 配置代理支持 (如需要)
- [ ] 添加错误处理和重试
- [ ] 实现并发安全

### Service 层
- [ ] 实现缓存机制
- [ ] 添加数据源降级
- [ ] 使用 `asyncio.Lock` 保护共享状态
- [ ] 添加详细日志
- [ ] 实现资源清理 (`close` 方法)

### API 层
- [ ] 定义 Pydantic 模型
- [ ] 添加参数验证
- [ ] 实现错误处理
- [ ] 添加 API 文档字符串

### 测试
- [ ] 单元测试覆盖率 > 80%
- [ ] 并发测试
- [ ] 集成测试
- [ ] 性能测试

### 文档
- [ ] 更新 API 文档
- [ ] 更新架构文档
- [ ] 添加使用示例

---

## 🎯 最佳实践

### 1. 代理配置
```python
# 云端 API 必须使用代理
proxy = os.getenv("PROXY_URL", "http://192.168.151.18:3128")

# 本地 TCP 连接不使用代理
# Mootdx 直连，不设置 proxy 参数
```

### 2. 错误处理
```python
try:
    result = await provider.fetch(...)
    if not result.success:
        logger.warning(f"Fetch failed: {result.error}")
        # 尝试降级
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    # 返回错误或使用缓存
```

### 3. 缓存策略
```python
# 根据数据类型设置不同 TTL
cache_ttl = {
    "realtime": 5,      # 实时数据 5 秒
    "daily": 3600,      # 日线数据 1 小时
    "financial": 86400, # 财务数据 1 天
}
```

### 4. 并发安全
```python
class YourService:
    def __init__(self):
        self._lock = asyncio.Lock()
    
    async def get_data(self, code: str):
        async with self._lock:
            # 保护共享状态
            pass
```

---

## 📚 参考文档

- [EPIC-007 完成报告](file:///home/bxgh/microservice-stock/services/get-stockdata/docs/reports/epic007/epic007_completion_report.md)
- [EPIC-008 混合架构](file:///home/bxgh/microservice-stock/docs/epics/epic008-hybrid-architecture/EPIC-008-混合架构实施.md)
- [网络配置指南](file:///home/bxgh/microservice-stock/services/get-stockdata/docs/antigravity-net/00_Overview.md)
- [编码规范](file:///home/bxgh/microservice-stock/services/get-stockdata/docs/CODING_STANDARDS.md)

---

**文档版本**: 2.0  
**维护人**: AI 开发助手  
**最后更新**: 2025-12-21
