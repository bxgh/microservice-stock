# WXCH Gateway: 微信云托管 API 网关与服务手册

## 1. 文档索引 (Documentation Index)

- **核心 API 调用指南**: [docs/api/WXCH_GATEWAY_USAGE.md](../../docs/api/WXCH_GATEWAY_USAGE.md) (接口参数、响应示例与小程序接入)
- **股市日记 API 规格说明书**: [docs/api/api-spec-diary.md](../../docs/api/api-spec-diary.md) (股市日记功能专用)
- **全局数据库字典**: [docs/standards/TABLES_INDEX.md](../../docs/standards/TABLES_INDEX.md) (数据实体物理对照)

---

## 2. 系统角色与架构

`wxch-gateway` 是 A 股盘后分析系统的“用户侧网关”，运行在 **微信云托管 (WeChat CloudBase)** 生产环境下。

- **核心职责**: 
  - 为微信小程序客户端提供高并发、低延迟的 A 股股票数据 API。
  - 处理微信静默登录与 JWT 鉴权管理。
  - 为敏感操作（如股市日记写入与读取）提供异步数据库连接池支持。
  - 执行客户端请求的字段规范化与异常脱敏，防止后端堆栈信息外泄。
- **物理边界**: 运行于腾讯云 Serverless 容器环境，通过云托管 VPC 直连腾讯云内网 MySQL 5.7 数据库 (`172.17.0.10`)，绝不直接处理大内存高吞吐的数据采集或量化计算任务（耗时及重计算任务均通过消息队列接力至内网服务器）。

### 2.1 目录结构

服务设计与开发遵守 `AGENTS.md` 的规范：
```
wxch-gateway/
├── app/                  # FastAPI 核心业务逻辑
│   ├── api/              # API 路由与控制器 (v1)
│   ├── core/             # 系统核心配置与安全策略
│   ├── db/               # 异步数据库连接池 (aiomysql)
│   └── models/           # Pydantic v2 数据模型与校验
├── docs/                 # 文档资产区
│   ├── readme.md         # 本手册
│   └── features/         # 微服务专属特征目录
│       └── wechat-gateway/
│           ├── design/   # 详细设计稿 (Epic/Story Drafts)
│           ├── reviews/  # 设计评审与反馈记录
│           └── implementation_logs/ # 实施日志与对账存证
└── scripts/              # 辅助运维与本地测试脚本
```

---

## 3. 核心 API 服务矩阵

本网关提供以下五大核心数据服务模块，全部遵循 `/api/v1/` 统一路由前缀：

### 3.1 行情服务 (Quotes Engine)
- **个股日 K 线**: `GET /api/v1/stocks/{code}/kline` (支持多格式代码转换，支持复权选择)
- **实时五档快照**: `GET /api/v1/stocks/{code}/snapshot` (买卖盘口、估值指标与市值)
- **个股当日分时**: `GET /api/v1/stocks/{code}/time_share` (当日分时点阵与均价)

### 3.2 深度基本面服务 (Deep Fundamentals)
- **业绩基本面**: `GET /api/v1/stocks/{code}/fundamentals` (机构评级与业绩预告)
- **财务季报**: `GET /api/v1/stocks/{code}/financials` (核心利润表与 ROE 衍生指标)
- **股权变动**: `GET /api/v1/stocks/{code}/shareholders` (历史股东户数与十大股东)

### 3.3 用户与鉴权服务 (Auth & User Profile)
- **静默登录**: `POST /api/v1/auth/login` (微信临时凭证无感登录，生成 JWT Token)
- **个性化配置**: `GET / PUT /api/v1/user/profile` (个人中心、护眼/长辈模式与配置持久化)

---

## 4. 运维与测试指南

### 4.1 本地测试运行
在本地开发环境下，可使用虚拟环境并一键启动：
```bash
# 1. 安装项目依赖
pip install -r requirements.txt

# 2. 配置环境变量
# 拷贝模板并填写腾讯云数据库直连信息
copy .env.example .env

# 3. 启动 FastAPI 热重载服务
uvicorn app.main:app --host 0.0.0.0 --port 8006 --reload
```

### 4.2 自动化质量控制 (QC)
上线部署前，必须在本地 Docker 沙盒中完成接口联调与防劣化回归测试：
```bash
# 执行 API 联调流水线校验
python scripts/testing/test_api_flow.py
```

### 4.3 微信云托管部署
服务已集成持续集成（CI）流水线：
1. **代码合并**: 将开发完成的 Story 代码合并至主分支 `feat/wxch-gateway` 或 `master`。
2. **流水线触发**: 提交推送至 Gitee 触发腾讯云托管自动化 Docker 镜像构建。
3. **安全审计**: 构建机自动审计环境兼容性，拒绝任何不合规依赖包。
4. **灰度发布**: 云托管控制台自动执行滚动灰度发布，确保用户侧无白屏影响。

---

**交付记录**:
- **服务状态**: 🟢 活动中 (Active) · 微信云托管生产就绪
- **最新版本**: v1.2.0
- **主要维护人**: Antigravity AI
- **最后更新日期**: 2026-05-18
