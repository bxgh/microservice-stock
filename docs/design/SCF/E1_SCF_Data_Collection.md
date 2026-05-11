# Epic: E1 - SCF 原生数据采集系统 (SCF-Native Collector)

> **Status**: Designing  
> **Source of Truth**: docs/design/SCF/E1_SCF_Data_Collection.md

## 1. 业务背景
为了实现极致的零成本运维和高可用性，将原有的 Docker 微服务架构迁移至腾讯云 SCF。本 Epic 专注于核心 K 线数据的采集、清洗与入库。

## 2. E1-S1: Data-Hub 核心采集适配器

### 2.1 任务描述
构建一个高度抽象的 `Data-Hub` 云函数，能够根据输入参数选择最合适的数据源（Tushare/AkShare/mootdx）获取股票日线行情，并统一输出为标准格式。

### 2.2 验收标准 (AC)
- **AC1 (Given-When-Then)**:
  - **Given**: 输入 `ts_code="000001.SZ"`, `trade_date="2026-05-08"`, `source="akshare"`
  - **When**: 调用 `Data-Hub` 采集函数
  - **Then**: 应该从 AkShare 抓取数据并返回标准的 JSON 结构，包含 `hloc`, `vol`, `amount` 等字段。
- **AC2 (Fault Tolerance)**:
  - **Given**: 指定的数据源失效（如 Tushare 积分不足）
  - **When**: 设置了自动切换模式
  - **Then**: 应该自动回退到备用数据源（AkShare/mootdx）进行尝试。

## 3. E1-S2: 任务审计与数据库就绪探测 (MySQL 5.7)

### 3.1 任务描述
实现数据库入库逻辑，包含幂等性校验、任务流水审计（`pipeline_run`）以及数据就绪探测（`data_readiness`）。

### 3.2 验收标准 (AC)
- **AC1 (Idempotency)**:
  - **Given**: 同一天的同一只股票数据已存在于 `stock_kline_daily`
  - **When**: 再次执行采集入库
  - **Then**: 数据库应执行 `ON DUPLICATE KEY UPDATE` 或跳过，确保不产生重复记录。
- **AC2 (Audit Trace)**:
  - **Given**: 采集成功
  - **Then**: `pipeline_run` 表中必须产生一条状态为 `success` 的记录，并关联 `request_id`。

## 4. E1-S3: SCF 云端部署与 VPC 通信

### 4.1 任务描述
配置 `serverless.yml`，实现 SCF 与现有 MySQL 所在的 VPC 环境打通。

### 4.2 验收标准 (AC)
- **AC1 (Network Connectivity)**:
  - **When**: 在 SCF 运行环境中执行 `mysql_ping`
  - **Then**: 应能通过内网 IP 连通现有 MySQL 实例。
- **AC2 (Resource Efficiency)**:
  - **When**: 部署完成
  - **Then**: 函数内存占用应控制在 256MB 以内。

---
*Created by Antigravity AI - 2026-05-11*
