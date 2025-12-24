# EPIC-002 数据集成完成需求文档

**项目**: get-stockdata 服务  
**需求方**: quant-strategy 服务  
**优先级**: P0 (阻塞 quant-strategy 核心功能)  
**创建日期**: 2025-12-21  
**预计工期**: 2-3 天

---

## 📋 需求概述

当前 EPIC-002 相关 API 端点已实现，但返回空数据或 null 值。需要完成数据源集成，使 API 返回真实的财务和估值数据。

### 当前状态
- ✅ API 端点已实现 (6个)
- ✅ 数据模型已定义
- ❌ 数据源未正确集成
- ❌ 返回数据为空或 null

---

## 🎯 核心需求

### 需求 1: 财务指标数据集成 (P0)

**API**: `GET /api/v1/finance/indicators/{stock_code}`

**当前问题**: 返回 404，无数据

**需要返回的字段**:

#### 资产负债表
```json
{
  "total_assets": 1234.56,        // 总资产 (亿元)
  "net_assets": 567.89,           // 净资产 (亿元)
  "goodwill": 12.34,              // 商誉 (亿元)
  "monetary_funds": 234.56,       // 货币资金 (亿元)
  "interest_bearing_debt": 123.45,// 有息负债 (亿元)
  "accounts_receivable": 45.67,   // 应收账款 (亿元) - P1
  "inventory": 34.56,             // 存货 (亿元) - P1
  "accounts_payable": 23.45,      // 应付账款 (亿元) - P1
  "current_assets": 456.78,       // 流动资产 (亿元) - P2
  "current_liabilities": 234.56,  // 流动负债 (亿元) - P2
  "total_liabilities": 567.89     // 总负债 (亿元) - P2
}
```

#### 利润表
```json
{
  "revenue": 2345.67,             // 营业收入 (亿元)
  "operating_cost": 1234.56,      // 营业成本 (亿元) - P1
  "operating_profit": 456.78,     // 营业利润 (亿元) - P1
  "net_profit": 345.67,           // 净利润 (亿元)
  "gross_profit": 1111.11,        // 毛利润 (亿元) - P1
  "ebit": 500.00,                 // 息税前利润 (亿元) - P1
  "ebitda": 550.00                // EBITDA (亿元) - P2
}
```

#### 现金流量表
```json
{
  "operating_cash_flow": 234.56,  // 经营现金流 (亿元)
  "investing_cash_flow": -123.45, // 投资现金流 (亿元) - P2
  "financing_cash_flow": -45.67,  // 筹资现金流 (亿元) - P2
  "free_cash_flow": 189.01        // 自由现金流 (亿元) - P1
}
```

**数据源**: 
- 优先: 云端 AkShare API (124.221.80.250:8003)
- 备选: 新浪财经 API (需代理)

**验收标准**:
- [ ] API 返回 200 状态码
- [ ] 所有 P0 字段非 null
- [ ] 数据单位为亿元
- [ ] 数据时效性 < 1 个交易日

---

### 需求 2: 历史财务数据 (P0)

**API**: `GET /api/v1/finance/history/{stock_code}?periods=8&report_type=Q`

**当前问题**: 返回 404，无数据

**需要返回的数据**:
```json
{
  "stock_code": "600519",
  "periods": 8,
  "data": [
    {
      "report_date": "2024-09-30",
      "revenue": 2345.67,
      "net_profit": 345.67,
      "total_assets": 1234.56,
      "net_assets": 567.89,
      "operating_cash_flow": 234.56
      // ... 其他字段
    },
    // ... 最近 8 个季度
  ]
}
```

**验收标准**:
- [ ] 返回最近 8 个季度数据
- [ ] 数据按时间倒序排列
- [ ] 每期数据包含所有 P0 字段
- [ ] 支持季报 (Q) 和年报 (A) 查询

---

### 需求 3: 市场估值数据 (P0)

**API**: `GET /api/v1/market/valuation/{stock_code}`

**当前问题**: 返回结构正确，但所有字段为 null

**需要返回的字段**:
```json
{
  "stock_code": "600519",
  "report_date": "20251221",
  "total_market_cap": 2500.00,           // 总市值 (亿元)
  "circulating_market_cap": 2500.00,     // 流通市值 (亿元)
  "pe_ttm": 35.5,                        // 市盈率 TTM
  "pe_static": 34.2,                     // 静态市盈率
  "pb_ratio": 12.3,                      // 市净率
  "ps_ratio": 8.5,                       // 市销率 - P1
  "pcf_ratio": 25.0,                     // 市现率 - P1
  "dividend_yield_ttm": 1.2,             // 股息率 (%) - P1
  "total_shares": 125600.0,              // 总股本 (万股) - P1
  "circulating_shares": 125600.0         // 流通股本 (万股) - P1
}
```

**数据源**: 
- 优先: 云端 AkShare API
- 备选: 东方财富 API

**验收标准**:
- [ ] 所有 P0 字段非 null
- [ ] 数据实时性 < 5 分钟 (交易时段)
- [ ] 数据实时性 < 1 天 (非交易时段)

---

### 需求 4: 估值历史数据 (P0)

**API**: `GET /api/v1/market/valuation/{stock_code}/history?years=5&frequency=D`

**当前问题**: API 可能未实现或返回空数据

**需要返回的数据**:
```json
{
  "stock_code": "600519",
  "data": [
    {
      "date": "2024-12-21",
      "pe_ratio": 35.5,
      "pb_ratio": 12.3,
      "price": 1800.0
    }
    // ... 5 年历史数据
  ],
  "statistics": {
    "pe": {
      "mean": 32.5,
      "median": 30.2,
      "p25": 25.0,
      "p50": 30.2,
      "p75": 38.0,
      "p90": 45.0,
      "min": 18.0,
      "max": 60.0
    },
    "pb": { /* 同样结构 */ }
  }
}
```

**验收标准**:
- [ ] 返回 5 年历史数据
- [ ] 包含统计信息 (均值、分位数)
- [ ] 支持日/周/月频率

---

### 需求 5: 行业统计数据 (P1)

**API**: `GET /api/v1/finance/industry/{industry_code}/stats`

**当前问题**: 返回 404，无数据

**需要返回的数据**:
```json
{
  "industry_code": "801010",
  "industry_name": "农林牧渔",
  "report_date": "2024-09-30",
  "stats": {
    "roe": {
      "mean": 8.5,
      "median": 7.2,
      "p25": 5.0,
      "p75": 12.0,
      "p90": 15.0
    },
    "revenue_growth": { /* 同样结构 */ },
    "pe_ratio": { /* 同样结构 */ },
    "pb_ratio": { /* 同样结构 */ }
  },
  "sample_size": 156  // 行业内公司数量
}
```

**验收标准**:
- [ ] 支持申万行业分类
- [ ] 返回行业内统计分布
- [ ] 数据更新频率 < 1 月

---

### 需求 6: 公司基本信息增强 (P0)

**API**: `GET /api/v1/stocks/{stock_code}/info`

**需要补充的字段**:
```json
{
  "stock_code": "600519",
  "stock_name": "贵州茅台",
  "industry_code": "801010",        // 行业代码 (申万) - 新增
  "industry_name": "农林牧渔",      // 行业名称 - 新增
  "listing_date": "2001-08-27",     // 上市日期
  "exchange": "SH"
}
```

**验收标准**:
- [ ] 行业代码和名称非空
- [ ] 使用申万行业分类标准

---

## 🔧 技术实施要求

### 1. 数据源集成

#### 优先方案: 云端 AkShare API
```python
# 配置
AKSHARE_API_URL = "http://124.221.80.250:8003"
PROXY_URL = "http://192.168.151.18:3128"

# 使用 AkshareProvider
from data_sources.providers.akshare_provider import AkshareProvider

provider = AkshareProvider(
    api_url=AKSHARE_API_URL,
    proxy_url=PROXY_URL
)
```

#### 备选方案: 本地 AkShare
```python
import akshare as ak

# 需要配置代理
import os
os.environ['HTTP_PROXY'] = 'http://192.168.151.18:3128'
os.environ['HTTPS_PROXY'] = 'http://192.168.151.18:3128'
```

### 2. 错误处理

**要求**:
- 数据源失败时记录详细日志
- 实现降级机制 (主数据源 → 备用数据源 → 缓存)
- 返回明确的错误信息

**示例**:
```python
try:
    data = await self._fetch_from_primary_source(code)
except DataSourceError as e:
    logger.warning(f"Primary source failed: {e}, trying fallback")
    data = await self._fetch_from_fallback_source(code)
    
if not data:
    raise HTTPException(
        status_code=404,
        detail=f"No data available for {code} from any source"
    )
```

### 3. 缓存策略

**要求**:
- 财务数据: 缓存 1 天
- 估值数据: 缓存 5 分钟 (交易时段), 1 小时 (非交易时段)
- 行业统计: 缓存 1 周

### 4. 数据验证

**要求**:
- 验证数据类型和范围
- 检查必填字段
- 标记异常值

---

## 📅 实施计划

### Phase 1: 数据源集成 (1 天)
- [ ] 配置云端 AkShare API
- [ ] 测试数据源连通性
- [ ] 实现基础数据获取

### Phase 2: API 实现 (1 天)
- [ ] 实现财务指标 API
- [ ] 实现历史数据 API
- [ ] 实现估值数据 API

### Phase 3: 测试与优化 (0.5 天)
- [ ] 单元测试
- [ ] 集成测试
- [ ] 性能优化

### Phase 4: 文档更新 (0.5 天)
- [ ] 更新 API 文档
- [ ] 更新 EPIC-002 状态

---

## ✅ 验收标准

### 功能验收
- [ ] 所有 6 个 API 返回真实数据
- [ ] P0 字段完整性 100%
- [ ] P1 字段完整性 > 80%

### 性能验收
- [ ] API 响应时间 < 2s (p95)
- [ ] 缓存命中率 > 50%
- [ ] 错误率 < 1%

### 数据质量验收
- [ ] 数据准确性抽检通过
- [ ] 数据时效性符合要求
- [ ] 异常值 < 5%

---

## 📝 相关文档

- [EPIC-002 完整需求](file:///home/bxgh/microservice-stock/services/get-stockdata/docs/todo/EPIC_002_COMPLETE_DATA_REQUIREMENTS.md)
- [API 验证报告](file:///home/bxgh/.gemini/antigravity/brain/4054ca1a-632a-458f-bbf2-adb2383a79c9/epic002_api_verification.md)
- [服务完成计划](file:///home/bxgh/.gemini/antigravity/brain/4054ca1a-632a-458f-bbf2-adb2383a79c9/service_completion_plan.md)

---

**文档版本**: 1.0  
**创建人**: AI 开发助手  
**审批状态**: 待审批
