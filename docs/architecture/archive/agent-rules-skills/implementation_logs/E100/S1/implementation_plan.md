# Implementation Plan - E100-S1: AGENTS.md 升级与规约解耦

本项目旨在将 `AGENTS.md` 升级至 v1.2，通过将技术规约剥离至 `.agent/rules/` 目录，降低文档复杂度，并建立严格的根目录治理体系。

## User Review Required

> [!IMPORTANT]
> - 本次变更将移动 `AGENTS.md` 中的部分技术细节（如并发锁、熔断器等）到新创建的 `.agent/rules/python-coding-standards.md`。
> - 将引入“根目录准入白名单”，Agent 以后将严禁在根目录创建临时文件。

## 架构溯源与风险认证
- **架构模式**: 模块化治理体系。
- **保障机制**: 通过思维链显式激活 `[Workflow Guard]` 角色，并在交付前执行物理清理。
- **激活角色**: `[Workflow Guard]`, `[Infra Specialist]`

## 需求解析 (Readiness Check)
- **业务位置**: 属于系统级治理升级。
- **核心逻辑**: 迁移 -> 适配 -> 重构 -> 校验。
- **依赖认证**: 已克隆 `microservice-stock-ck` 仓库，具备源码参考条件。
- **TBD 销账**: 无。

## Proposed Changes

### 规约解耦与适配

#### [NEW] [.agent/rules/python-coding-standards.md](file:///home/ubuntu/microservice-stock/.agent/rules/python-coding-standards.md)
- 从 41 服务器迁移并适配。
- 重点保留：并发锁 (asyncio.Lock)、熔断与重试、时区规范、资源清理 (try...finally)。

#### [MODIFY] [AGENTS.md](file:///home/ubuntu/microservice-stock/AGENTS.md)
- 升级版本号至 `v1.2`。
- 移除 Section 6.2 中的技术冗余（已下沉至 python-coding-standards.md）。
- 增加 Section 3.4 “根目录整洁规范”。
- 完善 Section 9.1 “具体实施流程”，加入 Docs-First 和角色激活要求。

### 根目录治理

#### [MODIFY] [AGENTS.md](file:///home/ubuntu/microservice-stock/AGENTS.md) (Section 3.4)
- 定义白名单：`akshare-api`, `baostock-api`, `docs`, `scripts`, `stock-manager-api` 等核心目录。
- 规定临时文件重定向规则。

## Verification Plan

### Automated Tests
- 无需代码运行，通过 Agent 自审白名单符合性。

### Manual Verification
- 检查 `AGENTS.md` v1.2 的引用链路是否正确跳转至 `.agent/rules/python-coding-standards.md`。
- 验证 Agent 是否能准确识别根目录违规文件并报错。
