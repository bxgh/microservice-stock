# 股市日记系统：后端 API 接口需求文档 (V1.0)

本文档定义了前端“股市日记”模块所需的后端接口规范，旨在支持日记看板、多维列表、专业编辑器及数据分发功能。

---

## 1. 通用规范
- **Base URL**: `/api/v1/diary`
- **认证方式**: Bearer JWT (由 `Authorization` Header 携带)
- **数据格式**: JSON
- **错误处理**: 标准 HTTP 状态码 + 业务错误描述

---

## 2. 接口列表

### 2.1 获取日记看板统计数据
- **Endpoint**: `GET /stats`
- **描述**: 用于主页顶部的指标展示。
- **返回字段**:
  - `monthly_days`: (int) 本月记录天数
  - `error_book_count`: (int) 错题本（#错题本 标签或特定情绪）总篇数
  - `latest_mood`: (string) 最近一次的心情描述
  - `mood_distribution`: (array) 心情分布统计（用于后续图表展示）

### 2.2 获取日记列表 (分页/过滤)
- **Endpoint**: `GET /entries`
- **参数**:
  - `page`: (int) 页码
  - `page_size`: (int) 每页条数
  - `tab`: (string) 分类过滤 [`all`, `review`, `error`, `research`, `notes`]
  - `query`: (string) 全文搜索关键词 (支持 ngram 内容搜索)
- **返回字段**:
  - `list`: (array) 日记简要信息
    - `id`, `title`, `summary`, `mood`, `category`, `date`, `time`, `is_error_book`
    - `stocks`: (array) 关联股票 [{name, code}]
    - `tags`: (array) 标签列表
  - `total`: (int) 总条数

### 2.3 获取日记详情
- **Endpoint**: `GET /entries/:id`
- **返回字段**: 完整日记对象，包含 `content` (Markdown)。

### 2.4 保存/更新日记
- **Endpoint**: `POST /entries` (新建) / `PUT /entries/:id` (修改)
- **Payload**:
  - `title`: (string) 标题
  - `content`: (string) Markdown 内容
  - `mood`: (string) 心情
  - `category`: (string) 分类
  - `stocks`: (array) 提取出的股票代码列表
  - `tags`: (array) 提取出的标签列表
  - `attachments`: (array) 图片/附件 COS Key 列表

### 2.5 批量导出任务 (Epic 5)
- **Endpoint**: `POST /export`
- **Payload**: `{ "ids": [], "format": "markdown" }`
- **描述**: 异步生成全量 Markdown 包。

### 2.6 公众号分发 (Epic 5)
- **Endpoint**: `POST /publish/mp`
- **Payload**: `{ "entry_id": int, "is_snapshot": bool }`
- **描述**: 将日记内容转换为微信素材格式并推送到草稿箱。

---

## 3. 数据库设计要点 (参考)
- **全文索引**: `diary_entry.content` 需建立 `ngram` 全文索引以支持快速搜索。
- **关联表**: `diary_stock` 用于建立日记与个股的 N:N 关系，便于按股票筛选日记。
- **静态标签**: `diary_tag_dict` 预置系统推荐标签。
