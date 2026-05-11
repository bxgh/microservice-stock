# 异动捕捉模块 · 设计交付文档 v1.1

| 项 | 内容 |
|---|---|
| **文档版本** | v1.1 |
| **生成日期** | 2026-05-02 |
| **替代版本** | v1.0(2026-05-02) |
| **适用项目** | A 股盘后复盘体系 · L8 扩展模块 |
| **数据库** | MySQL 5.7 |
| **状态** | 已对齐共识,待实施 |

---

## 1. 简介

本模块在 L8 现有基础上扩展,产出**统一异动池** + **每日 Top 10 推送清单**,作为后续"观察点系统"的信号供给层。

### 1.1 v1.1 核心变化
- **弹性设计**: 标签 + Profile 替代固定优先级。
- **形态标签**: 扩展至 22 个细分标签,大幅强化形态识别。
- **多维印证**: 引入共振等级 (L1-L5)、反向信号、时间共振。
- **数据保留**: 被忽略的涨停也入库,带 `excluded_reasons` 标注。

### 1.2 目标与范围
- 产出 3 类异动池 (strong / early / trap)。
- 每条信号附带完整多维标签及多维印证评估。
- 综合评分函数支持权重热配置及重复跟踪压制。

---

## 2. 文档索引

1.  **[E1 数据结构](file:///home/ubuntu/microservice-stock/docs/design/异动股捕捉/E1_Data_Structure.md)**: 派生指标表、统一信号表、标签字典、Profile 配置等 9 张表。
2.  **[E2 信号判定与标签体系](file:///home/ubuntu/microservice-stock/docs/design/异动股捕捉/E2_Signal_Rules.md)**: 标签判定框架、三池产出逻辑、多维印证计算。
3.  **[E3 综合评分与可解释性](file:///home/ubuntu/microservice-stock/docs/design/异动股捕捉/E3_Scoring_Function.md)**: 评分公式、子项细则、中文说明生成。
4.  **[E4 Top 10 推送规则](file:///home/ubuntu/microservice-stock/docs/design/异动股捕捉/E4_Top10_Rules.md)**: 动态配额、填补规则及推送生成逻辑。
5.  **[E5 系统集成](file:///home/ubuntu/microservice-stock/docs/design/异动股捕捉/E5_System_Integration.md)**: 数据流向、任务编排及下游接口。
6.  **[附录](file:///home/ubuntu/microservice-stock/docs/design/异动股捕捉/Appendices.md)**: 标签字典列表、预设 Profile 详情、生命周期预留。

---

## 3. 核心共识 (基线)

- **定位**: 信号优选 → 多维标注 → Top 10 输出。
- **三池**: `strong` (强异动)、`early` (启动前)、`trap` (陷阱)。
- **启动前优先组合**: 龙头预备役 > 连板接力 > 箱体蓄势 > 趋势反转。
- **弹性原则**: 系统不替用户预设涨停优先级,通过 Profile 实现。

---

## 4. 实施路线

- **技术依赖**: 依赖 L1-L8 已有数据。
- **里程碑**: 预计工时 9 天,从 DDL 落地到调度集成。
- **风险点**: MySQL 5.7 排名计算性能、形态判定复杂度、权重调优。
