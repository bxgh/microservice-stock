# Epic E23-S8 每日格言打卡系统 HTTP REST API 接口契约 (API.md)

> [!NOTE]
> **API 真源声明**: 每日格言打卡系统通过统一的 `wxch-gateway` Web 网关对外暴露。微信小程序端必须携带标准授权标头进行接入。本文件作为前端与后端系统开发的唯一真源 HTTP REST 契约协议。

---

## 1. 基础配置与鉴权契约

- **API 基本路径 (Base URL)**: `/api/v1`
- **默认时区 (Timezone)**: `Asia/Shanghai` (CST)
- **安全鉴权 (Authentication)**: 
  - 所有接口（除公开或免登录除外，打卡相关接口一律强制校验鉴权）均必须在 HTTP Request Headers 中携带微信小程序颁发的 JWT Access Token。
  - **标头结构**:
    ```http
    Authorization: Bearer <Your_Access_Token>
    ```

---

## 2. 接口端点定义 (Endpoints)

### 2.1 手工录入格言 (POST /checkin/maxim/quote)

- **接口描述**: 允许用户从小程序端录入自定义或收集的金句格言（支持手工录入和粘贴复制）。
- **请求格式**: `application/json`
- **请求 Payload**:
  ```json
  {
    "content": "在别人恐惧时我贪婪，在别人贪婪时我恐惧。",
    "source_author": "巴菲特",
    "source_book": "致股东的信",
    "category": 1,
    "base_weight": 80
  }
  ```
  - **字段约束**:
    - `content`: `str`，格言正文。必填，长度限 10 ~ 500 字。
    - `source_author`: `str`，原作者。非必填，限 64 字以内。
    - `source_book`: `str`，来源渠道或书籍。非必填，限 128 字以内。
    - `category`: `int`，分类。1=经典名言, 2=大佬语录, 3=历史教训, 4=用户摘录, 5=自己写的金句。默认 1。
    - `base_weight`: `int`，基础曝光权重。默认 50，范围 1 ~ 100。
- **响应体 (Response Body)**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": {
      "quote_id": 12,
      "content": "在别人恐惧时我贪婪，在别人贪婪时我恐惧。",
      "created_at": "2026-05-19T10:08:13Z"
    }
  }
  ```

---

### 2.2 每日格言智能推荐与日内锁定 (GET /checkin/today)

- **接口描述**: 小程序端今日打卡主页加载时调用。根据智能加权轮询推荐算法返回格言，每日凌晨 4:00 后首次调用进行曝光与日内锁定，当日后续调用幂等返回锁定的格言。
- **请求格式**: 无 Payload
- **响应体 (已锁定格言)**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": {
      "msg": "LOCKED",
      "quote": {
        "id": 12,
        "content": "在别人恐惧时我贪婪，在别人贪婪时我恐惧。",
        "source_author": "巴菲特",
        "source_book": "致股东的信",
        "category": 1,
        "is_favorited": 0,
        "insight_count": 3
      },
      "history_insight": {
        "completed_diary_id": 98,
        "last_insight_content": "这是我之前写过的心得解读...",
        "last_insight_date": "2026-05-18"
      }
    }
  }
  ```
- **响应体 (词库为空冷启动防空转)**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": {
      "msg": "EMPTY_LIB",
      "quote": null,
      "history_insight": null
    }
  }
  ```

---

### 2.3 格言打卡行为交互控制 (POST /checkin/maxim/action)

- **接口描述**: 用户对锁定格言进行收藏（加权）、拉黑（屏蔽推荐）或跳过（释放当前锁定并扣减推荐分）的动作交互。
- **请求格式**: `application/json`
- **请求 Payload**:
  ```json
  {
    "quote_id": 12,
    "action_type": "favorite",
    "value": 1
  }
  ```
  - **字段约束**:
    - `quote_id`: `int`，名言唯一主键。必填。
    - `action_type`: `str`，动作类型。必须在 `["favorite", "dislike", "skip"]` 范围内。
    - `value`: `int`，设置的值。0=取消/未操作, 1=激活。
- **响应体**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": null
  }
  ```

---

### 2.4 提交心得感悟并完成打卡 (POST /checkin/maxim/submit)

- **接口描述**: 用户在今日打卡格言卡片下编写个人感悟，点击完成打卡。自动在数据库中生成随笔日记并更新状态锁定记录，执行数据与计数的事务更新。
- **请求格式**: `application/json`
- **请求 Payload**:
  ```json
  {
    "quote_id": 12,
    "insight": "这是一段字数必须大等于三十个字并且长度不能超过五百个汉字的极其深刻投资感悟反思，在这里记录心得体会。",
    "mood": 1
  }
  ```
  - **字段约束**:
    - `quote_id`: `int`，锁定打卡的格言ID。必填。
    - `insight`: `str`，解读心得。必填，长度限 30 ~ 500 字。
    - `mood`: `int`，打卡心情。非必填，限 1=平静, 2=兴奋, 3=郁闷, 4=焦虑, 5=贪婪, 6=恐惧。
- **响应体**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": {
      "diary_id": 102,
      "title": "格言解读 · 2026-05-19",
      "entry_date": "2026-05-19",
      "accumulated_insight_count": 4
    }
  }
  ```
- **异常拦截 (重复打卡保护)**:
  - 当今日已打卡成功时，再次提交会返回 `HTTP 400`。
  ```json
  {
    "error": {
      "code": "BAD_REQUEST",
      "message": "您今日已完成格言打卡，请勿重复提交！",
      "request_id": "req_8c3dceac"
    }
  }
  ```

---

### 2.5 历史反思轨迹时间轴 (GET /checkin/maxim/timeline)

- **接口描述**: 传入特定格言 ID，获取该用户针对此条格言的所有历史打卡反思轨迹与当时大盘情绪快照，帮助用户实现与过去的自己“隔空对话”。
- **请求格式**: Query Parameters
  - `quote_id`: `int`，格言ID。必填。
- **响应体**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": {
      "quote_id": 12,
      "content": "在别人恐惧时我贪婪，在别人贪婪时我恐惧。",
      "total_insights": 2,
      "timeline": [
        {
          "diary_id": 102,
          "date": "2026-05-19",
          "insight": "这是一段非常深刻并且字数一定要大于三十个汉字才可以正常通过后台Pydantic拦截校验的投资感悟反思，测试落库与锁更新逻辑。",
          "mood": 1,
          "market_summary": {
            "ts_code": "000001.SH",
            "pct_chg": -0.000934
          }
        },
        {
          "diary_id": 98,
          "date": "2026-05-18",
          "insight": "昨日的大跌中我有些许恐慌，记录今天的心得体会，要时刻遵守巴菲特老爷子的教诲...",
          "mood": 4,
          "market_summary": {
            "ts_code": "000001.SH",
            "pct_chg": -0.012400
          }
        }
      ]
    }
  }
  ```

---
*本接口契约文件为每日格言打卡系统 HTTP 服务端标准契约，已向全局网页 Portal 挂接。*
