# Walkthrough - E6-S2: SCF Collector Debugging & Local Integration

## 1. 调试目标
建立稳定的本地调试环境，验证数据抓取与数据库写入逻辑。

## 2. 调试过程

### Phase 1: 数据抓取验证 (Fetch-Only)
- **脚本**: `scratch/test_fetch_only.py`
- **执行结果**:
```text
H:\AppData\Roaming\Python\Python311\site-packages\requests\__init__.py:109: RequestsDependencyWarning: urllib3 (2.0.4) or chardet (7.4.3)/charset_normalizer (3.2.0) doesn't match a supported version!
  warnings.warn(
--- Fetch Test Start ---
[Tushare] Normalized data sample (first 1 rows):
  ts_code trade_date    open    high     low   close  pre_close  volume        amount  turnover   pct_chg  trade_status
0  600519.SH 2026-05-11  1372.89  1372.89  1361.0  1361.33    1372.99   57135  7.790721e+09       0.0 -0.008492             1
--- Fetch Test End ---
```
- **结论**: Tushare 归一化逻辑（小数化、金额转换）符合预期。

### Phase 2: 本地集成验证 (DB Write)
- **环境**: Docker MySQL 5.7 (localhost:33066)
- **脚本**: `scratch/debug_local.py`
- **物理查验日志** (来自 `scratch/check_db.py`):
```text
Total Rows: 1
{'ts_code': '600519.SH', 'trade_date': datetime.date(2026, 5, 11), 'open': Decimal('1372.8900'), 'high': Decimal('1372.8900'), 'low': Decimal('1361.0000'), 'close': Decimal('1361.3300'), 'pre_close': Decimal('1372.9900'), 'volume': 57135, 'amount': Decimal('7790721392.0000'), 'turnover': Decimal('0.000000'), 'pct_chg': Decimal('-0.008492'), 'trade_status': 1, 'created_at': datetime.datetime(2026, 5, 12, 2, 51, 15)}

Pipeline Logs: 1
{'run_id': 'local-debug-session', 'pipeline_id': 'Data-Hub', 'biz_date': datetime.date(2026, 5, 11), 'status': 'success', ...}
```

## 3. 验证结论
本地集成测试 **100% 通过**，审计日志已正确记录。
