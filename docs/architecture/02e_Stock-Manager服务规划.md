# 02e. Stock-Manager-API 服务规划

> **状态**: 规划中 (Planning)  
> **版本**: v1.0  
> **更新日期**: 2026-01-01

---

## 1. 服务定位

| 属性 | 说明 |
|:---|:---|
| **服务名称** | `stock-manager-api` |
| **端口** | `8004` |
| **容器名** | `stock-manager` |
| **定位** | 数据溯源管理系统的**业务中台**，负责元数据管理、质量审计、跨容器调度编排 |
| **核心价值** | 将"系统管理"逻辑从"数据抓取"逻辑中剥离，实现职责单一化 |

---

## 2. 架构背景

### 2.1 现状问题

当前 `baostock-api` 容器承担了过多职责：

| 职责类型 | 具体功能 | 问题 |
|:---|:---|:---|
| **数据源适配** | 封装 BaoStock SDK 进行数据抓取 | ✅ 合理 |
| **基础元数据** | 管理交易日历、标的基线 | ⚠️ 应剥离 |
| **系统审计** | 跨容器聚合调度任务、生成审计报告 | ⚠️ 应剥离 |
| **调度中心** | 充当"主控"角色指挥其他容器 | ⚠️ 应剥离 |

**存在的风险**：
1. **资源瓶颈**：128MB 内存限制下，同时跑数据同步、跨容器调度和审计逻辑容易 OOM
2. **耦合度高**：未来增加新数据源时，审计逻辑仍需挂在 `baostock` 下
3. **容错性差**：BaoStock 连接器崩溃会导致整个"溯源管理系统"不可用

### 2.2 目标架构

```
┌─────────────────┐
│   Frontend      │
│  (Taro H5 App)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ stock-manager   │◄──────────────────────┐
│   (8004)        │                       │
│ [管理中枢]       │                       │
└────────┬────────┘                       │
         │ HTTP 调用                       │
    ┌────┴────┬────────────┐              │
    ▼         ▼            ▼              │
┌───────┐ ┌───────┐ ┌──────────┐          │
│baostock│ │akshare│ │pywencai  │          │
│ (8001) │ │(8003) │ │ (8002)   │          │
│[抓取器]│ │[抓取器]│ │[抓取器]  │          │
└───┬───┘ └───┬───┘ └────┬─────┘          │
    │         │          │                │
    └─────────┴──────────┴────────────────┘
              │
              ▼
        ┌───────────┐
        │  MySQL    │
        │(腾讯云CDB) │
        └───────────┘
```

---

## 3. 职责边界划分

| 职责 | Stock-Manager (新) | BaoStock-API (瘦身后) |
|:---|:---|:---|
| **交易日历** | ✅ 管理 | - |
| **标的基线** | ✅ 管理 | - |
| **周度审计** | ✅ 生成报告 | - |
| **时效性监控** | ✅ 检测 Lag | - |
| **跨容器调度** | ✅ 指挥中心 | ❌ 仅接收指令 |
| **数据补偿** | ✅ 决策层 | ⚙️ 执行层 |
| **K线同步** | - | ✅ 执行 |
| **复权因子** | - | ✅ 执行 |
| **BaoStock SDK** | - | ✅ 封装 |

---

## 4. API 规划

### 4.1 元数据管理 (`/api/v1/metadata`)

| 接口 | 方法 | 说明 |
|:---|:---|:---|
| `/metadata/calendar/tradingDays` | GET | 获取交易日历 |
| `/metadata/baseline/current` | GET | 获取当前标的基线 |
| `/metadata/baseline/history` | GET | 基线变更历史 (未来扩展) |

### 4.2 质量审计 (`/api/v1/audit`)

| 接口 | 方法 | 说明 |
|:---|:---|:---|
| `/audit/weekly` | GET | 周度审计报告 |
| `/audit/daily/{date}` | GET | 单日审计详情 |
| `/audit/reports` | GET | 历史审计记录列表 |
| `/audit/reports/{id}` | GET | 单个报告详情 |

### 4.3 调度编排 (`/api/v1/scheduler`)

| 接口 | 方法 | 说明 |
|:---|:---|:---|
| `/scheduler/jobs` | GET | 跨容器任务列表 (聚合) |
| `/scheduler/jobs/{id}/{action}` | POST | 控制任务 (转发) |
| `/scheduler/jobs/{id}/logs` | GET | 任务日志 (代理) |
| `/scheduler/executions` | GET | 执行历史 (聚合) |

### 4.4 数据运维 (`/api/v1/ops`)

| 接口 | 方法 | 说明 |
|:---|:---|:---|
| `/ops/freshness` | GET | 数据时效性检测 |
| `/ops/remediate` | POST | 触发数据补偿 |
| `/ops/reset` | POST | 重置同步进度 (危险) |

### 4.5 系统健康 (`/api/v1/system`)

| 接口 | 方法 | 说明 |
|:---|:---|:---|
| `/system/health` | GET | 聚合所有容器健康状态 |
| `/system/stats` | GET | 系统统计 (标的数、记录数等) |

---

## 5. 技术栈

| 组件 | 选型 | 说明 |
|:---|:---|:---|
| **框架** | FastAPI | 保持与现有服务一致 |
| **数据库** | 腾讯云 MySQL | 共享现有库，直连 |
| **HTTP 客户端** | httpx | 调用其他容器 API |
| **日志** | python-json-logger | 统一 JSON 格式 |
| **配置** | pydantic-settings | 环境变量管理 |
| **基础镜像** | python:3.12-slim | 符合项目规范 |

---

## 6. 目录结构

```
stock-manager-api/
├── Dockerfile
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   ├── config.py               # 配置管理
│   ├── api/
│   │   ├── __init__.py
│   │   ├── metadata.py         # 元数据接口
│   │   ├── audit.py            # 审计接口
│   │   ├── scheduler.py        # 调度编排接口
│   │   ├── ops.py              # 运维接口
│   │   └── system.py           # 系统健康接口
│   ├── services/
│   │   ├── __init__.py
│   │   ├── calendar_service.py # 交易日历服务
│   │   ├── baseline_service.py # 基线服务
│   │   ├── audit_service.py    # 审计服务
│   │   ├── scheduler_proxy.py  # 调度代理服务
│   │   └── ops_service.py      # 运维服务
│   └── utils/
│       ├── database.py         # 数据库连接池
│       ├── logger.py           # 日志工具
│       └── http_client.py      # 容器间 HTTP 客户端
```

---

## 7. Docker 部署配置

```yaml
# docker-compose.yml 新增配置
stock-manager:
  build: ./stock-manager-api
  image: stock-manager-api:latest
  container_name: stock-manager
  restart: unless-stopped
  ports:
    - "8004:8000"
  environment:
    - TZ=Asia/Shanghai
    - LOG_LEVEL=${LOG_LEVEL:-INFO}
    - BAOSTOCK_API_URL=http://baostock-api:8000
    - AKSHARE_API_URL=http://akshare-api:8000
    - PYWENCAI_API_URL=http://pywencai-api:8000
  env_file:
    - .env
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 60s
    timeout: 10s
    retries: 3
    start_period: 15s
  depends_on:
    - baostock-api
    - akshare-api
  deploy:
    resources:
      limits:
        memory: 128M
        cpus: '0.5'
      reservations:
        memory: 50M
        cpus: '0.1'
  mem_limit: 128m
  cpus: 0.5
  networks:
    - stock-network
```

---

## 8. 迁移计划

| 阶段 | 任务 | 风险 | 预计耗时 |
|:---|:---|:---:|:---:|
| **Phase 1** | 创建 `stock-manager-api` 骨架，实现元数据接口 | 低 | 2h |
| **Phase 2** | 迁移审计逻辑 (`audit/weekly`, `freshness`) | 低 | 2h |
| **Phase 3** | 迁移调度编排逻辑 (`scheduler/jobs` 聚合) | 中 | 3h |
| **Phase 4** | 从 `baostock-api` 移除冗余代码 | 中 | 1h |
| **Phase 5** | 更新前端调用路径 | 中 | 1h |
| **Phase 6** | 集成测试与文档更新 | 低 | 2h |

**总预计耗时**: 约 11 小时

---

## 9. 预期收益

| 维度 | 收益 |
|:---|:---|
| **职责清晰** | 抓取层专注抓取，管理层专注审计和调度 |
| **资源隔离** | 管理类接口独享资源，避免影响数据同步性能 |
| **扩展性** | 未来增加新数据源，只需在 Manager 里配置即可 |
| **容错增强** | 即使某个抓取器挂掉，审计和日历接口仍可用 |
| **前端友好** | 统一入口，减少前端对接多个容器的复杂度 |

---

## 10. 风险与应对

| 风险 | 应对措施 |
|:---|:---|
| 迁移期间接口不可用 | 采用渐进式迁移，新旧接口并行运行 |
| 跨容器调用延迟增加 | 使用 httpx 连接池，设置合理超时 |
| 数据库连接数增加 | 共享现有连接池配置，限制 maxsize |

---

*文档版本：v1.0*  
*创建日期：2026-01-01*
