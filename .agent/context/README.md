```text
# Example Code Block
This is a placeholder for a code example.
```

# AI 上下文文档索引

> **用途**: AI 开发助手的快速上下文加载入口
> **更新时间**: 2026-01-07 10:30:00

## 文档列表

| 文件 | 用途 | 优先级 |
|------|------|--------|
| [01_ARCHITECTURE.md](01_ARCHITECTURE.md) | 项目架构、服务职责、技术栈 | 🔴 必读 |
| [02_API_ENDPOINTS.md](02_API_ENDPOINTS.md) | 25 个端点清单 | 🔴 必读 |
| [03_DATA_SOURCES.md](03_DATA_SOURCES.md) | 数据源特性与异常处理 | 🟡 按需 |
| [04_TROUBLESHOOTING.md](04_TROUBLESHOOTING.md) | 故障排查手册 | 🟡 按需 |
| [05_CODE_TEMPLATES.md](05_CODE_TEMPLATES.md) | 代码模板与规范 | 🟡 按需 |
| [06_PERFORMANCE.md](06_PERFORMANCE.md) | 性能基线与监控 | 🟢 参考 |

## 快速加载策略

### 场景: 新增端点
加载: `01_ARCHITECTURE.md` + `02_API_ENDPOINTS.md` + `05_CODE_TEMPLATES.md`

### 场景: 问题排查
加载: `01_ARCHITECTURE.md` + `04_TROUBLESHOOTING.md`

### 场景: 数据源集成
加载: `01_ARCHITECTURE.md` + `03_DATA_SOURCES.md`

### 场景: 性能优化
加载: `01_ARCHITECTURE.md` + `06_PERFORMANCE.md`

## 相关文档

- 项目规则: `../.antigravityrules`
- 开发规范: `../docs/guidelines/开发规范.md`
- 架构设计: `../docs/architecture/`
- 问题修复记录: `../docs/bugfix/`
