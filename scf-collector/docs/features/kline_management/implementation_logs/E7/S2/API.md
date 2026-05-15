# 接口定义 - E7-S2: Shadow Audit 操作标准

## 1. 影子审计触发 (op: shadow_audit)
用于对比主源入库数据与实时备份源数据的完整性与准确性。

### 1.1 输入参数 (JSON Payload)
| 字段 | 类型 | 必选 | 说明 |
| :--- | :--- | :--- | :--- |
| `op` | string | 是 | 固定值: `shadow_audit` |
| `trade_date` | string | 否 | 交易日期 (YYYY-MM-DD)，默认为当天 |

### 1.2 输出结果 (Response)
```json
{
    "status": "success",
    "audit": {
        "trade_date": "2026-05-13",
        "task_name": "ShadowAudit",
        "primary_source": "Tushare",
        "secondary_source": "AkShare(em)",
        "primary_count": 5493,
        "secondary_count": 5492,
        "overlap_count": 5492,
        "coverage_rate": 0.9998,
        "status": "PASS",
        "report_content": "# 影子审计报告...",
        "close_mae": 0.0,
        "volume_mae": 0.21876,
        "amount_mae": 0.029315,
        "pct_chg_mae": 0.000002
    },
    "request_id": "..."
}
```

## 2. 存证数据表 (meta_data_audit_log)
审计结果将自动写入此表，关键字段如下：
- `report_content`: 存储 Markdown 格式的完整审计报告。
- `status`: 存储最终判定结论 (PASS/WARNING/FAIL)。
- `close_mae`: 核心对账指标，决定最终状态。
