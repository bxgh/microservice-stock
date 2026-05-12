# Technical Report - E6-S2: SCF Collector Integration Testing

## 1. 摘要
完成 `scf-collector` 的本地环境标准化配置，成功通过 Tushare 数据源的抓取、归一化及数据库写入测试。

## 2. 关键变更

### 环境隔离
- 引入 `docker-compose-test.yml`，提供 MySQL 5.7 本地镜像。
- 将调试脚本统一迁移至 `scratch/` 目录，符合 `AGENTS.md` 的根目录整洁规范。

### 部署优化
- 增强 `deploy.py`，支持 `--test` 参数，为云端蓝绿部署/替身测试提供工具支撑。

## 3. 问题与对策
- **网络连接**: 发现 AkShare/Mootdx 在 WSL2 代理下存在解析异常，已在 `debug_guide.md` 中记录排查建议。
- **环境连通性**: 解决了 Windows 宿主机连接 Docker 容器的 MySQL 时序初始化问题（增加 retry/wait 逻辑）。

## 4. 后续计划
1. 在云端创建 `stock-collector-test` 函数进行网络连通性验证（Phase 3）。
2. 修复 AkShare/Mootdx 的 Fallback 降级逻辑。
