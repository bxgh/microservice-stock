# Walkthrough: E100-S2 WXCH 网关治理角色

## 1. 变更说明
针对 `wxch-gateway` 的特殊运行环境和业务场景，建立了专有的治理角色 `[Gateway Guardian]`，并强化了安全与性能红线。

### 关键证据 (Physical Evidence)

#### 1.1 新增 [Gateway Guardian] 角色
在 `ROLES.md` 中成功定义了网关专用角色，涵盖身份校验、信息脱敏、负载控制等核心禁令。

#### 1.2 WXCH 环境适配
在 `[Infra Specialist]` 中增加了关于微信云托管环境变量和内网域名的强制要求。

#### 1.3 反模式同步
`AGENTS.md` 已同步增加“网关暴露敏感堆栈信息”的反模式，确保全域认知一致。

## 2. 验证结论
通过本次更新，`wxch-gateway` 的开发将具备更强的防御性约束。后续在修改网关代码时，Agent 必须通过激活该角色来确保 API 的安全性和移动端体验。

---
**验收状态**: ✅ 已通过自检
**激活角色**: [Workflow Guard] 已确认物理存证完整。
