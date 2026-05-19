# E23-S2 每日格言智能推荐与日内幂等锁定 API 交付报告

本报告记录了 [Epic E23] 每日格言打卡子系统中 **E23-S2（每日格言智能推荐与日内幂等锁定 API）** 的完整开发、测试与物理交付存证。

---

## 1. 核心交付成果 (Accomplishments)

已 100% 成功交付 E23-S2 阶段约定的所有核心业务功能和接口设计：

*   **凌晨 4:00 时间切分 (T1)**：成功在 `checkin_service.py` 中实现了基于 `Asia/Shanghai` 时区的凌晨 4:00 业务日期切分（`get_business_date`）。每天 04:00 前的访问一律划归为前一天，保证日历划分的业务合理性。
*   **多维度加权轮询挑选算法 (T2)**：
    *   自动过滤被拉黑的格言（`is_disliked = 1`）。
    *   自动进行最近 30 天已曝光历史排重，减少名言的短期重复曝光率。
    *   支持**收藏格言加权 (+20 积分)**；支持针对跳过名言的**连续跳过扣减惩罚分**。
*   **大盘情绪自动对齐加权 (T3)**：
    *   直连物理表 `ods_index_daily` 提取上证综指（`000001.SH`）最近一交易日的真实涨跌幅（`pct_chg`）。
    *   当大盘大涨（涨幅 >= +0.5%）时，自动对经典与心态类格言（Category 1, 3）进行 **+15 情绪加分**；
    *   当大盘大跌（跌幅 <= -0.5%）时，自动对大佬与心态类格言（Category 2, 3）进行 **+15 情绪加分**。
*   **空库冷启动兜底防闪烁 (T4)**：当系统冷启动且名言词库为空时，返回 `msg: "EMPTY_LIB"` 并向锁定表原子写入 `locked_target_id = NULL` 空值锁记录，完全规避界面空数据闪烁与重复扫表。
*   **日内锁定与历史打卡见解追溯 (T5)**：
    *   日内首次挑选后立即原子写入锁定表 `diary_checkin_lock`；后续调用命中锁定，幂等返回完全一致的名言。
    *   通过联表查询（锁表与日记随笔表 `diary_entry` JOIN），自动追溯该用户历史针对该格言发表的最新一次打卡见解（`history_insight`），呈现在界面上进行自我心灵对话。
*   **API 路由器注册 (T6)**：完整注册并挂载了 `GET /api/v1/checkin/today` 今日格言推荐端点。

---

## 2. 数据库物理结构与字段对齐存证

### 2.1 锁定表（`diary_checkin_lock`）结构
```text
Checking diary_checkin_lock columns:
  - id: bigint(20)
  - user_id: bigint(20)
  - business_date: date
  - checkin_type: tinyint(4)
  - locked_target_id: bigint(20)
  - status: tinyint(4)
  - completed_diary_id: bigint(20)
  - created_at: timestamp
  - updated_at: timestamp
```

### 2.2 用户行为状态表（`diary_quote_user_state`）结构
```text
Checking diary_quote_user_state columns:
  - id: bigint(20)
  - user_id: bigint(20)
  - quote_id: bigint(20)
  - is_favorited: tinyint(1)
  - skip_count: int(11)
  - expose_count: int(11)
  - last_exposed_at: datetime
  - created_at: timestamp
  - updated_at: timestamp
```

---

## 3. 自动化集成测试与 AC 验证报告

我们在 `wxch-gateway/scripts/testing/test_checkin.py` 中实现了 Consolidated 强隔离回归集成测试，成功在单个 asyncio 事件循环下完成了对 E23-S1 与 E23-S2 阶段 100% 全套验收标准 (AC) 的自动化覆盖：

```bash
python -m pytest -v wxch-gateway/scripts/testing/test_checkin.py
```

### 运行通过结果存证 (Test Success Log)

```text
============================= test session starts =============================
platform win32 -- Python 3.11.5, pytest-8.4.1, pluggy-1.6.0 -- D:\Program Files\Python311\python.exe
cachedir: .pytest_cache
rootdir: E:\gitee\microservice-stock
plugins: anyio-3.7.1, asyncio-1.1.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 2 items

wxch-gateway/scripts/testing/test_checkin.py::test_e23_checkin_integration_suite PASSED [ 50%]
wxch-gateway/scripts/testing/test_checkin.py::test_e23_s2_business_date_logic PASSED [100%]

======================== 2 passed, 7 warnings in 3.45s ========================
```

---

## 4. 后续交接与上线说明

1.  **小程序端对接**：前端可以开始调用 `GET /api/v1/checkin/today`。若返回的数据中 `data.msg` 为 `"EMPTY_LIB"` 且 `data.quote` 为 `null`，说明数据库格言库为空，小程序端应友好引导用户“添加第一条自定义名言”。
2.  **大盘情绪数据源**：加权挑选完全依赖于 `ods_index_daily` 中 `000001.SH`（上证综指）的盘后日线记录。云端采集任务应每日收盘后按时运行，保证数据为最新状态。
