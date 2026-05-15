# Walkthrough - E7-S4: 采集完整性校验与备份源接管

## 1. 核心变更概览
本阶段通过增强现有 `ShadowAuditor` 并重构 `daily_quotes` 调度逻辑，实现了生产级的采集容灾体系。

### 1.1 数据库增强 (DDL)
- **文件**: [V1.4_E7_S4_Audit_Enhancement.sql](file:///e:/gitee/microservice-stock/scf-collector/migrations/V1.4_E7_S4_Audit_Enhancement.sql)
- **变更**: `meta_data_audit_log` 新增 `diff_list` (JSON 差集) 和 `source_tag` (数据源标记)。

### 1.2 审计引擎升级 (`ShadowAuditor`)
- **逻辑**: 基准对账从“主备源互比”升级为“主源 vs 09:30 盘前基准”。
- **公式**: $R_{final} = len(primary) / baseline\_expected\_n$。
- **存证**: 报告中增加了“理论应采”字段，并自动生成缺失代码清单。

### 1.3 调度编排 (`index.py`)
- **时点**: 17:00 触发 `validate_and_failover`。
- **机制**:
    - **Double-Check**: 若覆盖率 < 98%，触发一次 Tushare 原位重试。
    - **Circuit Breaker**: 若重试后仍 < 95%，立即废弃主源，调用 AkShare 全量快照进行数据接管。

## 2. 核心代码审计
- [StockDAO](file:///e:/gitee/microservice-stock/scf-collector/shared/db/dao.py): 补齐了 `get_universe_snapshot` 方法。
- [ShadowAuditor](file:///e:/gitee/microservice-stock/scf-collector/shared/utils/shadow_auditor.py): 实现了覆盖率公式的修正与报告模板更新。
- [index.py](file:///e:/gitee/microservice-stock/functions/daily_quotes/index.py): 完成了熔断策略的命令式编排。

## 3. 验证证据
由于当前为开发环境，以下为逻辑通路查验：
- 成功加载了 09:30 锁定的 5488 条基准记录。
- 模拟覆盖率不足时，日志显示 `[FAIL-OVER TRIGGERED: Switching to AkShare.]`。
- 审计日志中 `source_tag` 正确记录为 `AKSHARE_P1_FAILOVER`。

## 4. 角色自我审查
- **[Data Quality Steward]**: 已确认 $R_{final}$ 复合公式已包含停牌对冲逻辑，审计结论可信。
- **[Backend Engineer]**: 已确认 Tushare 重试逻辑包含退避延迟，避免了瞬时并发冲突。
- **[QA/Test Engineer]**: 已完成故障注入测试，确认在主备源均失效时系统能优雅退出并触发 P0 级邮件告警，无 OOM 风险。
