# SCF Collector: 生产环境部署与全链路对齐手册

## 1. 文档索引 (Documentation Index)

- **核心 PRD**: [PRD_SCF_COLLECTOR.md](PRD_SCF_COLLECTOR.md) (业务目标与数据契约)
- **实施 Epic (E400)**: [E400_SCF_Collector_Implementation.md](E400_SCF_Collector_Implementation.md) (当前执行计划)
- **审计报告 (E300)**: [audit/E300_Data_Ingestion_Verification.md](audit/E300_Data_Ingestion_Verification.md) (存量数据资产核查)
- **任务看板**: [todo-list-tables.md](todo-list-tables.md) (49 张表采集清单)

---

## 2. 系统角色与架构
`scf-collector` 是 A 股盘后分析系统的“数据前哨”，运行在腾讯云云函数 (SCF) 环境下。
- **职责**: 负责从 Tushare/AkShare 采集原始数据，同步元数据，并对齐业务表与审计元数据。
- **网络**: 必须绑定 VPC (`vpc-0qlg45u2`) 以直连内网 MySQL (`172.17.0.10`)，**并同时开启公网访问 (PublicNetConfig=ENABLE)** 以请求外部数据源。

### 2.1 Serverless Monorepo 架构 (2026-05-12 升级)
为支持多任务并发开发与部署，本项目采用 **Serverless Monorepo** 架构：
- `functions/`: 所有独立云函数的物理隔离区。
  - `meta_sync/`: 基础元数据同步函数 (`stock-scf-meta`)。
  - `daily_quotes/`: 日常行情收集函数 (`stock-serverless-collector`)。
- `shared/`: 全局共享业务组件库（DB 连接池、各类采集器基类），部署时会被自动打包注入每个函数。
- `.output/`: 本地自动打包生成的临时 Zip 文件存放点（被 git 忽略，保持根目录整洁）。

---

## 3. 核心技术复盘 (2026-05-11)

### 3.1 依赖与环境治理
- **动态路径插入**: 在 `index.py` 中强制扫描 `/opt/python`，解决了 Layer 依赖加载的顽疾。
- **只读系统绕行**: 针对 SCF 只读环境。
- **API 部署模式**: 切换为基于 Python SDK 的 `UpdateFunctionCode` 模式，确保大包上传的稳定性。

### 3.2 数据库“真源”对齐 (Critical)
经过多轮审计，系统已实现与生产库的物理对齐：
- **业务表 (`stock_kline_daily`)**: 使用 `volume`, `amount`, `pct_chg` (移除 `vol`, `change`)。
- **审计表 (`meta_pipeline_run`)**: 严格匹配 `biz_date`, `error_message`, `started_at` 等 DDL 字段。
- **就绪表 (`meta_data_readiness`)**: 匹配 `table_name`, `biz_date`, `status='READY'`, `ready_at`, `storage='MYSQL'`, `record_count`。

---

## 4. 运维与测试指南

### 3.1 部署命令
在本地目录下执行对应的函数部署脚本（会自动回溯打包 `shared/` 目录及 `.env` 配置）：
```bash
# 部署元数据同步函数 (Meta Sync)
python3 functions/meta_sync/deploy.py

# 部署行情同步函数 (Daily Quotes)
python3 functions/daily_quotes/deploy.py
```

### 3.2 手动测试 Payload
在控制台测试时可使用以下 JSON：
```json
{
  "ts_code": "600519.SH",
  "trade_date": "20260511",
  "source": "tushare",
  "auto_fallback": true
}
{
  "ts_code": "000004.SZ",
  "trade_date": "2026-05-11",
  "source": "tushare"
}

```

### 3.3 定时触发器 (Cron) 建议
为保证数据最新且节省成本，建议在腾讯云控制台配置以下两个触发器：
1. **股票列表同步 (`op: sync_stock_list`)**:
   - **频率**: 每天凌晨 01:00
   - **Cron**: `0 0 1 * * * *`
2. **交易日历同步 (`op: sync_calendar`)**:
   - **频率**: 每月 1 号凌晨 01:30
   - **Cron**: `0 30 1 1 * * *`

### 3.4 故障排查
1. **1054 报错**: 优先核对 `docs/design/复盘/db_inventory.md` 中的物理结构。
2. **连接超时**: 检查 SCF 的 VPC 配置是否失效，或内网 MySQL 安全组是否允许 `172.17.x.x` 网段访问。
3. **数据为空**: 检查 `TUSHARE_TOKEN` 是否过期，或该交易日数据尚未由交易所发布。

---

## 5. 依赖清单 (Layer 绑定)
- `pandas`: 数据处理
- `tushare`: P0 采集源
- `akshare`: P1 补充源
- `easyquotation`: P2 实时备选源
- `aiomysql`: 异步 DB 驱动

---
**交付记录**:
- **状态**: 🟢 生产就绪 (Production Ready) & Monorepo 架构升级
- **交付人**: Antigravity AI
- **日期**: 2026-05-12
