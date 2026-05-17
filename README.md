# A 股盘后微服务数据系统 (腾讯云端仓)

[![Python 3.12](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![License-MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Microservice-Architecture](https://img.shields.io/badge/Architecture-Microservice%20%26%20Serverless-orange.svg)](docs/architecture/01_体系架构总览.md)
[![Data-Quality-Arbitration](https://img.shields.io/badge/Data%20Quality-Three--Source%20Arbitration-red.svg)](scf-collector/docs/done-list-tables.md)

本项目是一个高度解耦、弹性高可用的 A 股数据采集与 API 服务微服务集群。作为混合云量化分析系统的**公网 IO 云端仓**，系统承载着多源行情获取、高频分笔直连、数据清洗缓存、就绪探测以及数据质量自愈闭环的核心职责，并为下游移动端小程序和桌面 Web 复盘提供高性能、标准化的统一 RESTful API。

---

## 🔗 远程仓库与代码源 (Git Remotes)

本仓实行多端同步开发与双源备份机制，配置了两个高可用 Git 远程仓库：
*   **Gitee (主仓/国内同步源)**：[wwsa518/microservice-stock](https://gitee.com/wwsa518/microservice-stock) (SSH: `git@gitee.com:wwsa518/microservice-stock.git`)
*   **GitHub (镜像仓/公网公开源)**：[bxgh/microservice-stock](https://github.com/bxgh/microservice-stock) (SSH: `git@github.com:bxgh/microservice-stock.git`)

可通过以下命令配置双向推送（Push to Both Remotes）：
```bash
# 添加远程源
git remote set-url --add --push origin git@github.com:bxgh/microservice-stock.git
git remote set-url --add --push origin git@gitee.com:wwsa518/microservice-stock.git
```

---

## 🏗️ 架构设计哲学：**“IO 上云，计算下沉，存储分层”**

为了在低成本云端资源下实现机构级的量化投研数据支撑，系统遵循高度分工的架构思想：
*   **IO 上云 (Cloud Ingestion)**：利用腾讯云轻量服务器高可用及公网 IP，24小时不间断执行多源爬虫与 API 采集，保障数据链的可靠性。
*   **计算下沉 (Local Compute)**：高负载的回测、因子训练、机器学习模型运行在低成本的内网算力中心（10核 64G 节点），避免昂贵的公网算力开销。
*   **存储分层 (Tiered Storage)**：
    *   **Hot 层 (Redis)**：存储实时信号、因子缓存、任务状态与流控锁。
    *   **Warm 层 (云 MySQL 5.7)**：存储 ODS 交易行情、变动点维度、系统元数据与审计流水。
    *   **Cold/OLAP 级 (内网 ClickHouse)**：海量历史行情与因子大表，提供超 13 倍的高性能查询提速。

---

## 🚀 微服务矩阵与端口规划 (Fixed Ports)

系统由多个独立封装的 Docker 容器和 Serverless 云函数共同组成，各模块共享公网或专有网络，遵循严格的端口与资源约束：

| 模块名称 | 固定端口 | 服务角色与核心职责 | 内存限制 | 核心接口与规范链接 |
| :--- | :--- | :--- | :--- | :--- |
| **wxch-gateway** | `80` / `443` | **Nginx 网关**：负责公网 SSL 终结、路径重路由、跨域 CORS 控制及安全限流。 | 128MB | [网关配置说明](docs/architecture/02a_Nginx网关配置.md) |
| **Cloud-API** | `8000` | **BFF 聚合层**：统一公网入口，负责 JWT 用户鉴权、API 转发及基于 Redis 的任务调度。 | 800MB | [Cloud-API BFF 规范](docs/architecture/02b_Cloud-API聚合层.md) |
| **baostock-api** | `8001` | **BaoStock 代理服务**：封装 TCP 协议，负责提供增量历史 K 线下载、指数权重同步及 Broken Pipe 自动重连。 | 256MB | [baostock-api 详情](docs/architecture/02c_数据采集微服务.md) |
| **pywencai-api** | `8002` | **同花顺问财 NLP 选股**：集成 Node 环境，提供自然语言选股和主题标签获取，实施严格限流器（~10 req/min）与指数退避重试。 | 512MB | [pywencai-api 详情](docs/architecture/02c_数据采集微服务.md) |
| **akshare-api** | `8003` | **AkShare 丰富行情源**：提供财务报表、个股异动快照、业绩预告和直爬同花顺发行价补全服务。 | 256MB | [akshare-api 详情](docs/architecture/02c_数据采集微服务.md) |
| **stock-manager-api** | `8004` | **数据管理中台**：全局元数据同步协调、交易日历计算状态、审计报告汇总与任务编排中继站。 | 192MB | [Stock Manager 规范](docs/api/STOCK_MANAGER_API.md) |
| **tushare-api** | `8005` | **Tushare P0 级接口**：标准化 REST 服务，保障主力数据源获取与高频流控安全。 | 128MB | [Tushare API 需求规格](docs/spec/云端数据源API需求规格.md) |
| **monitor-service** | `8006` | **情绪与评分监控**：进行市场温度评分、国债收益率 ERP 指标计算、个股异动得分与 L8 信号生成。 | 256MB | [度量指标规范](docs/standards/TABLES_INDEX.md) |
| **mootdx-api** | `8007` | **通达信直连行情**：基于 TCP 直连通达信服务器，提供盘中极速 Tick 级高频成交分笔与实时快照。 | 256MB | [高频分流设计](docs/architecture/01_体系架构总览.md) |
| **scf-collector** | (云函数) | **Serverless 采集集群**：云端无服务器采集器，负责盘后 16:30 行情同步、因子变动点提取与就绪信号发布。 | ≤128MB | [已落地采集清单](scf-collector/docs/done-list-tables.md) |

---

## 📊 核心技术特性

### 1. 三层数据模型重构 (ODS -> DWD -> ADS)
系统打破了以往高冗余的存储架构，建立起逻辑严密的不可变模型：
*   **ODS 原始层 (`stock_kline_daily`)**：只存交易所未复权原始 OHLC 数据，主键 `(ts_code, trade_date)`。**写入后永不被篡改**，确保历史物理真实。
*   **维度因子层 (`stock_adjust_factor`)**：采用**变动点模式**（仅在发生分红除权时产生新记录），极大缩减冗余行，降低库体积。
*   **内嵌复权因子设计**：在日线表 `stock_kline_daily` 中直接新增 `adj_factor` (累积后复权因子) 字段。在每日盘后同步时一次性合并写入，彻底消除大批量历史回测和概念股扫描时的庞大 JOIN 开销。
*   **高性能复权视图 (`v_stock_kline_forward_adj`)**：专为 **MySQL 5.7** 深度优化，使用高效关联子查询 (Correlated Subquery) 替代窗口函数，在 **0.02 秒内**快速完成全市场标的前/后复权价动态计算。

### 2. 多源数据质控与自愈闭环 (Data Healing Engine)
系统实现了一套像素级、无死角的自动化数据质量自愈闭环（Epic E12）：
*   **全量空洞检测 (`kline_integrity_checker.py`)**：基于 Daily Chunking 内存优化策略，自动比对 meta_trading_calendar 巡检 1991 年至今的全部个股日线空洞。
*   **三源对账仲裁**：自动在 Tushare (P0)、BaoStock (P1)、AkShare (P2) 之间进行跨源核对，自动过滤已知停牌交易日，定位脏数据与因子盲区。
*   **事件驱动式自愈**：发现缺失后自动触发自愈任务入队 `meta_task_queue`，`AutoRepairWorker` 异步极速拉取权威源进行合并修复，实现历史数据的 100% 无死角覆盖。

### 3. SCF 部署与二进制安全性门禁 (Binary Integrity)
针对腾讯云无服务器云函数 (SCF) 的只读与 Linux 运行环境限制，部署流水线制定了极其严苛的二进制平台审计（[scf-deployment](.agents/skills/scf-deployment/SKILL.md)）：
*   **安全构建工具 (`scripts/scf_build_tool.py`)**：强制指定 `--platform manylinux2014_x86_64` 与 `--only-binary=:all:` 环境，保障平台一致性。
*   **Windows binary 零容忍**：在打包过程中如果审计发现任何代表 Windows 平台编译的 `.pyd` 文件，构建将立即阻断并强行报错，彻底杜绝云端环境不可用隐患。

---

## 📦 部署与测试指南

### 1. 云端一键启动
在已配置好 `.env` 环境变量的腾讯云服务器中，执行以下指令快速拉起微服务集群：
```bash
# 启动微服务集群 (守护进程)
docker compose up -d

# 查看各容器健康检查状态
docker compose ps
```

### 2. 自动化质量验证 (QC)
修改或回填数据后，必须在 Docker 容器内部执行自动化回归测试，确保业务逻辑安全：
```bash
# 运行完整单元测试
pytest tests/

# 运行针对特定 Epic / 接口的精度核对脚本
python scripts/testing/verify_stocks_precise.py
```

### 3. 数据回填与疗愈
手动修复缺失数据或历史追溯时，可执行以下高性能批处理脚本：
```bash
# 一次性回填历史缺失的累积复权因子 (覆盖全历史)
python scripts/backfill/backfill_adj_factor.py
```

---

## 📜 开发者整洁规范 (AGENTS.md 硬红线)

为了保障代码仓长期可维护，共同协作时必须无条件遵守以下开发门禁：
1.  **根目录整洁规范 (Strict Root Dir Governance)**：根目录禁止创建任何不在白名单内的临时、测试或一次性文件。所有的临时代码必须存放在各微服务下的 `scratch/` 目录中，跨服务调试存放于 `scratch/history/`。
2.  **A 股口径统一**：
    *   全库禁止使用 `stock_code` 或 `dt`，必须统一使用 `ts_code` (如 `600519.SH`) 和 `trade_date` (如 `2026-05-15`)。
    *   涨跌幅 `pct_chg` 必须在采集层除以 100，全系统一律存储**小数**（如 0.0987 代表 9.87%）。
    *   成交额 `amount` 一律统一为**元**。
3.  **Docs-First 原则**：微服务的专属需求、设计与实施日志，**必须**物理存放于该微服务下的 `docs/features/{feature_name}/` 目录中。
4.  **HTML 门户同步**：所有新完成的设计、技术报告，在输出 `.md` 的同时，必须额外生成对应的 `.html` 副本，并运行 `python scripts/update_docs_portal.py` 同步全局与局部文档导航。

---

## 📚 体系文档索引

请参阅以下精简的工程文档以获得深度开发指导：

*   **架构蓝图**：
    *   [01. 混合云体系架构总览](docs/architecture/01_体系架构总览.md) — 了解 IO 云端仓与内网算力中心的物理网络交互与存储分层。
    *   [02. 云端微服务架构说明](docs/architecture/02_云端服务与API.md) — 包含 Nginx 网关、BFF 聚合层与数据就绪契约细节。
*   **数据库与口径标准化**：
    *   [全库数据表元数据总览 (TABLES_INDEX.md)](docs/standards/TABLES_INDEX.md) — 全局跨章节快速定位表、字段主键、高频引用及单位陷阱。
    *   [已落地云端数据表清单](scf-collector/docs/done-list-tables.md) — 已实现生产就绪的 meta 维表与交易行情表清单。
*   **数据模型重构与自愈**：
    *   [日线表内嵌复权因子设计方案](scf-collector/docs/features/kline_management/design/Adjfactor-in-klineDaily.md) — 了解 ODS 价格字段与累积后复权因子的物理合并设计。
    *   [补数与数据修复闭环设计 (E6)](docs/design/数据管线/历史数据校验体系/E6_补数与修复闭环.md) — 详解级联失效、重算信号以及 `meta_task_queue` 逻辑。
