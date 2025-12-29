# Scheduled Jobs API Specification (V1.2 Unified)

This document outlines the required endpoints for the "Jobs Management" module in the Microstock-Taro frontend. All requests are routed through the BaoStock gateway (`/api/v1/baostock/`).

## 1. Task Management (Cross-Container)

### 1.1 List All Jobs
Fetch a consolidated list of jobs from all containers (BaoStock, AkShare, PyWencai).

- **Endpoint**: `GET /api/v1/baostock/scheduler/jobs`
- **Response**:
```json
{
  "jobs": [
    {
      "id": "daily_kline_sync",
      "name": "日K同步",
      "container": "baostock-api",
      "trigger": "cron[0 17 * * 1-5]",
      "next_run_time": "2025-12-29 17:00:00",
      "status": "success" 
    },
    {
      "id": "ak_valuation_sync",
      "name": "估值同步",
      "container": "akshare-api",
      "trigger": "interval[24:00:00]",
      "next_run_time": null,
      "status": "paused"
    }
  ]
}
```

### 1.2 Job Control
Control specific jobs in specific containers.

- **Endpoint**: `POST /api/v1/baostock/scheduler/jobs/{job_id}/{action}?container={container_name}`
- **Parameters**:
  - `action`: `run` | `pause` | `resume`
  - `container`: Target service name (e.g., `akshare-api`, `pywencai-api`)
- **Success Response**: `{"status": "ok"}`

---

## 2. Sync Progress & Health Monitoring

### 2.1 Real-time Sync Status
Used for updating progress bars (e.g., in the Daily K-line Sync).

- **Endpoint**: `GET /api/v1/baostock/sync/status`
- **Response**:
```json
{
  "running": true,
  "current": 1200,
  "total": 5468,
  "current_code": "sh.600000",
  "start_time": "2025-12-27 17:01:23"
}
```

### 2.2 Daily Data Audit (V1.2)
Used for the "System Admin" completeness dashboard.

- **Endpoint**: `GET /api/v1/baostock/sync/verify/daily?date=YYYY-MM-DD`
- **Response**:
```json
{
  "date": "2025-12-27",
  "actual_count": 5200,
  "expected_count": 5465,
  "completeness_pct": 95.1,
  "status": "in_progress"
}
```

### 2.3 Weekly Sync History (V1.2)
Provides a list of counts for the current week's trading days, including both K-line data and adjust factor data.

- **Endpoint**: `GET /api/v1/baostock/sync/verify/weekly`
- **Response**:
```json
{
  "history": [
    { "date": "2025-12-22", "count": 5461 },
    { "date": "2025-12-23", "count": 5464 },
    { "date": "2025-12-24", "count": 5465 },
    { "date": "2025-12-25", "count": 5465 },
    { "date": "2025-12-26", "count": 5465 }
  ],
  "kline": [
    { "date": "2025-12-22", "count": 5461 },
    { "date": "2025-12-23", "count": 5464 },
    { "date": "2025-12-24", "count": 5465 },
    { "date": "2025-12-25", "count": 5465 },
    { "date": "2025-12-26", "count": 5465 }
  ],
  "adjust_factor": [
    { "date": "2025-12-22", "count": 4 },
    { "date": "2025-12-23", "count": 5 },
    { "date": "2025-12-24", "count": 8 },
    { "date": "2025-12-25", "count": 4 },
    { "date": "2025-12-26", "count": 3 }
  ]
}
```

**Note**: `history` field is provided for backward compatibility (same as `kline`). New frontend implementations should use `kline` and `adjust_factor` for clarity.

---

## 3. Proposed Enhancements (Action Items)

### 3.1 Job Log Stream & Summary
To replace raw logs with high-value information. Frontend polls this every 5 seconds.

- **Endpoint**: `GET /api/v1/baostock/scheduler/jobs/{job_id}/logs?container={container}&lines=50`
- **Response**:
```json
{
  "summary": "已处理: 546/5468, 正在同步: sh.600000, 预计剩余: 12分钟",
  "logs": [
    "[2025-12-27 17:05:01] [INFO] Starting sync",
    "[2025-12-27 17:05:05] [DEBUG] API status 200"
  ]
}
```
*Note: The `summary` field should contain a human-readable, concise status string extracted from the latest logs.*

### 3.2 Global Clean-up
Resetting all progress/buffers.

- **Endpoint**: `POST /api/v1/baostock/sync/reset`
- **Endpoint**: `POST /api/v1/baostock/sync/full` (Trigger manual catch-up)
