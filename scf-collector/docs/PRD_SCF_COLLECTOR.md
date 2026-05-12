# [PRD] Serverless 股票数据采集节点 (SCF Collector)

**文档 ID**: E6-PRD-01  
**版本**: v1.2 (2026-05-12)  
**状态**: 已就绪 (Ready for Staging)
**关联模块**: `scf-collector`

---

## 1. 业务背景 (Background)

为解决云端 ECS 资源受限、单点采集易被封禁以及固定任务调度缺乏弹性的问题，本项目将行情采集逻辑迁移至腾讯云 SCF (Serverless Cloud Function)。通过按需触发、多源回退的架构，构建一个高可用、零维护的数据接入层。

---

## 2. 核心目标 (Epic: E6)

构建一个“永不宕机”的股票数据抓取节点，支持四个以上数据源的自动切换，并确保产出数据严格符合 `stock_kline_daily` 物理表 Schema。

---

## 3. 功能需求 (User Stories & AC)

### ### E6-S1: 三级防线采集链路 (Fallback Chain)

**需求描述**: 作为数据管线，我希望在首选源失效时，系统能自动尝试备选源，确保采集成功率。

**验收标准**:
- **P0: Tushare (权威源)**：作为主数据源，提供最全的复权因子和基础财务字段。
- **P1: AkShare (强力源)**：具备“东方财富 + 新浪财经”双源自动切换，解决网络拦截问题。
- **P2: EasyQuotation (生存源)**：通过超轻量级 Web 接口（新浪/腾讯），在极端环境下保障收盘价不丢失。

### ### E6-S2: 数据标准化契约 (Data Normalization)

**需求描述**: 无论数据源如何切换，返回给数据库的结构必须保持一致。

**验收标准 (AC)**:
1. **代码格式**: `ts_code` 必须为 `600519.SH` 形式。
2. **量价单位**: 
   - `volume` (成交量): 统一转换为 **“手”** (Lot, 100股)。
   - `amount` (成交额): 统一转换为 **“元”** (Yuan)。
3. **涨跌幅**: `pct_chg` 统一为 **小数** (如 -0.015 代表 -1.5%)。
4. **幂等性**: 必须包含 `ON DUPLICATE KEY UPDATE` 逻辑，支持重复写入。

---

## 4. 技术规格 (Technical Specs)

### 4.1 运行环境
- **Runtime**: Python 3.10 (对齐腾讯云 SCF 标准环境)。
- **Memory**: 默认 128MB，推荐 256MB。
- **Timeout**: 30 秒。

### 4.2 审计与监控
- **状态记录**: 每次执行必须在 `meta_pipeline_run` 记录 `started_at`, `finished_at`, `status` (success/failed)。
- **数据就绪**: 成功后需在 `meta_data_readiness` 更新当日就绪标志，供下游计算节点识别。

---

## 5. 异常处理规范

1. **API 熔断**: 单次 API 调用失败不应崩溃，应记录 warning 并进入 Fallback。
2. **网络超时**: 全链路超时由 SCF 强制控制，应用层超时建议设为 10s 以留出 Fallback 时间。
3. **冷启动优化**: 核心 Collector 采用动态导入（Import inside function），减少冷启动延迟。

---

## 6. 维护记录 (Audit)

- **2026-05-12**: 初版发布 (v1.0)。
- **2026-05-12**: 增加 AkShare Fallback 逻辑及 EasyQuotation 兜底 (v1.2)。
