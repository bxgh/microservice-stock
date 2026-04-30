# 股市日记系统：API 规格说明书 (V1.0)

本文档详细描述了股市日记系统的后端 API 接口，供前端（WeChat Taro）与后端（wxch-gateway）对接使用。

---

## 1. 通用规范

- **Base URL**: `https://<gateway-domain>/api/v1/diaries`
- **认证方式**: 
  - Header: `Authorization: Bearer <JWT_TOKEN>`
  - Token 获取见 [token.md](./token.md)
- **数据格式**: 请求与响应均使用 `application/json`
- **公共响应结构**:
  ```json
  {
    "code": 200,      // 200=成功, 400=参数错误, 401=未授权, 403=权限不足, 500=服务器错误
    "data": { ... },   // 业务数据
    "message": "success"
  }
  ```

---

## 2. 核心枚举值 (Constants)

### 2.1 日记类型 (`entry_type`)
- `1`: 盘前 (Pre-market)
- `2`: 盘中 (Intra-day)
- `3`: 盘后 (Post-market)
- `4`: 周复盘 (Weekly Review)
- `5`: 随笔 (Notes)
- `6`: 个股研究 (Stock Research)

### 2.2 情绪标志 (`mood`)
- `1`: 冷静 (Calm)
- `2`: 兴奋 (Excited)
- `3`: 焦虑 (Anxious)
- `4`: 恐惧 (Fearful)
- `5`: 贪婪 (Greedy)
- `6`: 困惑 (Confused)

### 2.3 可见性 (`visibility`)
- `0`: 私密 (Private)
- `1`: 链接可见 (Link Only)
- `2`: 公开 (Public)

---

## 3. 接口列表

### 3.1 看板统计
- **Endpoint**: `GET /stats`
- **描述**: 获取用户当月日记统计及情绪概览。 (实际路径: `/api/v1/diaries/stats`)
- **响应 Data**:
  ```json
  {
    "monthly_days": 12,        // 本月记录天数
    "error_book_count": 5,     // 错题本总数 (标签 category=2)
    "latest_mood": 1,          // 最近一次日记的情绪值
    "mood_distribution": [     // 情绪分布统计
      { "mood": 1, "count": 10 },
      { "mood": 3, "count": 2 }
    ]
  }
  ```

### 3.2 日记列表 (分页/过滤)
- **Endpoint**: `GET /entries`
- **描述**: 获取日记列表。 (实际路径: `/api/v1/diaries/entries`)
- **查询参数**:
  - `page`: (int) 页码, 默认 1
  - `page_size`: (int) 每页大小, 默认 10
  - `tab`: (string) 分类 [可选: `all`, `review`, `error`, `research`, `notes`]
  - `query`: (string) 全文搜索关键词
  - `stock_code`: (string) 筛选特定股票关联的日记 (ts_code)
- **响应 Data**:
  ```json
  {
    "total": 100,
    "list": [
      {
        "id": 1024,
        "title": "今日操作总结",
        "excerpt": "今天主要关注了人工智能板块的龙头...",
        "entry_date": "2026-04-30",
        "entry_type": 3,
        "mood": 1,
        "is_pinned": 1,
        "is_error_book": true,
        "stocks": [
          {
            "ts_code": "600519.SH",
            "name": "贵州茅台",
            "price": 1750.5,      // 实时价格 (后端透传)
            "pct_chg": 1.25       // 实时涨跌幅
          }
        ],
        "tags": ["长线", "龙头"],
        "created_at": "2026-04-30 15:30:00"
      }
    ]
  }
  ```

### 3.3 日记详情
- **Endpoint**: `GET /entries/:id`
- **描述**: 获取指定日记的完整 Markdown 内容。 (实际路径: `/api/v1/diaries/entries/:id`)
- **响应 Data**:
  ```json
  {
    "id": 1024,
    "title": "今日操作总结",
    "content": "# Markdown 标题\n今天的内容...",
    "entry_date": "2026-04-30",
    "entry_type": 3,
    "mood": 1,
    "visibility": 0,
    "stocks": [{ "ts_code": "600519.SH", "name": "贵州茅台" }],
    "tags": ["长线", "龙头"],
    "attachments": [
      { "id": 1, "url": "https://cos.../a.jpg", "mime_type": "image/jpeg" }
    ],
    "created_at": "2026-04-30 15:30:00",
    "updated_at": "2026-04-30 16:00:00"
  }
  ```

### 3.4 保存/更新日记
- **Endpoint**: `POST /entries` (新建) / `PUT /entries/:id` (修改)
- **描述**: 保存或更新日记内容。 (实际路径: `/api/v1/diaries/entries` 或 `/api/v1/diaries/entries/:id`)
- **请求 Payload**:
  ```json
  {
    "title": "可选标题",
    "content": "Markdown 正文",
    "entry_date": "2026-04-30", // 默认为当天
    "entry_type": 3,
    "mood": 1,
    "visibility": 0,
    "is_pinned": 0,
    "stocks": ["600519.SH"],    // 传递 ts_code 数组
    "tags": ["错题本", "抄底"],  // 传递标签名称数组
    "attachment_ids": [1, 2]     // 关联已上传的附件 ID
  }
  ```
- **后端处理**: 自动根据内容截取 `excerpt`，自动维护 `diary_stock` 和 `diary_tag` 关联。

### 3.5 删除日记
- **Endpoint**: `DELETE /entries/:id`
- **描述**: 软删除日记 (设置 `deleted_at`)。 (实际路径: `/api/v1/diaries/entries/:id`)

### 3.6 标签字典获取
- **Endpoint**: `GET /tags/dict`
- **描述**: 获取系统推荐标签及用户历史标签。
- **响应 Data**:
  ```json
  {
    "system_tags": [
      { "name": "错题本", "category": 2, "color": "#FF4D4F" },
      { "name": "核心资产", "category": 3, "color": "#1890FF" }
    ],
    "user_tags": ["我的策略", "打板"]
  }
  ```

### 3.7 附件上传/登记
- **Endpoint**: `POST /attachments`
- **描述**: 客户端完成 COS 上传后，向后端登记附件信息。
- **请求 Payload**:
  ```json
  {
    "cos_key": "diary/1/202604/abc.jpg",
    "mime_type": "image/jpeg",
    "size_bytes": 102450,
    "original_name": "photo.jpg"
  }
  ```
- **响应 Data**: 返回附件的 `id`。

### 3.8 批量导出任务
- **Endpoint**: `POST /export`
- **请求 Payload**:
  ```json
  {
    "task_type": 1,     // 1=单篇, 2=按月, 3=按年, 4=全量
    "scope": { "month": "2026-04" }, // 视 task_type 而定
    "format": "md"      // 目前仅支持 md
  }
  ```
- **响应 Data**: `{ "task_id": 1001 }`

### 3.9 公众号发布 (草稿)
- **Endpoint**: `POST /publish/mp`
- **描述**: 将日记内容转换为 HTML 并上传至微信公众号草稿箱（仅支持已绑定的单个公众号）。 (实际路径: `/api/v1/diaries/publish/mp`)
- **请求 Payload**:
  ```json
  {
    "entry_id": 1024,
    "is_snapshot": true // 是否创建独立快照(允许二次编辑)
  }
  ```
- **响应 Data**: 
  ```json
  {
    "publish_record_id": 500,
    "wx_media_id": "xxx",
    "message": "Draft created successfully in WeChat"
  }
  ```

---

## 4. 错误码定义

| Code | 描述 |
|---|---|
| 200 | 请求成功 |
| 400 | 参数校验失败 (Invalid Parameter) |
| 401 | 身份认证失败 (Unauthorized) |
| 403 | 无权访问该资源 (Forbidden) |
| 404 | 资源不存在 (Not Found) |
| 429 | 请求过于频繁 (Rate Limit) |
| 500 | 服务器内部错误 (Internal Server Error) |

---

## 5. 数据库关联逻辑说明

1. **自动摘要**: 后端在保存日记时，通过正则去掉 Markdown 语法标签，取前 60 个字符存入 `excerpt`。
2. **股票关联**: 保存时根据 `stocks` 数组中的 `ts_code` 匹配 `stock_info` 表，维护 `diary_stock` 关系。
3. **标签关联**: 
   - 检查 `diary_tag_dict` 是否存在该标签名。
   - 不存在则创建，`owner_user_id` 设为当前用户 ID。
   - 更新 `diary_tag` 关系。
4. **行情透传**: `GET /entries` 列表接口中，后端需根据 `stocks` 的 `ts_code` 批量获取实时行情并返回。

---

## 6. 微信小程序调用示例 (WeChat Cloud Container)

建议在小程序中使用 `wx.cloud.callContainer` 进行调用，这样可以享受腾讯云内网加速。

```javascript
// 示例：创建一篇新日记
wx.cloud.callContainer({
  "config": {
    "env": "prod-xxxxx" // 你的云托管环境ID
  },
  "path": "/api/v1/diaries/entries",
  "header": {
    "X-WX-SERVICE": "wxch-gateway", // 目标服务名称
    "Authorization": "Bearer " + wx.getStorageSync('token') // 传递 JWT
  },
  "method": "POST",
  "data": {
    "entry_date": "2026-05-01",
    "entry_type": 5,
    "title": "今日复盘",
    "content": "今天市场表现...",
    "stocks": ["600519.SH"]
  },
  "success": (res) => {
    console.log("日记已保存:", res.data);
  },
  "fail": (err) => {
    console.error("请求失败:", err);
  }
});
```
