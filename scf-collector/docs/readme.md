# SCF Collector: 生产环境部署与全链路对齐手册

## 1. 系统角色与架构
`scf-collector` 是 A 股盘后分析系统的“数据前哨”，运行在腾讯云云函数 (SCF) 环境下。
- **职责**: 负责从 Tushare/AkShare/Mootdx 采集原始 K 线，并对齐业务表与审计元数据。
- **网络**: 通过 VPC 绑定 (`vpc-0qlg45u2`) 直连内网 MySQL (`172.17.0.10`)。

---

## 2. 核心技术复盘 (2026-05-11)

### 2.1 依赖与环境治理
- **动态路径插入**: 在 `index.py` 中强制扫描 `/opt/python`，解决了 Layer 依赖加载的顽疾。
- **只读系统绕行**: 针对 SCF 只读环境，将 `MOOTDX_CACHE_DIR` 强制重定向至 `/tmp`。
- **API 部署模式**: 切换为基于 Python SDK 的 `UpdateFunctionCode` 模式，确保大包上传的稳定性。

### 2.2 数据库“真源”对齐 (Critical)
经过多轮审计，系统已实现与生产库的物理对齐：
- **业务表 (`stock_kline_daily`)**: 使用 `volume`, `amount`, `pct_chg` (移除 `vol`, `change`)。
- **审计表 (`meta_pipeline_run`)**: 严格匹配 `biz_date`, `error_message`, `started_at` 等 DDL 字段。
- **就绪表 (`meta_data_readiness`)**: 匹配 `table_name`, `biz_date`, `status='READY'`, `ready_at`, `storage='MYSQL'`, `record_count`。

---

## 3. 运维与测试指南

### 3.1 部署命令
在本地目录下执行：
```bash
# 执行 API 强力发布 (需 .env 中配置 TENCENT_SECRET_ID/KEY)
python3 deploy.py
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

### 3.3 故障排查
1. **1054 报错**: 优先核对 `docs/design/复盘/db_inventory.md` 中的物理结构。
2. **连接超时**: 检查 SCF 的 VPC 配置是否失效，或内网 MySQL 安全组是否允许 `172.17.x.x` 网段访问。
3. **数据为空**: 检查 `TUSHARE_TOKEN` 是否过期，或该交易日数据尚未由交易所发布。

---

## 4. 依赖清单 (Layer 绑定)
- `pandas`: 数据处理
- `tushare`: P0 采集源
- `akshare`: P2 补充源
- `mootdx`: P1 补偿源
- `aiomysql`: 异步 DB 驱动

---
**交付记录**:
- **状态**: 🟢 生产就绪 (Production Ready)
- **交付人**: Antigravity AI
- **日期**: 2026-05-11
