# 量化数据监控小程序 - 前端开发规范

## 1. 项目概述

### 1.1 定位
这是一款面向个人量化交易者的**数据质量监控与任务管理**小程序。用户可以通过手机随时查看股票数据采集状态、触发补采任务、接收告警通知。

### 1.2 技术栈
- **框架**: 原生微信小程序 或 uni-app
- **UI 库**: WeUI / Vant Weapp
- **请求**: wx.request (封装统一的 API 调用模块)
- **状态管理**: 简单场景可用 globalData，复杂可用 MobX

### 1.3 后端接口
- **基础 URL**: `https://your-domain.com/api/v1`
- **认证方式**: 暂无 (后续可加 Token)

---

## 2. 页面结构

```
pages/
├── index/index          # 首页：今日数据概览 + 快捷操作
├── tasks/list           # 任务列表：查看所有任务状态
├── tasks/detail         # 任务详情：查看执行历史
├── commands/history     # 命令历史：我发起的触发记录
└── settings/index       # 设置：告警开关、阈值配置
```

---

## 3. 页面设计与交互

### 3.1 首页 (index)

#### 布局
```
┌────────────────────────────────────────┐
│  📊 今日数据概览          2026-01-14   │
├────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐   │
│  │  K线覆盖率   │  │  分笔覆盖率  │   │
│  │    98.5%     │  │    92.3%     │   │
│  │   ✅ 达标    │  │   ⚠️ 偏低    │   │
│  └──────────────┘  └──────────────┘   │
├────────────────────────────────────────┤
│  📋 最近任务                           │
│  ├─ daily_kline_sync   ✅ 17:32 完成   │
│  ├─ sync_tick_shard_0  ⏳ 运行中...    │
│  └─ pre_market_gate    ⏰ 明日 08:00   │
├────────────────────────────────────────┤
│  ┌────────────────────────────────┐    │
│  │     🔄 手动触发补采            │    │
│  └────────────────────────────────┘    │
└────────────────────────────────────────┘
```

#### 交互说明
1. 点击覆盖率卡片 → 跳转到对应数据详情页
2. 点击任务条目 → 跳转到任务详情页
3. 点击"手动触发补采" → 弹出任务选择弹窗

---

### 3.2 手动触发弹窗 (Modal)

```
┌────────────────────────────────────────┐
│           选择要触发的任务              │
├────────────────────────────────────────┤
│  ○ 盘前数据校验 (pre_market_gate)      │
│  ○ K线同步 (daily_kline_sync)          │
│  ○ 分笔补采 (sync_tick)                │
├────────────────────────────────────────┤
│  📅 目标日期: [2026-01-13]  ← 可选     │
├────────────────────────────────────────┤
│  [取消]              [确认触发]        │
└────────────────────────────────────────┘
```

#### 交互说明
1. 单选任务类型
2. 可选填入目标日期（默认昨天）
3. 点击"确认触发" → 调用 `/commands` 接口 → 显示"已加入队列"

---

### 3.3 命令历史页 (commands/history)

```
┌────────────────────────────────────────┐
│  📜 我的触发记录                        │
├────────────────────────────────────────┤
│  #12  sync_tick        ✅ 已完成       │
│       2026-01-14 09:15  耗时 3分12秒   │
├────────────────────────────────────────┤
│  #11  pre_market_gate  ✅ 已完成       │
│       2026-01-14 08:05  耗时 45秒      │
├────────────────────────────────────────┤
│  #10  daily_kline_sync ❌ 失败         │
│       2026-01-13 17:45  网络超时       │
└────────────────────────────────────────┘
```

---

## 4. API 接口规范

### 4.1 获取今日数据概览
```yaml
GET /api/v1/dashboard/overview

Response:
{
  "date": "2026-01-14",
  "kline_coverage": 98.5,
  "tick_coverage": 92.3,
  "kline_status": "ok",      // ok | warning | error
  "tick_status": "warning",
  "recent_tasks": [
    {
      "task_id": "daily_kline_sync",
      "name": "K线同步",
      "status": "SUCCESS",
      "last_run": "2026-01-14T17:32:00"
    }
  ]
}
```

### 4.2 获取任务列表
```yaml
GET /api/v1/tasks

Response:
{
  "tasks": [
    {
      "id": "pre_market_gate",
      "name": "盘前数据校验",
      "category": "pre_market",
      "enabled": true,
      "schedule": "08:00 交易日",
      "next_run": "2026-01-15T08:00:00",
      "last_status": "SUCCESS"
    }
  ]
}
```

### 4.3 触发任务命令
```yaml
POST /api/v1/commands

Request:
{
  "task_id": "sync_tick",
  "params": {
    "target_date": "20260113"   // 可选
  }
}

Response:
{
  "command_id": 15,
  "status": "PENDING",
  "message": "命令已加入队列"
}
```

### 4.4 查询命令状态
```yaml
GET /api/v1/commands/{command_id}

Response:
{
  "id": 15,
  "task_id": "sync_tick",
  "status": "DONE",           // PENDING | RUNNING | DONE | FAILED
  "created_at": "2026-01-14T09:15:00",
  "executed_at": "2026-01-14T09:15:05",
  "result": "SUCCESS"
}
```

### 4.5 获取命令历史
```yaml
GET /api/v1/commands?limit=20

Response:
{
  "commands": [
    {
      "id": 15,
      "task_id": "sync_tick",
      "status": "DONE",
      "created_at": "2026-01-14T09:15:00"
    }
  ]
}
```

---

## 5. 开发注意事项

### 5.1 网络请求封装
```javascript
// utils/api.js
const BASE_URL = 'https://your-domain.com/api/v1';

export const request = (options) => {
  return new Promise((resolve, reject) => {
    wx.request({
      url: BASE_URL + options.url,
      method: options.method || 'GET',
      data: options.data,
      success: (res) => {
        if (res.statusCode === 200) {
          resolve(res.data);
        } else {
          reject(res);
        }
      },
      fail: reject
    });
  });
};

// 使用示例
import { request } from '../../utils/api';
const overview = await request({ url: '/dashboard/overview' });
```

### 5.2 状态颜色规范
| 状态 | 颜色 | 图标 |
|:-----|:-----|:-----|
| SUCCESS / ok | #52c41a (绿) | ✅ |
| WARNING | #faad14 (黄) | ⚠️ |
| FAILED / error | #f5222d (红) | ❌ |
| RUNNING | #1890ff (蓝) | ⏳ |
| PENDING | #8c8c8c (灰) | ⏰ |

### 5.3 域名配置
在微信公众平台后台配置：
- **request 合法域名**: `https://your-domain.com`

---

## 6. 开发顺序建议

1. **首页 (index)**: 仅展示静态 Mock 数据
2. **手动触发弹窗**: 实现 POST /commands 调用
3. **命令历史页**: 实现列表拉取与状态轮询
4. **任务列表页**: 展示所有任务配置
5. **联调对接**: 替换 Mock 为真实 API

---

## 7. Mock 数据示例 (开发阶段使用)

```javascript
// mock/dashboard.js
export const mockOverview = {
  date: "2026-01-14",
  kline_coverage: 98.5,
  tick_coverage: 92.3,
  kline_status: "ok",
  tick_status: "warning",
  recent_tasks: [
    { task_id: "daily_kline_sync", name: "K线同步", status: "SUCCESS", last_run: "2026-01-14T17:32:00" },
    { task_id: "sync_tick_shard_0", name: "分笔采集", status: "RUNNING", last_run: "2026-01-14T15:35:00" }
  ]
};
```

#  发布日期：2026-01-14