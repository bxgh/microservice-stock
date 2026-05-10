# Walkthrough - E200-S3 级联失效与同步阻塞

## 1. 环境准备
已应用数据库迁移，新增 `meta_sync_status` 表并扩展 `meta_repair_log`。

## 2. 功能演示

### 2.1 正常同步流程 (ACKed)
在模拟修复过程中，同步网关更新了 LSN 位点，自愈引擎成功捕获 ACK。

```text
[INFO] 等待同步 ACK: 表=stock_kline_daily, 基准 LSN=100, 超时=60s
[INFO] 收到同步 ACK: 表=stock_kline_daily, 当前 LSN=105
[INFO] 成功修复异常 9128: 600519.SH@2026-05-10 via MOOTDX, Sync: ACKED
```

### 2.2 超时降级流程 (Orphan)
若同步网关在 60s 内未返回 ACK，系统将标记为孤儿状态。

```text
[WARNING] 同步 ACK 超时 (5s): 表=stock_kline_daily, 数据判定为 ORPHAN 状态
[INFO] 成功修复异常 9129: 600519.SH@2026-05-10 via MOOTDX, Sync: ORPHAN
```

### 2.3 级联失效演示 (Cascade)
修复后，下游 ADS 视图被自动清理以触发重算。

```sql
-- 验证清理结果
SELECT COUNT(*) FROM ads_kline_adj WHERE ts_code='600519.SH' AND trade_date='2026-05-10';
-- 结果: 0 (修复前为 1)
```

## 3. 验证结果
| 测试用例 | 预期结果 | 实际结果 | 状态 |
| :--- | :--- | :--- | :--- |
| 同步 ACK 捕获 | 状态标记为 ACKED | 状态为 ACKED, LSN 记录准确 | ✅ |
| 同步超时处理 | 状态标记为 ORPHAN | 状态为 ORPHAN, 继续级联任务 | ✅ |
| ADS 视图清理 | 关联记录被物理删除 | 记录已删除 | ✅ |
| 信号发送 | 插入 recalc_signal | 指令已生成 | ✅ |

---
**附件**: [REPORT.md](file:///home/ubuntu/microservice-stock/docs/design/数据管线/自愈管线/implementation_logs/E200/S3/REPORT.md)
