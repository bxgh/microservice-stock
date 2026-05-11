# 技术报告：SCF Collector 生产环境部署总结

## 1. 系统概览
`scf-collector` 是 A 股盘后分析系统的“前哨站”，负责从第三方 API（Tushare/AkShare/Mootdx）抓取原始数据并写入云端 MySQL。

## 2. 核心技术指标
- **运行时**: Python 3.10
- **超时配置**: 900s (支持长耗时数据回填)
- **内存红线**: 256MB (Pandas 运行下限)
- **网络拓扑**: 绑定 VPC `vpc-0qlg45u2` (内网互通)

## 3. 核心依赖清单
| 依赖项 | 版本 | 角色 |
|---|---|---|
| `tushare` | latest | P0 数据源 |
| `akshare` | latest | P2 补充源 |
| `mootdx` | latest | P1 补偿源 |
| `aiomysql` | 0.2.0 | 异步数据库驱动 |
| `pandas` | 2.0.x | 数据归一化引擎 |

## 4. 熔断与自愈机制
1. **自动降级**: `Tushare` (失败) -> `Mootdx` (失败) -> `AkShare`。
2. **连接保护**: 针对 `aiomysql` 实现了 `try...finally` 闭环，确保在高并发采集下不泄露数据库连接。
3. **数据幂等**: 采用 `ON DUPLICATE KEY UPDATE` 模式，支持重复触发而不产生脏数据。

## 5. 运维建议
- **监控项**: 重点关注 `meta_pipeline_run` 中的 `status='error'` 记录。
- **扩展性**: 若需接入新表，仅需在 `dao.py` 中增加对应的 `save_*` 方法，并保持 `db_inventory.md` 的同步更新。

---
**交付人**: Antigravity AI
**交付日期**: 2026-05-11
