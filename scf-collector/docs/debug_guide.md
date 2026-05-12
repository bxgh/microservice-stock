# SCF Collector 调试指南 (Standard Debugging Process)

本指南定义了 `scf-collector` 模块的标准调试流程，旨在帮助开发者快速定位问题，同时确保不影响生产环境的稳定性。

---

## 1. 调试环境准备

在开始调试前，请确保您的本地环境已按以下标准配置：

- **Python 版本**: 必须使用 `Python 3.10` (与云端运行环境对齐)。
- **虚拟环境**: 建议使用 `venv` 隔离依赖。
  ```bash
  python -m venv venv
  .\venv\Scripts\activate
  pip install -r scf-collector/requirements.txt
  ```
- **环境变量**: 确保 `scf-collector/.env` 中包含有效的 `TUSHARE_TOKEN` 和测试数据库配置。
- **WSL2 配置**: 若在 WSL2 下运行 Docker，请参考 `docs/wsl-set.md` 配置好宿主机代理。

---

## 2. 标准调试三阶段

### 第一阶段：脱机抓取调试 (Phase 1: Fetch-Only)
**目的**: 验证 API 令牌是否生效，抓取逻辑和数据归一化（Normalization）是否正确。
- **操作**: 运行 `python scratch/test_fetch_only.py`。
- **关注点**: 
  - `pct_chg` 是否已除以 100 变为小数？
  - `amount` 是否已乘以 1000 变为元？
  - 是否所有源（Tushare/AkShare/Mootdx）都能正常返回数据？

### 第二阶段：本地集成调试 (Phase 2: Local Integration)
**目的**: 验证数据库写入逻辑、Schema 兼容性及异步并发处理。
- **操作**: 
  1. 启动本地 Docker 测试库：`docker-compose -f scratch/docker-compose-test.yml up -d`。
  2. 运行本地完整调试脚本：`python scratch/debug_local.py`。
- **关注点**:
  - `ON DUPLICATE KEY UPDATE` 是否正常工作（重复写入不报错）？
  - 数据库连接池是否存在泄漏？
  - 资源占用情况：观察 `vmmem` (WSL2) 的内存占用是否在可控范围内。

### 第三阶段：云端替身调试 (Phase 3: Cloud Staging)
**目的**: 验证腾讯云 VPC 网络连通性、Layer 依赖加载及真实的冷启动耗时。
- **操作**: 
  1. 部署至测试函数：`python scf-collector/deploy.py --test`。
  2. 在腾讯云控制台使用“测试”功能，输入 Payload 进行验证。
- **关注点**:
  - 是否出现 `ImportError` (说明 Layer 没挂载对)？
  - 连接数据库是否超时 (说明 VPC/安全组没配对)？

---

## 3. 常见问题排查词典 (FAQ)

| 现象 | 可能原因 | 解决办法 |
| :--- | :--- | :--- |
| `ConnectionTimeout` | VPC 配置错误或内网库安全组未放行 | 检查 `VPC_ID` 和 `SUBNET_ID` 是否与数据库一致。 |
| `ImportError: pandas` | Layer 依赖未正确加载 | 检查 `index.py` 开头的 `sys.path` 插入逻辑，确保包含 `/opt/python`。 |
| 数据全是 `0` 或 `None` | API 积分不足或 Token 错误 | 检查 `.env` 中的 `TUSHARE_TOKEN`。 |
| 内存溢出 (OOM) | 数据量过大或 Pandas 内存碎片 | 建议分批次处理，或增加云函数的内存配置（推荐 256MB+）。 |

---

## 4. 资源监控建议

1. **本地**: 使用 `htop` (Linux/WSL) 或 任务管理器观察内存。
2. **云端**: 开启腾讯云 **CLS 日志服务**，通过 `monitoring` 视图观察函数的内存使用曲线和耗时。

---
**版本**: v1.0  
**更新日期**: 2026-05-12
