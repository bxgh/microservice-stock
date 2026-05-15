# Task List: [E12-S1] 分层数据完整性巡检 (Multi-Tier Integrity Checker)

## 状态说明
- `[ ]` 未开始
- `[/]` 进行中
- `[x]` 已完成

---

## 实施任务

### 1. 脚本开发 (E12-S1-T1)
- [ ] 创建 `scf-collector/scripts/inspect/check_kline_integrity.py`
- [ ] 实现 `--mode=[full|delta]` 参数解析逻辑
- [ ] 编写核心 SQL：基于 `meta_trading_calendar` 与 `stock_kline_daily` 的 LEFT JOIN 查漏逻辑
- [ ] 封装 Chunking 分批处理机制，支持 2000 万行量级对比

### 2. 状态维护 (E12-S1-T4)
- [ ] 在数据库中确认/创建 `meta_config` 相关配置项 `last_kline_check_date`
- [ ] 实现增量模式下的日期范围自动计算（基于 `last_kline_check_date` 至 今日）

### 3. 环境部署 (E12-S1-T2 & T3)
- [ ] **Docker 部署**: 将脚本映射至 `stock-manager` 容器，验证 Full 模式运行
- [ ] **SCF 部署**: 创建定时触发的 SCF 云函数，验证 Delta 模式运行

### 4. 任务下发 (E12-S1-T3)
- [ ] 实现巡检发现空洞后，向 `meta_task_queue` 自动插入 `kline_refetch` 任务的逻辑

---

## 验收标准 (AC) 验证记录
- [ ] **AC1: 增量巡检准确性**
- [ ] **AC2: 基准校验性能**
