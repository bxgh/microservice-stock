# Walkthrough: SCF Collector 生产化部署与全链路对齐

## 1. 任务背景
实现 `scf-collector` (Serverless Cloud Function) 在腾讯云生产环境的稳定运行，打通云函数与私有 VPC 内 MySQL 数据库的连接，并确保数据采集、转换、入库、审计的全链路闭环。

## 2. 实施关键路径

### A. 运行环境治理 (Runtime & Dependencies)
- **动态路径插入**: 在 `index.py` 中增加了对 `/opt` 和 `/opt/python` 的强力扫描，解决了 `pandas`, `tushare` 等 Layer 依赖加载失败的问题。
- **只读文件系统绕行**: 针对 `mootdx` 等库需要写缓存的问题，强制将 `MOOTDX_CACHE_DIR` 定位至 `/tmp`。
- **部署模式切换**: 放弃不稳定的 `Serverless Framework` 组件，切换为基于腾讯云 Python SDK 的原生 API 部署 (`UpdateFunctionCode`)，规避了 10MB+ 代码包的同步延迟问题。

### B. 网络与安全配置 (Networking)
- **VPC 穿透**: 完成了云函数与 `vpc-0qlg45u2` / `subnet-4t57ej5f` 的绑定，成功访问内网 IP `172.17.0.10:3306`。
- **凭据同步**: 通过 API 强力注入了 `TUSHARE_TOKEN`, `DB_HOST`, `DB_PASSWORD` 等生产环境变量。

### C. 数据一致性对齐 (Schema Alignment) - **核心突破口**
在经历了多次 `1054 Unknown column` 报错后，通过读取 `db_inventory.md` 建立了以下“真源”映射：
1. **业务表 (`stock_kline_daily`)**:
   - 字段名纠正：`vol` ➔ `volume`
   - 移除不存在字段：`change`, `updated_at`
2. **审计表 (`meta_pipeline_run`)**:
   - 完全匹配 DDL：`pipeline_id`, `biz_date`, `error_message`, `started_at` 等。
3. **状态表 (`meta_data_readiness`)**:
   - 字段对齐：`table_name`, `biz_date`, `status`, `ready_at`, `storage`, `record_count`。

## 3. 验证存证

### 日志片段 (成功入库)
```text
INFO:shared.db.connection:Connecting to MySQL at 172.17.0.10:3306...
INFO:shared.db.connection:MySQL connection pool created successfully.
INFO:[c380e0b0-...] Start collecting 600519.SH for 20260511. Preferred: tushare
INFO:[c380e0b0-...] Trying source: tushare...
INFO:shared.db.dao:Saving 1 records to stock_kline_daily...
INFO:shared.utils.notifier:Sending success notification for Data-Hub on 20260511...
Response: {"status": "success", "source_used": "tushare", "count": 1, "request_id": "c380e0b0-..."}
```

### SQL 真实查询验证
```sql
-- 验证业务数据
SELECT * FROM stock_kline_daily WHERE ts_code='600519.SH' AND trade_date='2026-05-11';
-- 验证审计日志
SELECT status, biz_date, error_message FROM meta_pipeline_run WHERE run_id='c380e0b0-...';
-- 验证就绪信号
SELECT * FROM meta_data_readiness WHERE biz_date='2026-05-11' AND table_name='stock_kline_daily';
```

## 4. 结论
系统已实现从“羊拉屎”式的零散修复到“全链路对齐”的平稳过渡。当前 `scf-collector` 已具备生产环境 7x24 自动调度的能力。
