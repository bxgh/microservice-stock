# [Story E23-S2] 每日格言智能轮询与日内锁定 API · 实施计划书

本计划书规划了每日格言打卡子系统 **E23-S2** 阶段的详细物理设计与技术实施路径，旨在提供工业级、支持高可用的日内格言幂等锁定、情绪对齐加权轮询以及冷启动兜底机制。

## User Review Required

> [!IMPORTANT]
> **业务时间分界线 (凌晨 4:00 规则)**
> 考虑到投资者的反思习惯，夜间打卡往往延续至凌晨。系统采用凌晨 **04:00** 作为格言更新的物理切分点：
> - 当前时间为 `03:30` -> 业务日期归属为**前一天**。
> - 当前时间为 `04:15` -> 业务日期归属为**今天**。
> - 系统将基于 `Asia/Shanghai` 时区进行高精度时钟运算。

> [!WARNING]
> **多并发冷启动防穿透**
> 当小程序启动且格言库为空时，首批进站的用户并发调用 `GET /today`。系统必须在 `diary_checkin_lock` 中写入 `locked_target_id = NULL` 占位记录，实现日内空值锁定，杜绝并发下数据库被反复扫描重试。

---

## Proposed Changes

本期 Story E23-S2 开发聚焦于 `wxch-gateway` 的服务层与 API 路由层。

### [wxch-gateway Backend Component]

#### [MODIFY] [app/services/checkin_service.py](file:///e:/gitee/microservice-stock/wxch-gateway/app/services/checkin_service.py)
在服务层新增并实现以下核心业务方法：
1. **`get_business_date(now: datetime) -> date`**：
   - 提取当前上海时区时间，判定若 `now.hour < 4`，返回 `(now - timedelta(days=1)).date()`，否则返回 `now.date()`。
2. **`select_daily_quote(user_id: int, business_date: date) -> Optional[dict]`**：
   - 从 `diary_quote_lib` 查询所有未删除格言（`is_deleted = 0`）。
   - 从 `diary_quote_user_state` 查询当前用户的行为记录：
     - 排除 `is_disliked = 1`（永久屏蔽）的格言。
     - 排除最近 30 天内曾曝光过的格言（`last_exposed_at >= business_date - 30 days`）。
   - 计算加权得分：
     - 初始权重 = 格言主表 `base_weight`。
     - 连续跳过扣权：`weight = max(1, base_weight - consecutive_skip_count * 10)`。
     - 收藏加权：如果 `is_favorited = 1`，则 `weight += 20`。
     - 大盘指数对齐加权：从 `ods_index_daily` 检索上证指数（`000001.SH`）最近交易日的涨跌幅 `pct_chg`：
       - 若 `pct_chg >= 0.005`（大盘大涨），则 Category 1 (经典名言/进取) 与 Category 3 (心态/纪律) 权重增加 `+15`。
       - 若 `pct_chg <= -0.005`（大盘大跌），则 Category 2 (大佬语录/防守) 与 Category 3 (心态/纪律) 权重增加 `+15`。
   - 使用加权轮询概率算法（`random.choices`）进行最终格言挑选。
3. **`get_or_lock_today_quote(user_id: int) -> TodayQuoteResponseData`**：
   - 计算业务日期 `business_date`。
   - 查询 `diary_checkin_lock` 确认用户今日是否已锁定：
     - 若已存在锁记录且 `locked_target_id` 不为空，则读取格言库详情，补充 `is_favorited` 状态及该格言下用户最新的 `history_insight`（历史见解，读取自 `diary_entry` 最新心得）。
     - 若锁记录存在 but `locked_target_id IS NULL`，返回 `EMPTY_LIB` 状态。
     - 若不存在锁：
       - 执行 `select_daily_quote()`。
       - 若选出格言，原子写入 `diary_checkin_lock` 锁记录（`locked_target_id = quote_id, status = 0`），并在 `diary_quote_user_state` 中累加 `expose_count = expose_count + 1`，更新 `last_exposed_at`。
       - 若无可用格言（冷启动空库），原子写入 `diary_checkin_lock` 锁记录（`locked_target_id = NULL, status = 0`），返回 `EMPTY_LIB`。

#### [MODIFY] [app/api/checkin.py](file:///e:/gitee/microservice-stock/wxch-gateway/app/api/checkin.py)
实现预留的 `GET /api/v1/checkin/today` 路由方法：
- 注入 `user_id: int = Depends(get_current_user_id)`。
- 调用 `checkin_service.get_or_lock_today_quote(user_id)`。
- 组装并返回 `TodayQuoteResponse`。

---

## Verification Plan

我们将在 `wxch-gateway/scripts/testing/test_checkin.py` 中增量编写高度密集的场景断言：

### Automated Tests
1. **冷启动防穿透测试**：
   - 清空 `diary_quote_lib`（或使用测试用户隔绝匹配）。
   - 连续调用 2 次 `GET /api/v1/checkin/today`。
   - 预期返回状态码 `200`，`msg` 包含 `"EMPTY_LIB"`，`quote` 字段为 `None`。
   - 查验数据库中新增了一条 `locked_target_id IS NULL` 的锁记录，证明空锁机制生效。
2. **幂等锁定与日内防闪烁测试**：
   - 手工录入格言 A、格言 B。
   - 首次调用 `GET /api/v1/checkin/today`，挑选其中一条并返回（假设为格言 A）。
   - 第二次调用该接口，预期返回的仍是格言 A（锁定生效）。
   - 查验锁定表 `diary_checkin_lock` 与用户状态表 `expose_count` 和 `last_exposed_at` 正确更新。
3. **加权轮询算法测试**：
   - 伪造大盘指数数据（写入 `ods_index_daily` 临时测试记录）：
     - 场景 A：上证指数大跌 2.5% -> 校验“防守型格言”被抽中概率显著提升。
     - 场景 B：上证指数大涨 1.8% -> 校验“纪律/进取型格言”被抽中概率显著提升。
4. **凌晨 4:00 时间切分测试**：
   - 注入 Mock 时钟，校验凌晨 3:59 判归为前一天，凌晨 4:01 判归为今天。

### 运行测试命令
```bash
python -m pytest -v wxch-gateway/scripts/testing/test_checkin.py
```
