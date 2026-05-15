# E7-S1 实施闭坑指南 (Pitfall Avoidance Guide)

> **导读**: 本文档记录了在 E7-S1 Phase 1 开发中由于疏忽导致的典型错误，按角色职责分类，旨在防止后续 Phase 2/3 重蹈覆辙。

---

## 1. [DB Auditor] 数据库审计角色

### 🚩 陷阱 1: MySQL 5.7 `Updated At` 停滞
- **现象**: 执行 `ON DUPLICATE KEY UPDATE` 时，如果更新的值与原值完全相同，`updated_at` 字段不会自动触发更新。
- **闭坑**: 必须在 OKU 子句中显式赋值：`updated_at = CURRENT_TIMESTAMP`。
- **教训**: 不要盲目信任数据库的自动触发器，关键审计点（如快照锁定时间）必须人工确认刷新。

### 🚩 陷阱 2: 老表结构“先入为主”
- **现象**: 在 `stock_basic_info` 这种老表的查询中误加了 `is_deleted = 0` 过滤，导致 SQL 报错（老表无此字段）。
- **闭坑**: 实施 DDL 管理前，必须通过 `DESCRIBE` 物理确认老表字段，严禁凭经验假设。

---

## 2. [Security Auditor] 安全审计角色

### 🚩 陷阱 3: 临时脚本凭据泄露
- **现象**: 在 `scratch/` 脚本中为了测试方便硬编码了 `MYSQL_PASSWORD` 和 `TUSHARE_TOKEN`。
- **闭坑**: 
  1. 所有脚本必须通过 `load_dotenv` 从 `.env` 加载凭据。
  2. 必须在 `.gitignore` 中显式排除 `scratch/` 目录或特定脚本名。
- **教训**: 临时代码也是代码，一旦提交 Git，凭据即视为失效且需重置。

---

## 3. [Backend Engineer] 后端开发角色

### 🚩 陷阱 4: 资源初始化冗余 (SCF 优化)
- **现象**: 每次方法调用都执行 `ts.pro_api(token)`。在 SCF 环境下，这会增加网络往返和冷启动开销。
- **闭坑**: 在类 `__init__` 中初始化 `self.pro` 并持久化复用。
- **教训**: Serverless 编程需时刻关注“执行上下文重用”以优化性能。

### 🚩 陷阱 5: 逐条写入与性能瓶颈
- **现象**: 停牌数据同步采用 `for ... await execute_query`。
- **闭坑**: 后续应迁移至 `executemany` 模式，将 31 次数据库往返压缩为 1 次，防止 SCF 在极端行情（如大面积停牌）下超时。

---

## 4. [Infra Specialist] 基础设施角色

### 🚩 陷阱 6: 逻辑链路的“静默空转”
- **现象**: 非交易日请求停牌接口返回空 DataFrame，代码不做任何提示即退出。
- **闭坑**: 必须增加 `INFO` 级别日志说明（如 `Returned empty for non-trading day`），防止监控人员因观察到“零结果”而误报系统故障。

---

## 5. [Data Quality Steward] 数据质量角色

### 🚩 陷阱 7: 快照幂等性风险
- **现象**: 早期 SQL 未处理 `biz_date` 的 `ON DUPLICATE KEY UPDATE`。
- **闭坑**: 快照必须支持“覆盖写入”而非“报错中断”。如果 09:30 的任务重跑，系统应能自动更新当日基准，确保 17:00 校验使用的是最新的采样数据。

---

**[Backend Engineer] 签名**: _________________  
**[DB Auditor] 签名**: _________________  
**日期**: 2026-05-13
