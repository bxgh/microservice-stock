# Implementation Plan - Deploy mootdx-api to Tencent Cloud [E101-S1]

## 1. 实施前准入 (Readiness Check)
- [x] **需求解析**: 将 `mootdx-api` 从外部仓库移植至腾讯云环境，移除内网代理并集成。
- [x] **依赖认证**: 已查实公网 TDX 节点连通性，MySQL 环境就绪，Redis 确定不启用。
- [x] **角色激活**: [Backend Architect], [DevOps Engineer].

## 2. 字段对齐矩阵 (Field Mapping Matrix)
遵循 5.4 节要求，API 输出与系统标准字段对齐如下：

| 逻辑字段 | Mootdx 字段 | 状态 | 单位/格式 |
| :--- | :--- | :--- | :--- |
| ts_code | code | ✅ | 6位数字字符串 |
| price | price | ✅ | 小数 |
| open | open | ✅ | 小数 |
| high | high | ✅ | 小数 |
| low | low | ✅ | 小数 |
| last_close | last_close | ✅ | 小数 |
| vol | vol | ✅ | 股 (需注意单位) |
| amount | amount | ✅ | 元 (已验证为元) |

## 3. 灰度先行策略 (Gray Deployment Strategy)
根据 5.4 节要求，实施三段式验证：
1. **样本测试**: 选取 10 只代表性个股（主板、创业板等）进行接口连通性测试。
2. **校验**: 检查 OHLC 逻辑、成交额量单位。
3. **全量**: 确认无误后交付 API 端点。

## 4. 实施细节

### 4.1 目录结构 [NEW]
- `mootdx-api/`: 微服务根目录。
- `mootdx-api/libs/gsd-shared/`: 移植核心共享库。
- `mootdx-api/src/`: API 源码。

### 4.2 容器化适配 [MODIFY]
- **Dockerfile**: 移除所有内网代理配置，优化国内镜像源。
- **docker-compose.yml**: 映射端口 `8007:8000`。
- **main.py**: 增加 `request_id` 追踪中间件（对齐 python-coding-standards.md）。

## 5. 验证计划

### 自动化测试
- `GET /health`: 连通性校验。
- `GET /api/v1/quotes`: 行情数据校验。

### 质量红线 (QC Redline)
- [x] 核心字段 (price, amount) 不允许为空。
- [x] 采样数据 (10只) 必须全部返回 200 OK。
- [x] 日志必须包含 `request_id`。
