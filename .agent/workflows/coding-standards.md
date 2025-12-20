---
description: 股票数据源微服务开发规范 - 编码时自动应用
---

# 开发规范

## 技术栈
- Python 3.12+
- FastAPI (必须)
- 基础镜像: python:3.12-alpine
- 内存限制: ≤128MB

## 异步规范
- **必须** 使用 `async/await` 处理所有 I/O
- **禁止** 使用阻塞同步调用 (requests, time.sleep)
- 共享状态使用 `asyncio.Lock()` 保护

## 日志规范
- JSON 格式输出
- **必须** 包含 `request_id` 字段
- 使用 `Asia/Shanghai` 时区

## API 规范
- 路由前缀: `/api/v1/`
- 健康检查: `GET /health` → `{"status": "healthy"}`
- 超时: 30秒
- 错误格式:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "描述",
    "request_id": "xxx"
  }
}
```

## 错误处理
- **禁止** 捕获裸 `Exception`
- 使用特定异常: `TimeoutError`, `ValueError` 等
- 日志记录上下文: 函数名、参数、错误详情

## 资源管理
- 服务类实现 `initialize()` 和 `close()` 方法
- **必须** 使用 `try...finally` 确保资源释放
- 优先使用 `async with` 上下文管理器

## PyWencai 特殊处理
- 频率限制: ~10次/分钟
- 预期失败率: 30%
- 必须实现重试机制 (MAX_RETRIES=3)

## 测试要求
- 框架: pytest + pytest-asyncio
- 必测: 健康检查、正常流程、异常处理

## Git 提交
- 使用 Conventional Commits: feat/fix/docs/test/refactor
