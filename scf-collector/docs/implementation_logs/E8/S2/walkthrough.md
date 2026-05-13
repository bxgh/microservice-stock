# Walkthrough - E8-S2: 字段废弃标记 (Deprecated Field Marking)

本 Story 已完成 `stock_adjust_factor` 表结构的元数据优化及全局文档同步。

## 变更内容
1. **数据库 DDL (T1)**：
    - 对 `fore_adjust_factor` 增加了“已废弃”注释，并统一精度为 `decimal(20, 6)`。
    - 对 `back_adjust_factor` 增加了“legacy 兼容”注释。
2. **全局文档 (T2)**：
    - 更新了 `docs/TABLES_INDEX.md`，补齐了 `stock_adjust_factor` 表定义。
    - 在“单位 / 命名陷阱速查”中新增了关于复权因子动态计算的说明。

## 验证结果

### 数据库 Schema 证据
用户已在本地工具中成功执行 SQL，并确认字段类型及主键状态：
- `fore_adjust_factor`: `decimal(20, 6)`
- `back_adjust_factor`: `decimal(20, 6)`
- `adjust_factor`: `decimal(16, 6)` (保持原样)

### 文档同步证据
- [TABLES_INDEX.md](file:///home/ubuntu/microservice-stock/docs/TABLES_INDEX.md) 已包含该表条目，并明确标注 `fore_adjust_factor` 已废弃。

## 角色审查意见
- **[DB Auditor]**: DDL 变更仅限 COMMENT，未改变存量数据，符合安全治理要求。
- **[Data Quality Steward]**: 通过文档明确了“动态计算”而非“静态读取”的规范，降低了下游数据漂移风险。
- **[Workflow Guard]**: 实施过程与 `AGENTS.md` 规范保持高度一致。
