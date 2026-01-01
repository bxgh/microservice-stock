# Cloud-API vs Stock-Manager 架构定位对比

> **创建日期**: 2026-01-01  
> **目的**: 澄清两个BFF层服务的职责边界与协作关系

---

## 核心区别总结

| 维度 | Cloud-API (02b) | Stock-Manager (02e) |
|:---|:---|:---|
| **定位** | **业务BFF** - 面向用户业务 | **管理BFF** - 面向系统运维 |
| **主要用户** | 前端用户 (策略、回测) | 前端开发者 + 运维人员 |
| **核心职责** | JWT鉴权、任务队列、数据聚合 | 元数据管理、质量审计、调度监控 |
| **端口** | 8000 | 8004 |
| **状态** | 规划中（未实现） | ✅ 已实现并部署 |

---

## 1. Cloud-API (业务聚合层)

### 1.1 核心职责
```
用户业务流 → Cloud-API → 后端微服务
```

**职责清单**:
1. ✅ **JWT 身份鉴权** - 验证用户身份和权限
2. ✅ **回测任务分发** - 接收策略，写入 Redis 队列
3. ✅ **股票数据查询** - 聚合 BaoStock/AkShare 数据
4. ✅ **用户策略管理** - CRUD 用户自定义策略
5. ✅ **历史查询** - 查询用户的回测历史

### 1.2 典型接口
```typescript
// 业务类接口
POST   /api/v1/backtest/submit       // 提交回测任务
GET    /api/v1/backtest/{id}/status  // 查询任务状态
GET    /api/v1/stocks/{code}/kline   // 获取K线数据
POST   /api/v1/strategies             // 创建策略
GET    /api/v1/user/history           // 用户历史
```

### 1.3 技术特点
- ✅ JWT 鉴权中间件
- ✅ Redis 任务队列
- ✅ 跨服务数据聚合
- ✅ 用户权限控制

---

## 2. Stock-Manager (系统管理层)

### 2.1 核心职责
```
系统监控/审计 → Stock-Manager → 后端微服务
```

**职责清单**:
1. ✅ **元数据管理** - 交易日历、标的基线
2. ✅ **质量审计** - 周度数据完整性报告
3. ✅ **调度监控** - 跨容器任务聚合与控制
4. ✅ **时效性监控** - 数据新鲜度检测
5. ✅ **系统健康** - 聚合所有服务状态

### 2.2 典型接口
```typescript
// 管理类接口
GET    /api/v1/metadata/calendar/tradingDays  // 交易日历
GET    /api/v1/metadata/baseline/current      // 标的基线
GET    /api/v1/audit/weekly                   // 周度审计
GET    /api/v1/ops/freshness                  // 时效性检测
GET    /api/v1/scheduler/jobs                 // 调度任务
POST   /api/v1/scheduler/jobs/{id}/pause      // 控制任务
```

### 2.3 技术特点
- ✅ 无鉴权（内部管理接口）
- ✅ 跨容器 HTTP 调用聚合
- ✅ 直连 MySQL 读取元数据
- ✅ 系统级监控与统计

---

## 3. 职责边界划分

### 按用户角色划分

| 用户角色 | 使用服务 | 典型场景 |
|:---|:---|:---|
| **普通用户** | Cloud-API | 查看股票、提交回测、管理策略 |
| **前端开发者** | Stock-Manager | 获取日历、审计数据、监控系统 |
| **运维人员** | Stock-Manager | 查看任务状态、触发修复、健康检查 |
| **管理员** | 两者都用 | 全功能访问 |

### 按数据性质划分

| 数据类型 | 负责服务 | 示例 |
|:---|:---|:---|
| **业务数据** | Cloud-API | 股票K线、财务指标、回测结果 |
| **元数据** | Stock-Manager | 交易日历、标的列表、基线数据 |
| **监控数据** | Stock-Manager | 任务状态、数据完整性、系统健康 |

---

## 4. 协作关系

### 4.1 独立运行
```
┌─────────────┐         ┌─────────────┐
│  Cloud-API  │         │Stock-Manager│
│   (8000)    │         │   (8004)    │
└──────┬──────┘         └──────┬──────┘
       │                       │
       ├───────────┬───────────┤
       ▼           ▼           ▼
   ┌────────┐  ┌────────┐  ┌────────┐
   │baostock│  │akshare │  │pywencai│
   └────────┘  └────────┘  └────────┘
```

- 两者**并行部署**，互不依赖
- 都可以直接调用底层数据服务

### 4.2 推荐部署
```
前端用户界面
    ▼
┌─────────────────┐
│   Nginx 网关     │
│   (80/443)      │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
Cloud-API  Stock-Manager
(业务流)    (管理流)
```

---

## 5. 当前状态与建议

### 5.1 现状
| 服务 | 实现状态 | 部署状态 |
|:---|:---:|:---:|
| Cloud-API | ❌ 仅规划 | - |
| Stock-Manager | ✅ 已实现 | ✅ Running |

### 5.2 建议方案

#### 方案A: 保持双层架构（推荐）⭐
```
优势:
- 职责清晰，业务/管理分离
- Stock-Manager 已验证可用
- 未来扩展性好

实施:
1. 继续完善 Stock-Manager
2. 后续实现 Cloud-API（用户鉴权后）
3. Nginx 网关统一路由
```

#### 方案B: 合并为单一BFF
```
优势:
- 减少容器数量
- 统一维护

劣势:
- 职责混杂
- 鉴权与管理接口混在一起
- 不推荐 ❌
```

### 5.3 推荐实施路径

**阶段1: 当前（已完成）**
```bash
✅ Stock-Manager 提供管理接口
✅ 前端可直接调用系统监控类API
```

**阶段2: 用户鉴权后**
```bash
⏳ 实现 Cloud-API
⏳ 添加 JWT 中间件
⏳ 实现回测任务队列
```

**阶段3: 生产就绪**
```bash
⏳ Nginx 网关统一入口
⏳ SSL 证书配置
⏳ 限流与安全加固
```

---

## 6. 前端接入指导

### 开发阶段（当前）
```typescript
// 直接使用 Stock-Manager
const API_BASE_URL = 'http://124.221.80.250:8004/api/v1';

// 无需鉴权，直接调用
const baseline = await fetch(`${API_BASE_URL}/metadata/baseline/current`);
```

### 生产阶段（未来）
```typescript
// 根据接口类型选择服务
const config = {
  cloudAPI: 'https://api.domain.com/v1',      // 业务接口
  managerAPI: 'https://api.domain.com/mgmt'   // 管理接口
};

// 业务接口需要 JWT
const backtest = await fetch(`${config.cloudAPI}/backtest/submit`, {
  headers: { 'Authorization': `Bearer ${token}` }
});

// 管理接口无需鉴权
const freshness = await fetch(`${config.managerAPI}/ops/freshness`);
```

---

## 7. 总结

### 核心差异
- **Cloud-API**: 面向**用户业务**的 BFF，需要鉴权，处理回测、策略等
- **Stock-Manager**: 面向**系统管理**的 BFF，无鉴权，提供监控、审计

### 关系定位
- ✅ **互补关系**，而非竞争关系
- ✅ 分别服务于不同的用户群体
- ✅ 可以并存，各司其职

### 推荐做法
1. ✅ 当前阶段：使用 Stock-Manager 即可满足管理需求
2. ⏳ 未来扩展：实现 Cloud-API 处理用户业务逻辑
3. ⭐ 长期规划：双层 BFF 架构，职责清晰

---

*文档版本: v1.0*  
*最后更新: 2026-01-01*
