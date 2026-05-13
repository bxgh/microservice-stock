# [Epic E7] SCF 采集链路可靠性与审计校验增强

**文档 ID**: E7-DESIGN-01  
**状态**: 待实施 (Pending)  
**关联模块**: `scf-collector` (腾讯云环境)

---

## 1. 业务背景 (Background)

随着行情数据深度参与量化计算，数据源的“不完整性”和“不确定性”成为下游计算（Node-41）最大的风险点。为了确保数据采集不仅“能跑通”，而且“可审计、高一致”，需要对现有采集逻辑进行可靠性重构。

---

## 2. 核心目标 (Epic Goals)

1. **时政判定**: 明确 17:00 为 Tushare 数据就绪的强制判定点，实现“全量或无”的 Fail-over。
2. **存证体系**: 建立“影子审计”机制，在日常运行中留存备份源（AkShare）的精度与完整性校验报告。
3. **字段契约**: 确保任何源的数据在入库前必须通过“字段完整性模型”，包含必要的派生计算补全。

---

## 3. 用户故事 (User Stories)

### ### E7-S1: 基于死线的全量降级逻辑 (17:00 Fail-over)

**作为** 数据管线，**我希望** 在 17:00 判定主源（Tushare）是否达到 99% 的覆盖率，**以便于** 在主源不可信时立即全量切换到备份源，保障数据一致性。

#### 任务 (Tasks)
- [/] **E7-S1-T1**: 实现 `meta_universe_snapshot` 逻辑，在 09:30 锁定当日理论应采总数 $N$ (需包含停牌数据对冲)。
- [ ] **E7-S1-T2**: 修改 `daily_quotes` 触发时机为 17:00。
- [ ] **E7-S1-T3**: 编写 `validate_batch_integrity` 函数，对比 Tushare 返回量与 $N$ 值。
- [ ] **E7-S1-T4**: 实现“熔断切换”逻辑：若 Tushare 校验失败，彻底丢弃其批次，启动备份源全量采集。

#### 验收标准 (AC)
- **AC1: 基准锁定 (含停牌对冲)**
  - **Given** 09:30 触发二次元数据增强同步
  - **When** 采集当日 `suspend_d` 并与 `stock_basic` 进行关联计算
  - **Then** 数据库记录当日 `expected_count` 为当日上市且未停牌股票总数。
- **AC2: 故障切换**
  - **Given** 17:00 触发采集，Tushare 由于接口限流仅返回 1000 条（$N \approx 5300$）
  - **When** 触发校验逻辑
  - **Then** 系统记录日志 `[CRITICAL] Tushare integrity check failed (18.8%). Switching to AKSHARE.` 并执行全量补齐。

---

### ### E7-S2: 影子审计与校验证据 (Shadow Audit Evidence)

**作为** 系统管理员，**我希望** 即使在主源正常时，也能定期看到备份源与主源的差异报告，**以便于** 证明备份源在关键时刻具备接管能力。

#### 任务 (Tasks)
- [ ] **E7-S2-T1**: 创建 `meta_data_audit_log` 表，用于存储单次采集的对账摘要。
- [ ] **E7-S2-T2**: 编写 `ShadowAuditJob` 脚本，同时拉取 Tushare 和 AkShare 数据进行字段级对比。
- [ ] **E7-S2-T3**: 自动化产出 Markdown 审计报告，存储于 `docs/audit/` 目录。

#### 验收标准 (AC)
- **AC1: 审计证据可见**
  - **Given** 每周三/周六 20:00 触发影子任务
  - **When** 任务执行完毕
  - **Then** 在 `docs/audit/` 目录下生成 `source_reliability_report.md`，包含 `close`, `amount` 等字段的平均误差分析。

---

### ### E7-S3: 字段完整性契约强制 (Data Contract)

**作为** 下游计算节点，**我希望** 无论数据来自哪个源（Tushare/AkShare），入库字段必须 100% 完整且量纲一致，**以便于** 避免因字段缺失或单位错误导致的均线计算及量价分析报错。

#### 任务 (Tasks)
- [ ] **E7-S3-T1**: 在 `shared/collectors/base.py` 中定义 `KLineModel` 强类型契约，作为唯一入库标准。
- [ ] **E7-S3-T2**: 开发 **AkShare Adapter (适配层)**，实现 `stock_zh_a_spot_em` 字段的原子级转换：
    - **代码补全**: 自动将 6 位纯数字代码（如 `600519`）重构为标准 `ts_code` 格式（如 `600519.SH`）。
    - **单位换算**: 强制将 AkShare 的 `成交量`（单位：股）除以 100 转换为“手”；确保 `成交额` 单位统一为“元”。
    - **昨收提取**: 优先提取接口自带的 `昨收` 字段，确保 `pct_chg` 的计算基准与主源一致。
- [ ] **E7-S3-T3**: 实现 **停牌与无效数据清洗 (Cleaner)**：
    - 若 `今开`, `最高`, `最低` 均为 0 或成交量为 0，判定为当日停牌，标记为无效记录，防止其进入 `ods` 层。
- [ ] **E7-S3-T4**: 增加 **字段合成器 (Field Synthesizer)** 兜底逻辑：若备份源物理缺失 `pre_close`，则通过 `close / (1 + pct_chg)` 强制反推补齐。

#### 验收标准 (AC)
- **AC1: 字段量纲一致性**
  - **Given** AkShare 返回成交量为 `500` (股)
  - **When** 经过 Adapter 归一化
  - **Then** `KLineModel.volume` 值为 `5.0` (手)，与 Tushare 存储口径完全对齐。
- **AC2: 代码格式重构**
  - **Given** 备份源返回代码为 `300750`
  - **When** 经过适配层
  - **Then** `ts_code` 必须为 `300750.SZ`。
- **AC3: 停牌过滤生效**
  - **Given** 某股票当日停牌，接口返回成交量为 `0`
  - **When** 进入校验层
  - **Then** 该条记录被拦截，不执行 INSERT 操作，审计日志记录一条 `Skipped (Suspended)`。

## 4. 数据采集率统一口径规范 (Unified Collection Rate Standard)

为确保主备源切换及数据就绪判定具备客观依据，特制定本统计规范。

### 4.1 基准分母 (Universe Denominator)
- **定义**: 当日全 A 股理论应采实体池。
- **数据源**: 以当日 09:20 录入的 `stock_basic_info` 表快照为准。
- **过滤条件**: 
  - `list_status = 'L'` (上市中)
  - `list_date <= {trade_date}` (已上市)
  - 排除状态为 'D' (退市) 或 'P' (暂停上市) 的品种。

### 4.2 计算公式 (Calculation Formula)
采用“停牌对冲”后的真实覆盖率算法：

$$R_{final} = \frac{Count(M_{received} \cup M_{suspended})}{Count(Universe_{baseline})}$$

其中：
- $M_{received}$: 主源成功返回且通过字段契约校验的去重代码集合。
- $M_{suspended}$: 当日处于停牌状态（参考 `ods_suspend_d` 表）且主源未返回记录的代码集合。

### 4.3 判定阈值与响应策略
| 覆盖率范围 ($R$) | 质量判定 | 调度动作 |
| :--- | :--- | :--- |
| **$R \ge 99.5\%$** | **完美 (Perfect)** | 立即更新 `meta_data_readiness` 为 READY，触发下游计算。 |
| **$98\% \le R < 99.5\%$** | **正常 (Normal)** | 记录 Missing 列表，标记 READY，次日凌晨执行二次补录。 |
| **$95\% \le R < 98\%$** | **风险 (Warning)** | 触发“成分股探测”：若缺失包含沪深 300 成分股，立即切换备份源；否则警告并通过。 |
| **$R < 95\%$** | **失效 (Critical)** | **一票否决**：判定主源整批不可信，立即丢弃数据并启动全量全字段 Fail-over 流程。 |

### 4.4 存证要求
每次采集任务必须在 `meta_data_audit_log` 中记录：
1. `expected_n`: 基准总数。
2. `actual_m`: 实采数。
3. `diff_list`: 缺失代码列表（JSON）。
4. `source_tag`: 最终采纳的数据源（如 `TUSHARE_P0` 或 `AKSHARE_P1_FAILOVER`）。

---

## 5. 维护记录

- **2026-05-13**: [Antigravity] 根据“17:00 死线、全量切换、常态化审计”原则初版设计。
