# API & Config Reference - E300-S1

## 1. 审计工具配置 (mapping_config.json)

审计工具使用 JSON 配置文件定义数据库表与 Tushare 接口的映射。

**路径**: `scripts/validation/mapping_config.json`

### 结构示例
```json
{
  "stock_kline_daily": { 
    "source": "tushare", 
    "api_name": "daily" 
  }
}
```

### 字段说明
| 字段 | 类型 | 说明 |
|---|---|---|
| `key` | string | 数据库表名 (ods_ / stock_ 开头) |
| `source` | string | 数据源名称 (目前固定为 tushare) |
| `api_name` | string | Tushare Pro 官方接口名称 |

## 2. 审计脚本调用

### 执行命令
```bash
python3 scripts/validation/field_mapping_audit.py
```

### 依赖环境
- `SQLAlchemy`: 数据库反射
- `Tushare`: 接口元数据获取
- `Pandas`: 数据结构处理
- `python-dotenv`: 环境配置加载
