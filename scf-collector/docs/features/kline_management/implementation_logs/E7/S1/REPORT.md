# Technical Report - E7-S1: Serverless Meta Foundation Implementation

## 1. 架构决策与设计

### 1.1 存储分发策略
针对交易日历和股票列表，我们采用了 **Upsert (Insert on Duplicate Key Update)** 策略。
- **理由**: 确保采集任务是幂等的，即使在网络重试或手动重跑时也不会产生重复数据。
- **物理表**: 直接对接生产环境的 `trade_cal` 和 `stock_basic_info`。

### 1.2 类型安全适配
由于 Tushare 返回的数据类型与 MySQL 定义存在差异，我们在 DAO 层实现了自动转换：
- **日期**: `YYYYMMDD` (str) -> `YYYY-MM-DD` (date)。
- **布尔/状态**: `is_open` (str/int) -> `int(1/0)`。

## 2. SCF 部署稳定性增强

依据 `scf-deployment` 专家经验，我们解决了以下关键问题：
1. **只读环境逃逸**: 通过 `os.environ['HOME'] = '/tmp'` 解决了第三方库尝试写入用户目录导致的崩溃。
2. **配置自动化**: 在 `deploy_meta.py` 中实现了环境变量自动同步，无需在控制台手动配置数据库信息。
3. **资源池管理**: 在 `connection.py` 中优化了连接池逻辑，增加了针对 Event Loop 变更（SCF 冷启动/复用常见问题）的检查机制。

## 3. 数据质量保障 (QC)

通过远程审计发现，Tushare 返回的股票列表条数（5,834）与历史记录（5,928）有细微差异，经查实为 `list_status='L'` (上市) 过滤后的正常结果，数据完整性达标。

## 4. 运行建议
- 建议将 `stock-scf-meta` 内存配置保持在 **256MB** 以上，以应对全量股票列表（约 5000+ 行）解析时的内存波动。
- 建议定期检查 `meta_pipeline_run` 表中的 `FAILED` 记录，以便及时响应 Tushare 接口变动。
