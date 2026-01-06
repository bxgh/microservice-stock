# 项目架构上下文

> **用途**: 为 AI 开发助手提供项目架构的快速理解

## 1. 系统架构

本系统采用 **"IO 上云，计算下沉，存储分层"** 的设计哲学：

```
┌─────────────────────────────────────────────────────┐
│               腾讯云 (2C 4G 80G SSD)                  │
├─────────────────────────────────────────────────────┤
│  akshare-api:8003   baostock-api:8001               │
│  pywencai-api:8002  stock-manager:8004              │
│                        ↓                             │
│              MySQL (腾讯云 CDB 5.7)                  │
└─────────────────────────────────────────────────────┘
```

## 2. 微服务职责

| 服务 | 端口 | 职责 | 关键特性 |
|------|------|------|----------|
| `baostock-api` | 8001 | K线/复权因子同步、调度中枢 | APScheduler、断点续传 |
| `akshare-api` | 8003 | 财务/估值/龙虎榜 | HTTP 接口丰富 |
| `pywencai-api` | 8002 | 问财语义选股 | 频率限制 ~10次/分 |
| `stock-manager` | 8004 | 数据聚合中台 | 聚合调用下游服务 |

## 3. 目录结构

```
microservice-stock/
├── .agent/                 # AI 上下文与工作流
│   ├── context/           # 上下文文档 (你正在读的)
│   ├── rules/             # 规则配置
│   └── workflows/         # 工作流定义
├── akshare-api/           # AkShare 微服务
├── baostock-api/          # BaoStock 微服务 (调度中枢)
├── pywencai-api/          # PyWencai 微服务
├── stock-manager-api/     # 聚合中台
├── docs/                  # 项目文档
│   ├── architecture/      # 架构设计
│   ├── bugfix/           # 问题修复报告
│   └── guidelines/       # 开发规范
├── scripts/testing/       # 验证脚本
└── docker-compose.yml     # 容器编排
```

## 4. 技术栈

| 类别 | 选型 | 版本 |
|------|------|------|
| 语言 | Python | 3.12+ |
| 框架 | FastAPI + Pydantic v2 | 0.109+ |
| 容器 | Docker + python:3.12-slim | - |
| 数据库 | MySQL | 5.7 |
| 调度 | APScheduler | - |

## 5. 关键约束

- **内存限制**: 每个容器 ≤128MB
- **异步优先**: 所有 I/O 必须使用 async/await
- **时区**: 固定使用 Asia/Shanghai
- **日志**: JSON 格式，必须包含 request_id
