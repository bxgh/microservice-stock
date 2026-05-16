# API 变更存证 (E13-S2)

## 1. 采集脚本详情
本次实施产出的采集脚本 `tushare_backfill_standalone.py` 是针对云端服务器环境深度优化的回填引擎。

### 脚本位置
- `stock-manager-api/tushare_backfill_standalone.py` (容器内运行版)
- `scf-collector/scripts/tushare_full_backfill.py` (标准库适配版)

## 2. 数据口径变更 (Truth Source)
| 字段 | Tushare 接口字段 | 处理逻辑 | 最终入库单位 |
|---|---|---|---|
| `amount` | `amount` (千元) | `* 1000.0` | **元** |
| `volume` | `vol` (手) | `float(val)` | **手** (Lots) |
| `pct_chg`| `pct_chg` (%) | `/ 100.0` | **小数** (Decimal) |

## 3. 进度审计契约 (Sync Progress)
回填引擎严格依赖 `sync_progress` 表进行断点续传。
- **任务标识 (task_name)**: `full_market_backfill`
- **进度标识 (current_code)**: `YYYYMMDD` (交易日字符串)
- **状态 (status)**: `completed`

## 4. 调用示例
```bash
docker exec -d stock-manager python /app/tushare_backfill_standalone.py
```
监控命令:
```bash
docker logs -f stock-manager
```
