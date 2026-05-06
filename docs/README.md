# 项目文档索引 (Documentation Index)

本项目文档统一存放在 `docs/` 目录下，按以下分类进行组织：

## 🤖 AI 上下文知识库 (AI Context)
从 `.agent/context/` 迁入的核心参考文档，供 AI 助手和开发者快速检索。

| 文件 | 用途 | 优先级 |
|------|------|--------|
| [architecture.md](architecture.md) | 项目架构、服务职责、技术栈 | 🔴 必读 |
| [api-endpoints.md](api-endpoints.md) | API 端点清单 | 🔴 必读 |
| [data-sources.md](data-sources.md) | 数据源特性与异常处理 | 🟡 按需 |
| [troubleshooting.md](troubleshooting.md) | 故障排查手册 | 🟡 按需 |
| [code-templates.md](code-templates.md) | 代码模板与规范 | 🟡 按需 |
| [performance.md](performance.md) | 性能基线与监控 | 🟢 参考 |

## 🏗️ 架构设计 (Architecture)
包含系统整体架构、数据获取架构及核心设计决策。
- [系统整体架构设计](architecture/架构设计.md)
- [数据获取架构与开发指南](architecture/DATA_ACQUISITION_ARCHITECTURE.md)

## 📋 需求规格 (Specifications)
包含各类 API 的功能需求、数据项定义及 EPIC 级开发规格。
- [云端数据源 API 需求规格](spec/云端数据源API需求规格.md)
- [EPIC-002 详细数据项定义](spec/epic002需求数据.md)

## 📜 开发规范 (Guidelines)
包含代码风格、资源控制及协作流程定义。
- [通用开发规范](guidelines/开发规范.md)
- [资源控制与性能限制指南](guidelines/RESOURCE_CONTROL.md)

## 📊 评估与报告 (Reports)
包含功能的阶段性验收报告、数据匹配度评估及技术审计结论。
- [EPIC-002 数据源匹配度评估](reports/EPIC002_数据源匹配度评估.md)
- [集群功能验收报告 (2025-12-21)](reports/功能验收报告.md)

## 🛡️ 数据质量与校验 (Data Quality)
包含历史数据巡检、跨源比对及业务规则校验设计。
- [E1: 数据模型重构](design/数据管线/历史数据校验体系/E1_数据模型重构.md)
- [E2: 写入路径同步校验](design/数据管线/历史数据校验体系/E2_写入路径同步校验.md)
- [E3: 巡检模块独立部署](design/数据管线/历史数据校验体系/E3_巡检模块独立部署.md)
- [E4: 跨源比对](design/数据管线/历史数据校验体系/E4_跨源比对.md)
- [E5: 业务规则校验](design/数据管线/历史数据校验体系/E5_业务规则校验.md)

---
*最后更新: 2026-05-06*
