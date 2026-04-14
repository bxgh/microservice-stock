# 股东数据 数据库结构

存储位置：腾讯云 MySQL 数据库。

## 1. 股东户数表 (`stock_shareholder_count`)
记录公司随时间推移的股东人数变化。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增ID | 主键 |
| `ts_code` | VARCHAR(20) | 股票代码 | 索引 |
| `end_date` | DATE | 截止日期 | 索引 |
| `holder_count` | INT | 股东户数 | |
| `holder_change_pct`| DECIMAL(24,6)| 户数变动比例 | 支持大比例变动 (如新股) |
| `avg_market_cap` | DECIMAL(20,2)| 户均持股市值 | 单位：元 |
| `updated_at` | TIMESTAMP | 更新时间 | 自动更新 |

- **唯一约束**: `uk_code_date (ts_code, end_date)`
- **主要查询**: 按 `ts_code` 倒序查询历史。

## 2. 前十大股东表 (`stock_top10_shareholders`)
记录各季度报告披露的前十大流通股东详情。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增ID | 主键 |
| `ts_code` | VARCHAR(20) | 股票代码 | 索引 |
| `end_date` | DATE | 截止日期 | 索引 |
| `rank` | INT | 排名 | 1-10 |
| `holder_name` | VARCHAR(255) | 股东名称 | 前20字符索引 |
| `share_type` | VARCHAR(50) | 股份类型 | |
| `hold_count` | BIGINT(20) | 持股数量 | 单位：股 |
| `hold_pct` | DECIMAL(10,4)| 持股比例 | 单位：% |
| `change_stat` | VARCHAR(50) | 变动状态 | 增减持、新进等 |
| `updated_at` | TIMESTAMP | 更新时间 | |

- **唯一约束**: `uk_code_date_rank (ts_code, end_date, rank)`
- **主要查询**: 给定 `ts_code` 和 `end_date` 查询排名前10的名单。

---

## 3. 技术优化
- **字段扩容**: `holder_change_pct` 采用 `DECIMAL(24,6)` 是为了应对极其特殊情况下（如公司分立、回购注销、新股上市初期）可能出现的超大变动比例，防止数据库溢出报错。
- **并发控制**: 写入时使用 `ON DUPLICATE KEY UPDATE`，确保多次同步同一份数据时不会产生冗余，且能更新旧数据。

## 3. 限售股解禁表 (`stock_restricted_release`)
记录限售股解禁历史及未来计划。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增ID | 主键 |
| `ts_code` | VARCHAR(20) | 股票代码 | 索引 |
| `release_date` | DATE | 解禁日期 | 索引 |
| `release_count` | BIGINT | 解禁数量 | 单位：股 |
| `release_market_cap` | DECIMAL(20,2)| 解禁市值 | 单位：元 |
| `ratio` | DECIMAL(10,4)| 占流通市值比 | |
| `holder_type` | VARCHAR(100) | 限售类型 | |

- **唯一约束**: `uk_code_date_type (ts_code, release_date)` (实际索引可能仅为 code+date)

## 4. 大宗交易每日明细表 (`stock_block_trade`)
记录逐笔大宗交易明细。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增ID | 主键 |
| `ts_code` | VARCHAR(20) | 股票代码 | 索引 |
| `trade_date` | DATE | 交易日期 | 索引 |
| `price` | DECIMAL(10,2) | 成交价 | |
| `volume` | DECIMAL(20,2) | 成交量 | 单位：股 |
| `amount` | DECIMAL(20,2) | 成交额 | 单位：元 |
| `buyer` | VARCHAR(255) | 买方营业部 | |
| `seller` | VARCHAR(255) | 卖方营业部 | |

- **索引**: `idx_trade_date`, `idx_ts_code` (无唯一约束，允许单日多笔)

## 5. 龙虎榜每日明细表 (`stock_lhb_daily`)
记录龙虎榜每日汇总及机构博弈数据。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增ID | 主键 |
| `ts_code` | VARCHAR(20) | 股票代码 | 索引 |
| `trade_date` | DATE | 交易日期 | 索引 |
| `close_price` | DECIMAL(10,4) | 收盘价 | |
| `change_pct` | DECIMAL(10,4) | 涨跌幅 | |
| `turnover_rate` | DECIMAL(10,4) | 换手率 | |
| `net_buy_amt` | DECIMAL(20,2) | 龙虎榜净买额 | |
| `reason` | TEXT | 上榜原因 | |
| `inst_net_buy_amt` | DECIMAL(20,2) | 机构净买入 | |
| `inst_buy_count` | INT | 买入机构数 | |
| `inst_sell_count` | INT | 卖出机构数 | |

- **唯一约束**: `uk_code_date (ts_code, trade_date)`

## 6. 北向资金每日持股表 (`stock_north_funds_daily`)
记录沪深股通每日个股持仓。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增ID | 主键 |
| `ts_code` | VARCHAR(20) | 股票代码 | 索引 |
| `trade_date` | DATE | 交易日期 | 索引 |
| `hold_count` | BIGINT | 持股数量 | |
| `hold_market_cap` | DECIMAL(20,2) | 持股市值 | |
| `hold_ratio` | DECIMAL(10,4) | 持股占比 | |

- **唯一约束**: `uk_code_date (ts_code, trade_date)`

## 7. 机构评级表 (`stock_analyst_rank`)
记录分析师/机构对个股的评级变动，用于计算信息维度 $I_{analyst}$。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增ID | 主键 |
| `stock_code` | VARCHAR(20) | 股票代码 | |
| `report_date` | DATE | 研报日期 | |
| `analyst` | VARCHAR(50) | 机构/分析师 | |
| `rating` | VARCHAR(20) | 评级 | 买入/增持等 |
| `change_direction` | VARCHAR(10) | 变动 | 维持/上调/下调 |
| `target_price` | DECIMAL(10,2) | 目标价 | |

- **唯一约束**: `uk_code_date_analyst (stock_code, report_date, analyst)`

## 8. 业绩预告表 (`stock_performance_forecast`)
记录上市公司业绩预告，用于捕捉预期差 $I_{forecast}$。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增ID | 主键 |
| `stock_code` | VARCHAR(20) | 股票代码 | |
| `notice_date` | DATE | 公告日期 | |
| `report_period` | DATE | 报告期 | 财报截止日 |
| `type` | VARCHAR(20) | 类型 | 预增/预减/扭亏等 |
| `growth_min` | DECIMAL(10,2) | 增长下限(%) | |
| `growth_max` | DECIMAL(10,2) | 增长上限(%) | |

- **唯一约束**: `uk_code_period (stock_code, report_period)`

## 9. 市场热度统计表 (`stock_sentiment_daily`)
记录股吧等社区的每日关注度元数据，用于计算散户情绪 $I_{buzz}$。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增ID | 主键 |
| `stock_code` | VARCHAR(20) | 股票代码 | |
| `trade_date` | DATE | 交易日期 | |
| `post_count` | INT | 发帖量 | 统计样本内 |
| `read_count` | INT | 阅读量 | 统计样本内 |
| `comment_count` | INT | 评论量 | 统计样本内 |
| `rank_score` | INT | 热度排名 | |

- **唯一约束**: `uk_code_date (stock_code, trade_date)`

## 10. 停牌数据表 (`stock_suspensions`)
记录股票每日停牌状态。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增ID | 主键 |
| `ts_code` | VARCHAR(20) | 股票代码 | 标准后缀格式 (如 `300912.SZ`) |
| `trade_date` | DATE | 停牌日期 | |
| `is_suspended` | TINYINT | 是否停牌 | 1=是 |
| `reason` | VARCHAR(255) | 停牌原因 | |

- **唯一约束**: `uk_code_date (ts_code, trade_date)`

## 11. 早盘数据 (Pre-Market)

### 11.1 业绩预告表 (`stock_performance_forecast`)
记录上市公司发布的业绩预告、快报信息。

| 字段名 | 类型 | 说明 | 备注 |
| :--- | :--- | :--- | :--- |
| `id` | INT | 自增ID | |
| `ts_code` | VARCHAR(20) | 股票代码 | 标准后缀 (如 `000001.SZ`) |
| `report_period` | DATE | 报告期 | 如 `2025-12-31` |
| `notice_date` | DATE | 公告日期 | |
| `type` | VARCHAR(255) | 预告类型 | "预增", "扭亏" 等 |
| `growth_range` | VARCHAR(255) | 变动幅度 | "50% - 80%" |

- **唯一约束**: `uk_code_period (ts_code, report_period)`

### 11.2 除权除息日程表 (`stock_xr_schedules`)
记录股票的除权除息日信息。

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `ts_code` | VARCHAR(20) | 股票代码 |
| `ex_date` | DATE | 除权除息日 |
| `bonus_ratio` | DECIMAL(10,4) | 送转比例 |
| `cash_div` | DECIMAL(10,4) | 派现金额 |

- **唯一约束**: `uk_code_date (ts_code, ex_date)`

---

## 12. 数据标准

### 股票代码格式 (Stock Code Format)
全系统数据库表统一遵循 **标准后缀格式**：
*   **字段名**: 通常命名为 `ts_code` 或 `stock_code`。
*   **格式**: `数字代码.后缀` (如 `603288.SH`, `301633.SZ`, `430047.BJ`)。
*   **清洗规则**: 废弃所有旧有前缀格式 (如 `sh.600000`)。存量数据已通过 `robust_migrate_codes.py` 脚本统一迁移。

## 13. 行业分类数据 (Industry Metadata)

### 13.1 申万行业 (`stock_industry_sw`)
记录申万一级、二级、三级行业分类。

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `code` | VARCHAR(20) | 股票代码 (PK) |
| `l1_code` | VARCHAR(20) | 一级行业代码 |
| `l1_name` | VARCHAR(50) | 一级行业名称 |
| `l2_code` | VARCHAR(20) | 二级行业代码 |
| `l2_name` | VARCHAR(50) | 二级行业名称 |
| `l3_code` | VARCHAR(20) | 三级行业代码 |
| `l3_name` | VARCHAR(50) | 三级行业名称 |
| `l3_name` | VARCHAR(50) | 三级行业名称 |

### 13.2 同花顺行业 (`stock_industry_ths`) - **首选**
记录同花顺一级、二级、三级行业分类。通过问财接口全量获取，由于其概念细分度高，作为系统首选行业归类。

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `id` | INT | 自增主键 |
| `ts_code` | VARCHAR(20) | 股票代码 (唯一约束) |
| `l1_name` | VARCHAR(50) | 同花顺一级行业名称 |
| `l2_name` | VARCHAR(50) | 同花顺二级行业名称 |
| `l3_name` | VARCHAR(50) | 同花顺三级行业名称 |
| `updated_at` | TIMESTAMP | 最后更新时间 |

- **唯一约束**: `uk_code (ts_code)`

### 13.3 同花顺板块字典 (`stock_sector_ths`)
存储所有发现的板块名称及其类型（行业或概念）。

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `id` | INT | 自增主键 |
| `sector_name` | VARCHAR(50) | 板块/概念/行业名称 |
| `sector_type` | ENUM | 板块类型 ('industry', 'concept') |
| `sector_level` | VARCHAR(20) | 行业级别 (针对行业类型) |
| `updated_at` | TIMESTAMP | 最后更新时间 |

- **唯一约束**: `uk_name_type (sector_name, sector_type)`

### 13.4 同花顺成分表 (`stock_sector_cons_ths`)
存储板块（主要是概念）与股票的多对多关系。

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `id` | INT | 自增主键 |
| `ts_code` | VARCHAR(20) | 股票代码 |
| `sector_id` | INT | 板块ID (关联 `stock_sector_ths.id`) |
| `updated_at` | TIMESTAMP | 最后更新时间 |

- **唯一约束**: `uk_code_sector (ts_code, sector_id)`
- **索引**: `idx_sector (sector_id)`

### 13.5 东方财富行业 (`stock_industry_em`) - **备选**
作为同花顺数据的补充与兜底方案，记录东方财富行业板块分类。

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `id` | INT | 自增主键 |
| `ts_code` | VARCHAR(20) | 股票代码 |
| `industry_code` | VARCHAR(20) | 行业代码 (如 BKxxxx) |
| `industry_name` | VARCHAR(50) | 行业名称 |
| `updated_at` | TIMESTAMP | 最后更新时间 |

- **唯一约束**: `uk_code_ind (ts_code, industry_code)`
