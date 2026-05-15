# Task List - E7-S2: Shadow Audit Production Hardening

- [x] **T1: 审计引擎重构 (ShadowAuditor)**
    - [x] 废弃临时文件 Markdown 生成，改为内存字符串流
    - [x] 实现对账报告持久化至数据库 `report_content` 字段
    - [x] 引入 7 维 MAE 矩阵判定逻辑 (Close MAE < 0.05)
- [x] **T2: 数据源量纲对齐 (AkShareAdapter)**
    - [x] 诊断 Sina 源与 EM 源的成交量单位差异
    - [x] 实施统一的 `/ 100.0` (股转手) 转换逻辑
    - [x] 增加转换异常的防御性日志
- [x] **T3: 云端入口与稳定性加固**
    - [x] 修复 SCF 触发器重复创建的容错处理
    - [x] 下线 `verify_ak_spot` 调试接口，强化 `COLLECTORS` 初始化保护
    - [x] 升级 `asyncio` 获取运行循环的安全性
- [x] **T4: 生产验证与存证**
    - [x] 执行 2026-05-13 全量收盘影子审计
    - [x] 确认 MAE 收敛至理想区间 (Volume MAE < 0.3)
    - [x] 同步更新 `done-list-tables.md` 采集状态
