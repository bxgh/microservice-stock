# Task List - E7-S1: 基础元数据云端同步

- [x] **T1: 核心库扩展 (Core Library)**
    - [x] `TushareCollector` 支持 `fetch_trading_calendar`
    - [x] `TushareCollector` 支持 `fetch_stock_list`
    - [x] `StockDAO` 支持 `save_trading_calendar` (目标表: `trade_cal`, 需转换日期和 INT 格式)
    - [x] `StockDAO` 支持 `save_stock_list` (目标表: `stock_basic_info`, Upsert 逻辑, 需处理日期字段)
- [x] **T2: 元数据入口 (Entry Point)**
    - [x] `meta_index.py` 头部注入 `/tmp` 环境重定向代码
    - [x] 创建 `meta_index.py` 处理 `sync_calendar` 操作
    - [x] 创建 `meta_index.py` 处理 `sync_stock_list` 操作
    - [x] 实现 SCF 标准 `main_handler` 封装
- [/] **T3: 部署与触发器 (Deployment)**
    - [x] 创建 `deploy_meta.py` 部署脚本
    - [ ] 验证云端函数创建与连通性
- [ ] **T4: 验证与交付 (Verification)**
    - [x] 跑通 `pytest` 单元测试 (Mock)
    - [ ] 编写 `tests/remote_invoke_meta.py` 使用 SDK 触发验证
    - [ ] 云端日志审计 (确认无只读报错)
    - [ ] 产出 `REPORT.md` 和 `API.md`
