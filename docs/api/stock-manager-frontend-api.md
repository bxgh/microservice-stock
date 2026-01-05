# Stock-Manager API 前端开发文档

> **服务版本**: v1.0  
> **更新日期**: 2026-01-01  
> **协议**: HTTP/HTTPS

---

## 基础信息

### 环境配置

#### 开发环境（本地调试）
```
Base URL: http://localhost:8004/api/v1
```

#### 测试/生产环境（腾讯云服务器）
```
Base URL: http://124.221.80.250:8004/api/v1
```

#### 推荐配置方式

**方式一: 环境变量**（推荐）
```typescript
// config.ts
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://124.221.80.250:8004/api/v1';

export const config = {
  apiBaseUrl: API_BASE_URL
};
```

**方式二: 配置文件**
```typescript
// config/environments.ts
const environments = {
  development: {
    apiBaseUrl: 'http://localhost:8004/api/v1'
  },
  production: {
    apiBaseUrl: 'http://124.221.80.250:8004/api/v1'  // 腾讯云公网IP
  }
};

export const config = environments[process.env.NODE_ENV || 'development'];
```

**Axios 初始化示例**:
```typescript
import axios from 'axios';
import { config } from './config';

const apiClient = axios.create({
  baseURL: config.apiBaseUrl,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
});

export default apiClient;
```

### 快速开始

**开发环境** `.env.development`:
```bash
REACT_APP_API_BASE_URL=http://localhost:8004/api/v1
```

**生产环境** `.env.production`:
```bash
REACT_APP_API_BASE_URL=http://124.221.80.250:8004/api/v1
```

### 通用响应格式

#### 成功响应
```json
{
  "data": { ... }
}
```

#### 错误响应
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "request_id": "unique_request_id"
  }
}
```

### HTTP 状态码

| 状态码 | 说明 |
|:---|:---|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## 1. 元数据接口 (Metadata APIs)

### 1.1 获取交易日历

**接口地址**: `GET /metadata/calendar/tradingDays`

**用途**: 获取指定周的交易日历，用于渲染前端日历组件

**请求参数**:
| 参数 | 类型 | 必填 | 说明 | 示例 |
|:---|:---|:---:|:---|:---|
| week | string | 否 | 周标识 | `current` 或 `2026-W01` |

**响应示例**:
```json
{
  "weekLabel": "2026-W01",
  "tradingDays": [
    {
      "date": "2025-12-29",
      "dayOfWeek": 1,
      "isHoliday": false
    },
    {
      "date": "2025-12-30",
      "dayOfWeek": 2,
      "isHoliday": false
    },
    {
      "date": "2025-12-31",
      "dayOfWeek": 3,
      "isHoliday": false
    },
    {
      "date": "2026-01-01",
      "dayOfWeek": 4,
      "isHoliday": true
    }
  ],
  "holidays": [
    {
      "date": "2026-01-01",
      "name": "元旦"
    }
  ]
}
```

**字段说明**:
| 字段 | 类型 | 说明 |
|:---|:---|:---|
| weekLabel | string | 周标识，格式 YYYY-Www |
| tradingDays | array | 交易日列表 |
| tradingDays[].date | string | 日期，格式 YYYY-MM-DD |
| tradingDays[].dayOfWeek | number | 星期几 (1=周一, 5=周五) |
| tradingDays[].isHoliday | boolean | 是否为节假日 |
| holidays | array | 节假日列表 |
| holidays[].date | string | 节假日日期 |
| holidays[].name | string | 节假日名称 |

**前端示例代码** (Axios):
```typescript
import axios from 'axios';

const getTrading Days = async (week: string = 'current') => {
  const response = await axios.get('/api/v1/metadata/calendar/tradingDays', {
    params: { week }
  });
  return response.data;
};

// 获取当前周
const currentWeek = await getTradingDays();

// 获取指定周
const specificWeek = await getTradingDays('2026-W02');
```

---

### 1.2 获取标的基线

**接口地址**: `GET /metadata/baseline/current`

**用途**: 获取全市场A股标的总数，用于数据完整性计算

**请求参数**: 无

**响应示例**:
```json
{
  "lastUpdated": "2026-01-01 16:43:37",
  "total": 5422,
  "markets": [
    {
      "market": "主板",
      "name": "沪市A股",
      "count": 3179
    },
    {
      "market": "创业板",
      "name": "创业板",
      "count": 1384
    },
    {
      "market": "北交所",
      "name": "北交所",
      "count": 270
    },
    {
      "market": "科创板",
      "name": "科创板",
      "count": 589
    }
  ]
}
```

**字段说明**:
| 字段 | 类型 | 说明 |
|:---|:---|:---|
| lastUpdated | string | 最后更新时间 |
| total | number | 全市场总数 |
| markets | array | 各市场详情 |
| markets[].market | string | 市场代码 |
| markets[].name | string | 市场名称 |
| markets[].count | number | 该市场标的数量 |

**前端示例代码**:
```typescript
const getBaseline = async () => {
  const response = await axios.get('/api/v1/metadata/baseline/current');
  return response.data;
};

const baseline = await getBaseline();
console.log(`当前监控标的总数: ${baseline.total}`);
```

---

## 2. 审计接口 (Audit APIs)

### 2.1 获取周度审计报告

**接口地址**: `GET /audit/weekly`

**用途**: 获取本周每日数据完整性审计报告，用于渲染数据质量仪表盘

**请求参数**:
| 参数 | 类型 | 必填 | 说明 | 示例 |
|:---|:---|:---:|:---|:---|
| week | string | 否 | 周标识 | `current` 或 `2026-W01` |

**响应示例**:
```json
{
  "weekLabel": "2026-W01",
  "lastUpdated": "2026-01-01 16:43:44",
  "days": [
    {
      "date": "2025-12-29",
      "kline": {
        "l1_baseline": 5422,
        "l2_mysql": 5465,
        "l3_clickhouse": 5465,
        "completeness_pct": 100.79
      },
      "overallStatus": "complete"
    },
    {
      "date": "2025-12-30",
      "kline": {
        "l1_baseline": 5422,
        "l2_mysql": 5468,
        "l3_clickhouse": 5468,
        "completeness_pct": 100.85
      },
      "overallStatus": "complete"
    },
    {
      "date": "2026-01-01",
      "overallStatus": "holiday"
    }
  ]
}
```

**字段说明**:
| 字段 | 类型 | 说明 |
|:---|:---|:---|
| weekLabel | string | 周标识 |
| lastUpdated | string | 数据更新时间 |
| days | array | 每日审计数据 |
| days[].date | string | 日期 |
| days[].kline | object | K线数据统计 (交易日才有) |
| days[].kline.l1_baseline | number | 基线总数 (分母) |
| days[].kline.l2_mysql | number | MySQL 实际条数 |
| days[].kline.l3_clickhouse | number | ClickHouse 实际条数 |
| days[].kline.completeness_pct | number | 完整性百分比 |
| days[].overallStatus | string | 状态: `complete`, `partial`, `critical`, `holiday` |

**状态枚举**:
| 状态 | 含义 | 颜色建议 |
|:---|:---|:---|
| `complete` | 完整性 ≥ 99% | 绿色 |
| `partial` | 95% ≤ 完整性 < 99% | 黄色 |
| `critical` | 完整性 < 95% | 红色 |
| `holiday` | 休市日 | 灰色 |

**前端示例代码**:
```typescript
interface AuditDay {
  date: string;
  kline?: {
    l1_baseline: number;
    l2_mysql: number;
    completeness_pct: number;
  };
  overallStatus: 'complete' | 'partial' | 'critical' | 'holiday';
}

const getAuditReport = async (week: string = 'current') => {
  const response = await axios.get('/api/v1/audit/weekly', {
    params: { week }
  });
  return response.data;
};

// 使用示例
const report = await getAuditReport();
report.days.forEach((day: AuditDay) => {
  console.log(`${day.date}: ${day.overallStatus}`);
});
```

**UI 渲染建议**:
```tsx
// React 示例
const AuditCalendar: React.FC = () => {
  const [report, setReport] = useState(null);
  
  useEffect(() => {
    getAuditReport().then(setReport);
  }, []);
  
  return (
    <div className="audit-calendar">
      {report?.days.map(day => (
        <div 
          key={day.date}
          className={`day day-${day.overallStatus}`}
        >
          <div className="date">{day.date}</div>
          {day.kline && (
            <div className="completeness">
              {day.kline.completeness_pct}%
            </div>
          )}
        </div>
      ))}
    </div>
  );
};
```

---

## 3. 运维接口 (Ops APIs)

### 3.1 获取数据时效性

**接口地址**: `GET /ops/freshness`

**用途**: 检测数据最后同步时间，用于实时监控数据新鲜度

**请求参数**: 无

**响应示例**:
```json
{
  "lastSyncTime": "2025-12-31 23:54:22",
  "lagMinutes": 1009,
  "status": "critical"
}
```

**字段说明**:
| 字段 | 类型 | 说明 |
|:---|:---|:---|
| lastSyncTime | string | 最后同步时间 |
| lagMinutes | number | 距今分钟数 |
| status | string | 状态: `normal`, `warning`, `critical` |

**状态判定规则**:
| 状态 | 条件 | UI 建议 |
|:---|:---|:---|
| `normal` | lag ≤ 30分钟 | 绿色，正常 |
| `warning` | 30 < lag ≤ 120分钟 | 黄色，提示 |
| `critical` | lag > 120分钟 | 红色，告警 |

**前端示例代码**:
```typescript
const getFreshness = async () => {
  const response = await axios.get('/api/v1/ops/freshness');
  return response.data;
};

// 轮询示例
setInterval(async () => {
  const freshness = await getFreshness();
  
  if (freshness.status === 'critical') {
    showNotification('数据同步延迟，请联系管理员');
  }
}, 60000); // 每分钟检查一次
```

---

### 3.2 获取复权因子数据

**接口地址**: `GET /ops/adjust-factor`

**用途**: 获取指定日期的复权因子同步数据

**请求参数**:
| 参数 | 类型 | 必填 | 说明 | 示例 |
|:---|:---|:---:|:---|:---|
| date | string | 否 | 日期 | `2025-12-31` |

**响应示例**:
```json
{
  "date": "2025-12-31",
  "count": 8,
  "codes": [
    "sh.600033",
    "sh.603043",
    "sz.000531",
    "sz.002400",
    "sz.002817",
    "sz.300339",
    "sz.300770",
    "sz.301687"
  ]
}
```

**字段说明**:
| 字段 | 类型 | 说明 |
|:---|:---|:---|
| date | string | 查询的日期 |
| count | number | 该日期复权因子数量 |
| codes | array | 示例股票代码（最多10个） |

**前端示例代码**:
```typescript
const getAdjustFactor = async (date: string) => {
  const response = await axios.get('/api/v1/ops/adjust-factor', {
    params: { date }
  });
  return response.data;
};

// 使用示例
const data = await getAdjustFactor('2025-12-31');
console.log(`${data.date}: ${data.count} 条复权因子`);
```

**UI渲染建议**:
```typescript
// 根据用户选中的日期动态显示
const AdjustFactorCard = ({ selectedDate }) => {
  const [data, setData] = useState(null);
  
  useEffect(() => {
    getAdjustFactor(selectedDate).then(setData);
  }, [selectedDate]);
  
  return (
    <div>
      <h3>复权因子</h3>
      <p>{selectedDate} 同步: {data?.count || 0} 条</p>
      {data?.count === 0 && (
        <span className="tip">
          {isHoliday(selectedDate) ? '休市日' : '无除权除息事件'}
        </span>
      )}
    </div>
  );
};
```

### 3.3 数据补全修复 (Remediate)

**端点**: `POST /api/v1/ops/remediate`

**功能**: 当某天 `L2 MySQL` 数据计数异常（缺失）时，手动触发云端重新抓取特定日期的数据。

**请求参数 (Query)**:
| 参数 | 类型 | 必选 | 说明 |
|:---|:---|:---|:---|
| date | string | 是 | 要修复的日期，格式 `YYYY-MM-DD` |
| scope | string | 否 | 范围：`incremental` (仅补缺，默认) / `full` (清空重抓) |
| data_type | string | 否 | 类型：目前仅支持 `kline` |

**响应示例**:
```json
{
  "status": "ok",
  "triggeredJobId": "remediate_kline_20251229",
  "message": "补偿任务已启动"
}
```

**前端调用建议**:
```typescript
const triggerRemediate = async (date: string) => {
  // 注意：这是一个异步任务，立即返回但工作在后台运行
  const response = await axios.post('/api/v1/ops/remediate', null, {
    params: { date, scope: 'incremental' }
  });
  return response.data;
};
```

---

## 4. 调度接口 (Scheduler APIs)

### 4.1 获取任务列表

**接口地址**: `GET /scheduler/jobs`

**用途**: 获取所有容器的调度任务列表（跨容器聚合）

**请求参数**: 无

**响应示例**:
```json
{
  "jobs": [
    {
      "id": "daily_comprehensive_sync",
      "name": "daily_comprehensive_sync_job_18:30",
      "next_run_time": "2026-01-01 18:30:00+08:00",
      "trigger": "cron[hour='18', minute='30', second='0']",
      "status": "active",
      "container": "baostock-api",
      "display_name": "[BaoStock] daily_comprehensive_sync_job_18:30"
    }
  ]
}
```

**字段说明**:
| 字段 | 类型 | 说明 |
|:---|:---|:---|
| jobs | array | 任务列表 |
| jobs[].id | string | 任务唯一标识 |
| jobs[].name | string | 任务原始名称 |
| jobs[].next_run_time | string | 下次执行时间 |
| jobs[].trigger | string | 触发器类型 |
| jobs[].status | string | 状态: `active`, `paused` |
| jobs[].container | string | 所属容器 |
| jobs[].display_name | string | 展示名称 |

**前端示例代码**:
```typescript
const getJobs = async () => {
  const response = await axios.get('/api/v1/scheduler/jobs');
  return response.data.jobs;
};

// 使用示例
const jobs = await getJobs();
const activeJobs = jobs.filter(j => j.status === 'active');
console.log(`运行中任务数: ${activeJobs.length}`);
```

---

### 4.2 控制任务

**接口地址**: `POST /scheduler/jobs/{job_id}/{action}`

**用途**: 控制任务执行（暂停、恢复、立即运行）

**请求参数**:
| 参数 | 类型 | 必填 | 说明 | 示例 |
|:---|:---|:---:|:---|:---|
| job_id | path | 是 | 任务ID | `daily_comprehensive_sync` |
| action | path | 是 | 操作类型 | `pause`, `resume`, `run` |
| container | query | 是 | 目标容器 | `baostock`, `akshare`, `pywencai` |

**响应示例**:
```json
{
  "status": "ok",
  "message": "Action pause sent to baostock"
}
```

**前端示例代码**:
```typescript
const controlJob = async (
  jobId: string,
  action: 'pause' | 'resume' | 'run',
  container: string
) => {
  const response = await axios.post(
    `/api/v1/scheduler/jobs/${jobId}/${action}`,
    null,
    { params: { container } }
  );
  return response.data;
};

// 暂停任务
await controlJob('daily_comprehensive_sync', 'pause', 'baostock');

// 立即运行
await controlJob('daily_comprehensive_sync', 'run', 'baostock');
```

---

### 4.3 获取任务日志

**接口地址**: `GET /scheduler/jobs/{job_id}/logs`

**用途**: 获取任务执行日志

**请求参数**:
| 参数 | 类型 | 必填 | 说明 | 示例 |
|:---|:---|:---:|:---|:---|
| job_id | path | 是 | 任务ID | `daily_comprehensive_sync` |
| container | query | 是 | 目标容器 | `baostock` |
| lines | query | 否 | 返回行数 | `50` (默认) |

**响应示例**:
```json
{
  "summary": "运行正常，已处理 3200/5820，无错误",
  "logs": [
    "[2026-01-01 17:05:01] [INFO] Processing sh.600036",
    "[2026-01-01 17:05:02] [INFO] Saved 1 record"
  ]
}
```

**前端示例代码**:
```typescript
const getJobLogs = async (
  jobId: string,
  container: string,
  lines: number = 50
) => {
  const response = await axios.get(
    `/api/v1/scheduler/jobs/${jobId}/logs`,
    { params: { container, lines } }
  );
  return response.data;
};
```

---

## 5. 系统接口 (System APIs)

### 5.1 系统健康检查

**接口地址**: `GET /system/health`

**用途**: 检查所有服务健康状态

**请求参数**: 无

**响应示例**:
```json
{
  "status": "healthy",
  "services": {
    "baostock_api": "healthy",
    "akshare_api": "healthy",
    "pywencai_api": "healthy",
    "mysql": "healthy"
  }
}
```

**字段说明**:
| 字段 | 类型 | 说明 |
|:---|:---|:---|
| status | string | 整体状态: `healthy`, `degraded` |
| services | object | 各服务状态 |
| services.* | string | 单个服务状态: `healthy`, `unhealthy` |

**前端示例代码**:
```typescript
const getSystemHealth = async () => {
  const response = await axios.get('/api/v1/system/health');
  return response.data;
};

// 服务监控组件
const ServiceMonitor: React.FC = () => {
  const [health, setHealth] = useState(null);
  
  useEffect(() => {
    const interval = setInterval(async () => {
      const data = await getSystemHealth();
      setHealth(data);
    }, 30000); // 每30秒检查一次
    
    return () => clearInterval(interval);
  }, []);
  
  return (
    <div>
      整体状态: {health?.status}
      {Object.entries(health?.services || {}).map(([name, status]) => (
        <div key={name}>{name}: {status}</div>
      ))}
    </div>
  );
};
```

---

## 6. 错误处理指南

### 6.1 常见错误码

| 错误码 | HTTP状态 | 说明 | 处理建议 |
|:---|:---:|:---|:---|
| `Invalid week format` | 400 | 周格式错误 | 检查参数格式 |
| `Unknown container` | 500 | 容器名不存在 | 使用正确的容器名 |
| `Invalid action` | 400 | 操作类型无效 | 使用 pause/resume/run |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 | 稍后重试或联系管理员 |

### 6.2 错误处理示例

```typescript
import axios, { AxiosError } from 'axios';

// Axios 拦截器配置
axios.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.data?.error) {
      const { code, message, request_id } = error.response.data.error;
      
      console.error(`[${request_id}] ${code}: ${message}`);
      
      // 根据错误码处理
      if (code === 'INTERNAL_ERROR') {
        showNotification('服务暂时不可用，请稍后重试');
      }
    }
    
    return Promise.reject(error);
  }
);
```

---

## 7. 完整示例 (React + TypeScript)

```typescript
// api/stockManager.ts
import axios from 'axios';
import { config } from '../config'; // 使用环境配置

const apiClient = axios.create({
  baseURL: config.apiBaseUrl, // ✅ 从配置读取
  timeout: 10000,
});

export const stockManagerAPI = {
  // 元数据
  getTradingDays: (week: string = 'current') =>
    apiClient.get('/metadata/calendar/tradingDays', { params: { week } }),
  
  getBaseline: () =>
    apiClient.get('/metadata/baseline/current'),
  
  // 审计
  getAuditReport: (week: string = 'current') =>
    apiClient.get('/audit/weekly', { params: { week } }),
  
  // 运维
  getFreshness: () =>
    apiClient.get('/ops/freshness'),
  
  // 调度
  getJobs: () =>
    apiClient.get('/scheduler/jobs'),
  
  controlJob: (jobId: string, action: string, container: string) =>
    apiClient.post(`/scheduler/jobs/${jobId}/${action}`, null, {
      params: { container }
    }),
  
  // 系统
  getSystemHealth: () =>
    apiClient.get('/system/health'),
};

// 使用示例
export const useAuditReport = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  
  useEffect(() => {
    setLoading(true);
    stockManagerAPI.getAuditReport()
      .then(res => setData(res.data))
      .finally(() => setLoading(false));
  }, []);
  
  return { data, loading };
};
```

---

## 8. 性能优化建议

### 8.1 接口缓存策略

| 接口 | 缓存时长 | 说明 |
|:---|:---:|:---|
| `/metadata/calendar` | 1天 | 交易日历变化频率低 |
| `/metadata/baseline` | 1小时 | 基线每日更新 |
| `/audit/weekly` | 5分钟 | 审计数据按需刷新 |
| `/ops/freshness` | 无 | 实时数据，不缓存 |
| `/scheduler/jobs` | 30秒 | 任务状态变化较快 |

### 8.2 轮询建议

```typescript
// 推荐使用 React Query 或 SWR
import useSWR from 'swr';

const useFreshness = () => {
  return useSWR(
    '/ops/freshness',
    () => stockManagerAPI.getFreshness(),
    { refreshInterval: 60000 } // 每分钟刷新
  );
};
```

---

## 9. 联系与支持

- **服务端口**: 8004
- **健康检查**: `http://localhost:8004/health`
- **技术支持**: 查阅 QC 报告或联系后端团队

---

*文档版本: v1.0*  
*最后更新: 2026-01-01*
