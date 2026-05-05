# Microservice Stock Data System

本项目是一个高度解耦的股票数据采集微服务集群，将不同的数据源（AkShare, BaoStock, PyWencai）封装为独立的微服务提供统一的 RESTful API。

## 🚀 快速开始

### 核心服务端口
- **8000**: [Stock Dictionary](docs/architecture/架构设计.md#31-akshare-api-8000) (股票词典)
- **8001**: [BaoStock API](docs/architecture/架构设计.md#32-baostock-api-8001) (历史数据 & MySQL 同步)
- **8002**: [PyWencai API](docs/architecture/架构设计.md#33-pywencai-api-8002) (语义选股)
- **8003**: AkShare API (实时行情/财务)
- **8004**: [Stock Manager](docs/design/数据管线/历史数据校验体系/E6_补数与修复闭环.md) (数据管理中台)
- **8005**: Tushare API (主力数据源 P0)

### 📊 数据持久化与质量闭环
- **BaoStock -> MySQL**: 支持全市场 A 股 K 线数据的自动化同步。
- **E6 补数与修复**: 基于 Tushare(P0) + AkShare(P2) 的自动化数据修复流水线，支持审计回溯与级联失效处理。
- **特性**: 支持断点续传、增量更新、后台异步索引、全链路数据审计。

### 部署
```bash
docker compose up -d
```

## 📚 文档指南
详细文档请参阅 [docs/README.md](docs/README.md)。

- [架构设计](docs/architecture/架构设计.md)
- [数据获取架构](docs/architecture/DATA_ACQUISITION_ARCHITECTURE.md)
- [开发规范](docs/guidelines/开发规范.md)
- [API 需求规格](docs/spec/云端数据源API需求规格.md)

## 🛠️ 运维与测试
测试脚本位于 `./scripts/testing/` 目录下。
运维工具位于 `./scripts/` 目录下。
