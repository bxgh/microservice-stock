# [Epic E200] A 股自愈型数据管线实施方案

**关联 PRD**: [PRD-自愈型数据管线 v1.5](file:///home/ubuntu/microservice-stock/docs/design/数据管线/自愈管线/PRD-自愈型数据管线.md)
**当前状态**: 准入审计中
**实施主体**: [Data Quality Steward]

---

## ## E200-S1: 差异化跨源扫描器 (Scanner)
**描述**: 实现字段级差异化校验逻辑，集成 Mootdx 新源，建立三源仲裁的核心判定引擎。

#### 任务 (Tasks)
- [ ] **E200-S1-T1**: 集成 `mootdx-api` 客户端，封装历史 K 线获取接口。
- [ ] **E200-S1-T2**: 开发 `FieldLevelValidator` 逻辑，支持 OHLCV 及财务勾稽。
- [ ] **E200-S1-T3**: 实现“三取二”仲裁判定，输出修复建议记录。

#### 验收标准 (AC)
1. **Given**: Tushare(10.0), Mootdx(10.0), AkShare(9.5); **When**: 执行扫描; **Then**: 判定结果为 10.0，记录 AkShare 异常。
2. **Given**: 某源超时; **When**: 执行扫描; **Then**: 降级为双源比对并发出 WARN。

---

## ## E200-S2: 自动化修复与回滚引擎 (Healer)
#### 任务 (Tasks)
- [ ] **E200-S2-T1**: 建立 `meta_repair_log` 审计镜像存储。
- [ ] **E200-S2-T2**: 开发 `BackfillCoordinator` 对接补数服务。
- [ ] **E200-S2-T3**: 实现原子级一键回滚 API。

---

## ## E200-S3: 级联失效与同步阻塞 (Consistency)
#### 任务 (Tasks)
- [x] **E200-S3-T1**: 实现 Stage G 下游 ADS 视图清理信号。
- [x] **E200-S3-T2**: 开发 Stage F 阻塞同步等待 (ACK 机制)。

---

## ## E200-S4: 白名单与 SLA 监控 (Governance)
#### 任务 (Tasks)
- [ ] **E200-S4-T1**: 实现白名单强制过期逻辑 (5 交易日)。
- [ ] **E200-S4-T2**: 建立每日 SLA 自动化审计报告。
