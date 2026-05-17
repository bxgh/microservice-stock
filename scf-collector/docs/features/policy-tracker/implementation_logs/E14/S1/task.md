# Task List - E14-S1: Data Acquisition Layer

- [x] `[E14-S1-T1]` 数据库 Schema 落地与测试 (MySQL 5.7)
    - [x] 编写 DDL 脚本
    - [x] 执行建表并验证审计字段
- [x] `[E14-S1-T2]` 编写中国政府网 (gov.cn) 采集适配器
    - [x] 实现列表页抓取
    - [x] 实现详情页解析与 MD5 计算
    - [x] 验证入库逻辑
- [x] `[E14-S1-T3]` 独立测试云函数配置 (`scf-policy-monitor`)
    - [x] 创建 `monitor_index.py` 入口
    - [x] 联调微信/邮件通知链路
- [x] `[E14-S1-T4]` 交付物闭环
    - [x] 生成 `REPORT.html`
    - [x] 更新 `done-list-tables.md`
    - [x] 更新 Portal 索引

- [x] `[E14-S1-T5]` `GovCollector` 增强（解析发文机关动态归属为 `PBC`、`CSRC`）
- [x] `[E14-S1-T6]` 编写中国证监会 (csrc.gov.cn) 采集适配器 (`CsrcCollector`)
- [x] `[E14-S1-T7]` 整合 `index.py` 与微信/邮件分发通知
- [x] `[E14-S1-T8]` 编写单元测试与全面管道验证
