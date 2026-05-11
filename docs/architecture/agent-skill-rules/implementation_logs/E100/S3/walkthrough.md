# Walkthrough - E100-S3 数据质量 QC 准则优化

## 实施概述
针对 E1-S1 实施中暴露出的映射错误问题，对项目的治理文档进行了全面升级。引入了“映射矩阵验证”和“灰度同步”机制，将数据质量从“事后抽验”提升为“事前/事中强制约束”。

## 主要变更

### 1. 角色能力升级 ([ROLES.md](file:///home/ubuntu/microservice-stock/docs/architecture/agent-skill-rules/ROLES.md))
- 在 `[Data Quality Steward]` 角色中新增 3 条核心禁令：
    - **映射验证 (Matrix Check)**: 强制要求输出 API vs DB 的首条记录对比矩阵。
    - **灰度同步 (Grey-scale)**: 强制要求在全量回填前进行 10-50 条样本验证。
    - **核心字段零容忍**: 对 Fact 数据（如资产总计、净利润）的 NULL 率进行严控。

### 2. 治理框架升级 ([AGENTS.md](file:///home/ubuntu/microservice-stock/AGENTS.md))
- 新增 **5.4 节 数据质量闭环**：
    - 明确了映射双检、灰度先行、空值红线三大原则。
    - 将数据质量审计正式列入真源验证流程。

### 3. 指导手册发布 ([QC_GUIDELINES.md](file:///home/ubuntu/microservice-stock/docs/architecture/QC_GUIDELINES.md))
- 发布了标准化的数据接入检查清单，包含开发期、部署前、运行期、故障修复四个阶段的标准化操作。

## 验证结果

### 1. 规则应用实战：现金流量表修复
- **映射对齐**: 
    - `Tushare: n_cashflow_act` -> `DB: net_cash_flows_oper_act` [Verified]
    - `Tushare: n_cashflow_inv_act` -> `DB: net_cash_flows_inv_act` [Verified]
    - `Tushare: n_cash_flows_fnc_act` -> `DB: net_cash_flows_fnc_act` [Verified]
- **灰度验证**: 执行前 10 只股票同步，确认 `net_cash_flows_oper_act` 不再为 NULL。
- **全量修复**: 目前 `repair_cashflow_history.py` 正在运行中。
    - **当前进度**: 已修复 2200+ 条记录，NULL 值率正在快速下降。

### 2. QC 脚本证据
执行 `scratch/check_repair_progress.py` 结果：
```text
Repaired records: 2214
Total records: 278635
```

## 当前状态
- 数据治理准则已更新至 v1.4 版本。
- 现金流量表历史数据正在稳步修复中。
