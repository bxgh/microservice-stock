# 第 2 章修复方案

针对 4 个问题统一处理。先确认整体修复优先级,再给出具体的代码补丁。

---

## 一、问题归类与根因

| 问题 | 类型 | 根因 |
|---|---|---|
| 1. 风格因子定义错误 | 数据建模 | Antigravity 实施时偏离设计文档,自创了 5 因子方案 |
| 2. 题材榜单未实现 | 前端缺失 | 第 2 章 ADS 概念表 + 前端组件都未交付 |
| 3. 行业领涨股无值 | 计算 SQL 未跑 | E2-S1 步骤 3 的 UPDATE 没执行,或字段未映射到接口 |
| 4. 概念表数据不全 | 数据采集缺失 | `ods_concept_kline_daily` 没采集 |
| 5. 5/20 日累计未算 | 计算 SQL 未跑 | E2-S1 / E2-S3 中的 5/20 日相关 UPDATE 没执行 |

**根本结论:** Antigravity 实施时**没有完整执行第 2 章的 6 个 SQL 步骤**,且**前端有自创成分**(5 风格因子)。

---

## 二、修复路径

### 修复优先级

```
P0 立即修(影响功能):
  ├─ 风格因子改回方案 A(4 个公开指数因子)
  └─ 行业领涨股 SQL 重跑

P1 本章必补(影响完整性):
  ├─ 概念表 ods_concept_kline_daily 采集启动
  ├─ 题材榜单前端组件补上
  └─ 5/20 日累计 SQL 重跑

P2 数据回补(后续运行):
  └─ 行业 / 概念 / 风格因子至少回补 25 个交易日(覆盖 20 日累计)
```

---

## 三、修复方案 1:风格因子改回方案 A

### 3.1 清空当前错误数据

```sql
-- 清空当前的 5 因子配置和派生数据
DELETE FROM `ads_l2_style_factor`;
DELETE FROM `dim_style_factor`;
```

### 3.2 重新初始化 4 个因子(方案 A)

```sql
INSERT INTO `dim_style_factor`
  (factor_code, factor_name, long_index, long_name, short_index, short_name, description, display_order, is_active)
VALUES
  ('large_vs_small',
   '市值风格',
   '000300.SH', '沪深 300',
   '932000.CSI', '中证 2000',
   '大盘 vs 小盘,正值表示大盘强势',
   1, 1),

  ('value_vs_growth',
   '估值风格',
   '000919.CSI', '300 价值',
   '000918.CSI', '300 成长',
   '价值 vs 成长,正值表示价值股占优',
   2, 1),

  ('dividend_vs_micro',
   '防御进攻',
   '000922.CSI', '中证红利',
   '8841431.WI', '万得微盘股',
   '红利 vs 微盘,正值表示防御占优',
   3, 1),

  ('north_vs_south',
   '稳健成长',
   '000001.SH', '上证综指',
   '399006.SZ', '创业板指',
   '上证 vs 创业板,反映风险偏好',
   4, 1);
```

### 3.3 数据可获得性验证(供 Antigravity 测试)

执行下面 SQL 检查 4 个因子涉及的 8 个指数代码是否都能在 `ods_index_daily` 中找到:

```sql
SELECT
    f.factor_code,
    f.long_index,
    f.short_index,
    (SELECT COUNT(*) FROM `ods_index_daily` WHERE ts_code = f.long_index)  AS long_rows,
    (SELECT COUNT(*) FROM `ods_index_daily` WHERE ts_code = f.short_index) AS short_rows
FROM `dim_style_factor` f
WHERE f.is_active = 1;
```

**预期结果:** 4 行返回值,每行 `long_rows` 和 `short_rows` 都 > 0。

**特殊处理:**
- `932000.CSI` 中证 2000 指数:Tushare 实际代码可能是 `932000.SH`,**Antigravity 需要试一下两种代码哪个有数据**
- `000919.CSI` 沪深 300 价值、`000918.CSI` 沪深 300 成长:实际可能是 `.SH` 后缀
- `8841431.WI` 万得微盘股:**Tushare 大概率拉不到**,**Antigravity 验证后,如果不可用,请通知调整**(下面给替代方案)

### 3.4 万得微盘股 fallback 方案

如果 `8841431.WI` 在 Tushare 中确实拉不到,**临时禁用第 3 因子**,等数据源到位再启用:

```sql
UPDATE `dim_style_factor` SET is_active = 0 WHERE factor_code = 'dividend_vs_micro';
```

或者**用国证 2000 替代万得微盘股**(差别小,均反映小盘):

```sql
UPDATE `dim_style_factor`
SET short_index = '399303.SZ',
    short_name = '国证 2000',
    description = '红利 vs 国证 2000,正值表示防御占优'
WHERE factor_code = 'dividend_vs_micro';
```

### 3.5 清理后重跑 SQL

按第 2 章 E2-S3 的 SQL 重跑当日风格因子计算。**必须确保 5/20 日 JOIN 部分跑出来**,要点:

```sql
-- 检查重跑后的数据(应该有 4 行,且 spread_5d / spread_20d 不为 NULL)
SELECT trade_date, factor_code, factor_name,
       long_pct, short_pct, spread_today,
       spread_5d, spread_20d, direction
FROM `ads_l2_style_factor`
WHERE trade_date = '2026-04-27';
```

---

## 四、修复方案 2:行业领涨股 SQL 补跑

### 4.1 检查当前数据状态

```sql
SELECT trade_date, industry_code, industry_name,
       top_stock_code, top_stock_name, top_stock_pct
FROM `ads_l2_industry_daily`
WHERE trade_date = '2026-04-27'
LIMIT 10;
```

如果 `top_stock_*` 字段都是 NULL,说明 E2-S1 步骤 3 没跑。

### 4.2 单独重跑领涨股 UPDATE(无需重跑整个 E2-S1)

```sql
-- ============================================
-- 单独修复领涨股(适用于 ads_l2_industry_daily 已有数据但 top_stock_* 为 NULL 的情况)
-- ============================================

-- 步骤 1:清空旧值(避免污染)
UPDATE `ads_l2_industry_daily`
SET top_stock_code = NULL,
    top_stock_name = NULL,
    top_stock_pct = NULL
WHERE trade_date = :target_date;

-- 步骤 2:行业内涨幅 Top1 填充
UPDATE `ads_l2_industry_daily` o
INNER JOIN (
    SELECT
        sw.l1_code AS industry_code,
        SUBSTRING_INDEX(
            GROUP_CONCAT(k.code ORDER BY k.pct_chg DESC),
            ',', 1
        ) AS top_code,
        MAX(k.pct_chg) AS top_pct
    FROM `stock_kline_daily` k
    INNER JOIN `stock_industry_sw` sw ON k.code = sw.code
    WHERE k.trade_date = :target_date
      AND k.trade_status = 1
      AND sw.l1_code IS NOT NULL
    GROUP BY sw.l1_code
) t ON o.industry_code = t.industry_code
LEFT JOIN `stock_basic_info` sb ON sb.ts_code = t.top_code
SET
    o.top_stock_code = t.top_code,
    o.top_stock_name = sb.name,
    o.top_stock_pct  = t.top_pct
WHERE o.trade_date = :target_date;
```

### 4.3 关键检查点

#### 检查点 A:`stock_industry_sw.l1_code` 与 `ads_l2_industry_daily.industry_code` 是否一致?

```sql
-- 若以下查询返回 0 行,说明两边代码格式不同(一个带 .SI 后缀,另一个没带)
SELECT DISTINCT industry_code FROM `ads_l2_industry_daily`
WHERE trade_date = :target_date
  AND industry_code NOT IN (SELECT DISTINCT l1_code FROM `stock_industry_sw`);
```

如果有差异,需在 SQL JOIN 中用字符串处理对齐:
```sql
-- 例如 ads_l2_industry_daily.industry_code = '801010.SI'
-- 而 stock_industry_sw.l1_code = '801010'
-- JOIN 时需要:
ON SUBSTRING_INDEX(o.industry_code, '.', 1) = sw.l1_code
```

#### 检查点 B:`stock_kline_daily.code` 与 `stock_basic_info.ts_code` 是否一致?

```sql
-- 若以下查询返回大量结果,说明两边代码格式不同
SELECT k.code
FROM `stock_kline_daily` k
LEFT JOIN `stock_basic_info` sb ON k.code = sb.ts_code
WHERE k.trade_date = :target_date
  AND sb.ts_code IS NULL
LIMIT 10;
```

如果不一致(例如 `stock_kline_daily.code = '600519'` 而 `stock_basic_info.ts_code = '600519.SH'`),需要修改 JOIN 条件给 `code` 拼后缀:
```sql
LEFT JOIN `stock_basic_info` sb
  ON sb.ts_code = CONCAT(t.top_code,
                         CASE
                           WHEN t.top_code LIKE '6%' THEN '.SH'
                           WHEN t.top_code LIKE '0%' OR t.top_code LIKE '3%' THEN '.SZ'
                           WHEN t.top_code LIKE '8%' OR t.top_code LIKE '4%' THEN '.BJ'
                         END)
```

---

## 五、修复方案 3:概念数据采集 + 题材榜单前端

### 5.1 数据采集需求(交付 Antigravity)

补建 `ods_concept_kline_daily`(第 2 章 E1-S2 的 SQL 已给出),然后**采集任务最低要求**:

```yaml
采集任务: ods_concept_kline_daily
数据源: akshare stock_board_concept_hist_ths
触发时机: T 日 16:30 后
回补深度: 至少 25 个交易日(覆盖 20 日累计计算)
关键字段验证:
  - concept_code 与 stock_sector_ths.id 是否能 JOIN(可能需要做映射)
  - 字段单位:涨跌幅是否需要 / 100
```

### 5.2 概念聚合 SQL(基于已采集的 ODS)

第 2 章 E2-S2 的 SQL 不变,数据采到位后直接跑。

### 5.3 前端补:题材榜单组件

#### 5.3.1 wxml(添加在风格因子之后)

```xml
<!-- pages/dashboard/components/concept-ranking.wxml -->
<view class="card">
  <view class="card-side-bar"></view>
  <view class="card-header">
    <view class="card-title-cn">题材榜单</view>
    <view class="card-title-en">THEMES</view>
  </view>

  <view class="concept-list" wx:if="{{concepts.length > 0}}">
    <view class="concept-row" wx:for="{{concepts}}" wx:key="code">
      <view class="concept-rank mono">{{item.rank}}</view>
      <view class="concept-main">
        <view class="concept-name-row">
          <text class="concept-name">{{item.name}}</text>
          <text class="concept-tag tag-{{item.theme_label}}"
                wx:if="{{item.theme_label}}">
            {{item.theme_label_cn}}
          </text>
        </view>
        <view class="concept-meta">
          <text class="meta-pct mono {{item.pct_value >= 0 ? 'up' : 'down'}}">
            {{item.pct_value >= 0 ? '↑' : '↓'}} {{item.pct}}
          </text>
          <text class="meta-sep">·</text>
          <text class="meta-zt">涨停 {{item.limit_up_count}}/{{item.constituent_count}}</text>
          <text class="meta-sep">·</text>
          <text class="meta-persistence">{{item.persistence_display}}</text>
        </view>
      </view>
    </view>
  </view>

  <view class="empty-state" wx:else>
    <text class="empty-text">题材数据采集中</text>
  </view>
</view>
```

#### 5.3.2 wxss(用 v2 字号变量)

```css
/* 题材榜单 */
.concept-list {
  display: flex;
  flex-direction: column;
}
.concept-row {
  display: flex;
  align-items: flex-start;
  padding: var(--sp-row-gap) 0;
  border-bottom: 1rpx solid var(--hair);
}
.concept-row:last-child { border-bottom: none; }

.concept-rank {
  flex: 0 0 60rpx;
  font-size: var(--fs-body);
  color: var(--amber);
  font-weight: 600;
  padding-top: 4rpx;
}
.concept-main { flex: 1; min-width: 0; }

.concept-name-row {
  display: flex;
  align-items: center;
  margin-bottom: var(--sp-block-gap);
  flex-wrap: wrap;
}
.concept-name {
  font-size: var(--fs-body);
  color: var(--ink);
  margin-right: 12rpx;
  font-weight: 500;
}

.concept-tag {
  font-size: var(--fs-mini);
  padding: 2rpx 12rpx;
  border-radius: 2rpx;
  letter-spacing: 1rpx;
}
.tag-main_theme {
  background: rgba(212, 162, 62, 0.2);
  color: var(--amber-bright);
  border: 1rpx solid var(--amber);
}
.tag-follow_up {
  background: rgba(138, 181, 115, 0.15);
  color: var(--strong);
  border: 1rpx solid rgba(138, 181, 115, 0.3);
}
.tag-one_day {
  background: rgba(217, 122, 61, 0.15);
  color: var(--alert);
  border: 1rpx solid rgba(217, 122, 61, 0.3);
}
.tag-declining {
  background: rgba(119, 109, 88, 0.2);
  color: var(--ink-mute);
  border: 1rpx solid var(--hair);
}

.concept-meta {
  display: flex;
  align-items: center;
  font-size: var(--fs-aux);
  color: var(--ink-dim);
  flex-wrap: wrap;
}
.meta-pct { font-weight: 600; }
.meta-sep { color: var(--ink-mute); margin: 0 8rpx; }
.meta-zt {}
.meta-persistence {}

.empty-state {
  padding: 60rpx 20rpx;
  text-align: center;
}
.empty-text {
  font-size: var(--fs-body);
  color: var(--ink-mute);
}
```

#### 5.3.3 后端接口契约(扩展)

第 2 章设计的 `/api/dashboard/l2` 接口,补充 `concept` 节点的字段加工逻辑:

```javascript
// 后端返回的 concept.top10 数据结构
[
  {
    rank: 1,
    code: 'BK0900',
    name: '人形机器人',
    pct: '5.23%',                  // 字符串展示用
    pct_value: 0.0523,             // 数字版本(前端判断颜色)
    limit_up_count: 8,
    constituent_count: 45,
    persistence_score: 0.9,        // 0-1 数字
    persistence_display: '主线持续', // 后端转中文(0.8+ → '主线持续' / 0.6+ → '延续' / 0.3+ → '一日游' / NULL → '数据不足')
    theme_label: 'main_theme',
    theme_label_cn: '主线'         // 后端转中文(main_theme → '主线' / follow_up → '跟风' / one_day → '一日游' / declining → '退潮')
  },
  // ... 共 10 行
]
```

**theme_label_cn 转换规则:**

```python
LABEL_MAP = {
    'main_theme': '主线',
    'follow_up':  '跟风',
    'one_day':    '一日游',
    'declining':  '退潮',
}

PERSISTENCE_MAP = lambda score: (
    '主线持续' if score >= 0.8 else
    '延续'     if score >= 0.6 else
    '一日游'   if score >= 0.3 else
    '数据不足'  # score is None
)
```

---

## 六、修复方案 4:5/20 日累计 SQL 重跑

### 6.1 风格因子的 5/20 日

第 2 章 E2-S3 的 SQL **必须包含 5/20 日的 JOIN 部分**,而不是只跑当日。如果当前数据空,大概率是 Antigravity 跑了简化版(只有 spread_today 没有 spread_5d/20d)。

**修复:** 完整重跑 E2-S3 SQL(原文档已含 5/20 日逻辑)。

### 6.2 行业的 5/20 日排名

行业表的 `rank_5d` / `rank_20d` / `rank_diff_5d` 是后续做"动量上升 / 下降"判断的核心,如果未跑,需要重跑 E2-S1 步骤 5、6。

**修复后验证:**
```sql
SELECT trade_date, industry_name,
       rank_today, rank_5d, rank_20d, rank_diff_5d
FROM `ads_l2_industry_daily`
WHERE trade_date = '2026-04-27'
ORDER BY rank_today;
```

### 6.3 历史数据回补要求

5 日累计需要历史 5 日,20 日需要历史 20 日。**必须先回补再算。**

```yaml
回补优先级清单:
  ods_index_daily:           至少回补 25 交易日(覆盖 20 日累计)
                             建议直接回补 5 年,这是基础数据
  ods_sw_index_daily:        至少回补 25 交易日
                             建议直接回补 5 年
  ods_concept_kline_daily:   至少回补 25 交易日
                             历史 3 年起步
  ads_l2_*:                  在 ODS 回补完后,按交易日历循环跑 ADS 计算 SQL
                             覆盖最近 30 个交易日即可启动展示
```

---

## 七、修复执行顺序(给 Antigravity 的 checklist)

```
┌─ Phase 1: 数据采集补齐(2-3 天)─────────────────┐
│                                                  │
│ 1. 启动 ods_concept_kline_daily 采集任务          │
│ 2. 检查 ods_sw_index_daily 是否已有 25 日历史    │
│ 3. 检查 ods_index_daily 是否已有 25 日历史       │
│                                                  │
│ ⚠ 若历史不足,先回补再走 Phase 2                 │
└──────────────────────────────────────────────────┘

┌─ Phase 2: 风格因子修复(0.5 天)─────────────────┐
│                                                  │
│ 1. 执行第 3.1 节的清空 SQL                       │
│ 2. 执行第 3.2 节的 4 因子 INSERT SQL             │
│ 3. 执行第 3.3 节的可获得性验证 SQL               │
│ 4. 若万得微盘股不可用,执行 3.4 节 fallback       │
│ 5. 完整重跑 E2-S3 SQL(含 5/20 日)               │
│ 6. 验证 ads_l2_style_factor 有 4 行且字段非空    │
└──────────────────────────────────────────────────┘

┌─ Phase 3: 行业领涨股修复(0.5 天)───────────────┐
│                                                  │
│ 1. 执行第 4.1 节诊断查询                          │
│ 2. 执行第 4.3 节检查点 A 验证 industry_code 一致 │
│ 3. 执行第 4.3 节检查点 B 验证 stock code 一致    │
│ 4. 根据结果调整第 4.2 节 SQL 后执行              │
│ 5. 验证 top_stock_name 字段有值                  │
└──────────────────────────────────────────────────┘

┌─ Phase 4: 行业 5/20 日排名修复(0.5 天)─────────┐
│                                                  │
│ 1. 完整重跑 E2-S1 步骤 5、6 SQL                  │
│ 2. 验证 rank_5d / rank_20d / rank_diff_5d 非空   │
└──────────────────────────────────────────────────┘

┌─ Phase 5: 概念榜单(1-2 天)──────────────────────┐
│                                                  │
│ 1. ods_concept_kline_daily 采集到位后,跑 E2-S2  │
│ 2. 验证 ads_l2_concept_daily 当日数据 ≥ 350 行   │
│ 3. 后端接口加 concept 节点(第 5.3.3 节)         │
│ 4. 前端添加题材榜单组件(第 5.3.1 / 5.3.2 节)    │
└──────────────────────────────────────────────────┘

┌─ Phase 6: 历史回补(1-2 天)─────────────────────┐
│                                                  │
│ 按第 6.3 节回补优先级清单执行                     │
│ 完成后 Phase 1-5 数据全部完整                    │
└──────────────────────────────────────────────────┘
```

**总耗时预估:** 4–7 个工作日(取决于历史回补深度)

---

## 八、最关键的 3 个验证 SQL(修复完成后必跑)

```sql
-- ============================================
-- 验证 1:风格因子 4 行齐全,数据完整
-- ============================================
SELECT
    factor_code, factor_name,
    long_pct, short_pct, spread_today,
    spread_5d, spread_20d, direction
FROM `ads_l2_style_factor`
WHERE trade_date = :target_date;
-- 期望:返回 4 行(若万得微盘股 fallback 则 3 行),
--       所有 spread_today 非 NULL,spread_5d/20d 非 NULL


-- ============================================
-- 验证 2:行业领涨股完整,排名变化齐全
-- ============================================
SELECT
    industry_name, pct_chg,
    rank_today, rank_5d, rank_20d, rank_diff_5d,
    top_stock_code, top_stock_name, top_stock_pct
FROM `ads_l2_industry_daily`
WHERE trade_date = :target_date
ORDER BY rank_today
LIMIT 10;
-- 期望:31 行,top_stock_name / rank_5d / rank_diff_5d 非空


-- ============================================
-- 验证 3:概念表数据齐全,Top10 标签准确
-- ============================================
SELECT
    rank_today, concept_name,
    pct_chg, limit_up_count, constituent_count,
    persistence_score, theme_label
FROM `ads_l2_concept_daily`
WHERE trade_date = :target_date
  AND rank_today <= 10
ORDER BY rank_today;
-- 期望:10 行,theme_label 非空,Top5 中应有 main_theme 标签
```

---

## 九、给 Antigravity 的工作建议

**建议在新对话或工作分配文档里强调以下两点,避免再次出现实施偏差:**

1. **数据建模决策必须遵循设计文档**——不可自创因子或字段,有疑问优先反馈
2. **每个 ADS 计算 SQL 必须完整执行所有步骤**,而不是只跑当日聚合,跳过 5/20 日的 UPDATE 步骤会导致后续指标全部失效

如果 Antigravity 是 AI 工具,建议在系统提示中加一条:**"按设计文档原文实施,任何偏离需要先和用户确认"**。

---

## 完成

修复完成后,第 2 章效果会从当前的 75% 提升到 95%+。剩余的 P6 细节(文案优化、布局微调)可以滚动迭代,不阻塞下一章节。

如果修复过程中遇到 SQL 报错或数据异常,请把具体错误贴出来,我可以针对性给补丁。
。