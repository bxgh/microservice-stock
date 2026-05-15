# Epic E11: 文档体系标准化：基于功能领域的层级重构

> **Version**: v1.1  
> **Date**: 2026-05-15  
> **Status**: Approved

## 变更记录 (Change Log)

| 日期 | 版本 | 事件 |
|---|---|---|
| 2026-05-15 | v1.0 | 初始设计产出 |
| 2026-05-15 | v1.1 | 人工评审通过，新增 `scf-collector` 目录整理任务 |

---

## 1. 背景

随着项目功能的快速迭代，现有的文档存放方式（按文件类型散落在 `docs/` 或 `implementation_logs/` 下）导致功能相关的资产碎片化。开发者难以在同一目录下获取某个功能的完整上下文（设计、评审、日志）。本 Epic 旨在推行“以功能为核心”的目录重构，建立职责分明的业务领域映射体系。

## 2. 设计规范

重构后的文档树将遵循业务模块化原则，实现从“文件类型导向”到“功能逻辑导向”的转变。

### 2.1 微服务局部结构 (Local Feature View)

每个微服务的 `docs/` 目录下建立 `features/` 文件夹，按具体功能模块进行二层隔离：

```text
{service}/docs/features/
└── {feature_name}/          # 示例: kline_sync (K线同步功能)
    ├── design/              # 存放 draft_E{N}.md 和 .json (设计稿)
    ├── reviews/             # 存放 review_E{N}.html (评审记录)
    └── implementation_logs/ # 存放 E{N}-S{M} 的实施报告及 API.md
```

### 2.2 全局领域视图 (Global Domain View)

根目录 `docs/` 演进为项目的业务版图：

```text
docs/
├── domains/                 # 业务领域分类
│   ├── data_hub/            # 数据采集与存储领域
│   ├── quant_engine/        # 量化计算与策略领域
│   └── infrastructure/      # 基础设施（如门户自动化、监控）
└── standards/               # 技术标准与全局规约 (如 TABLES_INDEX.md)
```

---

## 3. Epic 拆解

### E11-S1: SOP 规约与 Agent 硬约束更新
**角色**: Requirement Architect  
**需求**: 在 `AGENTS.md` 中定义全新的功能目录强制约束。  
**价值**: 确保后续所有开发活动从创建目录开始就符合功能隔离原则。

#### 任务
- [ ] **E11-S1-T1**: 更新 `AGENTS.md` 第 5 节，明确 `{feature_name}` 目录层级要求
- [ ] **E11-S1-T2**: 更新 `epic-story-doc` 技能指令，支持自动识别/建议功能路径

#### 验收标准 (AC)
- **AC1 (规约覆盖)**: 
  - **Given**: `AGENTS.md` 已更新
  - **When**: 查看“文档归口原则”章节
  - **Then**: 必须明确提及 `docs/features/{feature_name}/` 这一层级结构

---

### E11-S2: 门户自动化脚本深度扫描适配
**角色**: DevOps Engineer  
**需求**: 升级 `update_docs_portal.py` 使其能识别功能目录并自动打标。  
**价值**: 在门户页自动按功能模块分组展示文档，提升搜索效率。

#### 任务
- [ ] **E11-S2-T1**: 修改扫描算法，识别 `features/` 下的二级目录名作为 Feature Tag
- [ ] **E11-S2-T2**: 更新 HTML 模板，增加按功能分组渲染的逻辑
- [ ] **E11-S2-T3**: 根据最新要求整理 `scf-collector/docs` 目录

#### 验收标准 (AC)
- **AC1 (功能打标验证)**: 
  - **Given**: 存在 `features/kline_sync/` 目录且内含 HTML 文档
  - **When**: 运行门户更新脚本
  - **Then**: HTML 页面中的文档标签应显示为 `[KLINE_SYNC]`（自动转大写）而非通用的 `[SCF-COLLECTOR]`

---

## 4. 风险管理

| 风险描述 | 影响 | 概率 | 缓解措施 |
|---|---|---|---|
| 存量文档迁移风险 | 中 | 高 | 采用分步迁移策略，优先对核心微服务进行重编，其他服务逐步跟进。 |
| 脚本路径兼容性 | 高 | 中 | 在更新脚本时增加对新旧路径的兼容，确保迁移期间门户不挂掉。 |

## 5. 里程碑 (Milestones)

- **M1: 结构规范入规** (2026-05-15): `AGENTS.md` 更新完成
- **M2: 脚本能力升级** (2026-05-15): 支持功能目录自动识别的更新脚本就绪
- **M3: 核心服务迁移** (2026-05-15): `scf-collector` 等核心服务完成功能目录重构
