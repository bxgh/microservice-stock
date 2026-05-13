# Task List - E7-S5: Trading Day Aware Trigger Control

- [x] **E7-S5-T1**: 扩展 `StockDAO` 添加 `is_trading_day`
  - [x] 实现 SQL 查询逻辑
  - [x] 确保处理日期格式转换
- [x] **E7-S5-T2**: 开发 `shared/utils/trading_day.py`
  - [x] 定义 `TradingDayGuard` 类
  - [x] 实现白名单检查逻辑
  - [x] 添加日志埋点
- [x] **E7-S5-T3**: 重构 `functions/meta_sync/index.py`
  - [x] 注入 `TradingDayGuard` 校验
  - [x] 处理异常返回
- [x] **E7-S5-T4**: 重构 `functions/daily_quotes/index.py`
  - [x] 同上
- [x] **E7-S5-T5**: 编写测试用例并验证
  - [x] `tests/test_trading_day.py`
  - [x] 本地模拟 SCF 调用
