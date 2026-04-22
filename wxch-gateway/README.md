# WXCH Gateway (微信云托管网关)

## 概述
本服务是专为微信小程序设计的 API 网关与数据接口服务。它运行在微信云托管环境，直接连接腾讯云 MySQL 数据库，提供高性能、低延迟的股票数据访问。

## 核心功能
- **个股 K 线接口**: 提供标准化的日 K 线数据查询。
- **自动格式标准化**: 兼容多种股票代码输入格式（如 `600519.SH`, `sh.600519`）。
- **云原生集成**: 深度集成微信云托管日志、请求追踪与环境变量管理。

## 快速开始

### 本地开发
1. 安装依赖: `pip install -r requirements.txt`
2. 配置环境变量: 创建 `.env` 文件并填入数据库连接信息。
3. 启动服务: `uvicorn app.main:app --reload`

### 部署
- 提交代码至 Gitee/GitHub 触发微信云托管流水线。
- **务必**在云托管控制台配置环境变量：`DB_HOST`, `DB_USER`, `DB_PASSWORD` 等。

## API 文档
- **详细调用指南**: 请参考 [docs/api/WXCH_GATEWAY_USAGE.md](../../docs/api/WXCH_GATEWAY_USAGE.md)
- **交互式文档**: 启动服务后访问 `/docs`

## 技术栈
- FastAPI
- aiomysql (异步连接池)
- Pydantic v2
- python-json-logger
