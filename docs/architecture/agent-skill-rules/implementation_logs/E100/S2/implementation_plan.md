# E100-S2: WXCH Gateway 专有治理角色与安全红线

> **激活角色**: [Requirement Architect], [Workflow Guard]
> **溯源**: 关联 `AGENTS.md` 1.1 节 (微服务边界) 及 `wxch-gateway/README.md`

## 1. 任务背景
`wxch-gateway` 运行于“微信云托管”环境，直接面向移动端用户。由于其环境的特殊性（Serverless、微信私有链路、OpenID 鉴权），通用的后端采集角色（如 `[Data Quality Steward]`）对其约束力不足。需要建立专有的安全与性能红线，防止敏感信息泄露并优化移动端体验。

## 2. 方案目标
- [ ] **新增角色**: 在 `ROLES.md` 中引入 `[Gateway Guardian]` 角色。
- [ ] **安全加固**: 定义 API 报错屏蔽规则，严禁泄露后端堆栈。
- [ ] **环境适配**: 在 `[Infra Specialist]` 中增加对微信云托管（WXCH）的专属描述。

## 3. 核心约束 (No-Go List 预览)
- **[Gateway Guardian]**:
    - ❌ **身份透传**: 严禁在未校验 `X-WX-OPENID` 的情况下返回用户私有数据。
    - ❌ **泄露堆栈**: 严禁在 `HTTP 500` 响应中包含 SQL 或 Traceback。
- **[Infra Specialist (WXCH)]**:
    - ❌ **静态 IP**: 严禁依赖固定 IP 进行连接，必须使用微信 VPC 内网域名。

## 4. 验收标准 (AC)

#### AC-1: 网关安全禁令生效
- **Given** 修改 `wxch-gateway` 目录下的控制器代码
- **When** 提交实施计划
- **Then** Agent 必须显示激活 `[Gateway Guardian]` 角色，并检查是否包含异常捕获与错误脱敏逻辑。

#### AC-2: 移动端数据负载约束
- **Given** 某个 API 涉及全量数据查询
- **When** 由 `[Gateway Guardian]` 审计
- **Then** 必须强制要求分页 (`limit`)，严禁单次返回超过 500 条原始数据。

## 5. 任务拆解
- [ ] **E100-S2-T1**: 更新 `ROLES.md`，添加第 8 个角色 `[Gateway Guardian]`。
- [ ] **E100-S2-T2**: 优化 `ROLES.md` 中 `[Infra Specialist]` 对 WXCH 环境的差异化描述。
- [ ] **E100-S2-T3**: 在 `AGENTS.md` 的反模式清单中增加“网关敏感信息泄露”。
