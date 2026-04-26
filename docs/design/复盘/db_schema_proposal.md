# 复盘数据表结构设计方案 (深度校对版)

## 1. 设计哲学
- **纵表化 (Vertical)**: 针对“多对象、易变动”的数据(指数、行业、个股),采用纵表结构,避免 DDL 变更。
- **宽表化 (Horizontal)**: 针对“单对象、多属性”的数据(市场整体流动性、宏观环境),采用宽表结构,方便单行读取。
- **ADS 层优化**: 冗余必要的行情上下文(价格、涨跌幅),实现“一站式”查询,避免大表关联。
- **工程一致性**: 统一 `fupan_` 前缀,统一 `decimal(20,4)` 金额精度,统一 `timestamp` 审计字段。

---

## 2. 表结构定义

### 2.1 市场指数表现表 (`fupan_market_index`)
**设计说明**: 纵表结构。用于存储 沪深300、中证1000、恒生指数等所有宽基与风格指数。

| 字段名 | 类型 | 约束 | 备注 |
| :--- | :--- | :--- | :--- |
| `trade_date` | `date` | `PRI` | 交易日期 |
| `ts_code` | `varchar(20)` | `PRI` | 指数代码 (如 000300.SH) |
| `index_name` | `varchar(50)` | | 指数简称 (如 沪深300) |
| `close` | `decimal(16,4)` | | 收盘价 |
| `pct_chg` | `decimal(8,4)` | | 涨跌幅 (0.0123 代表 1.23%) |
| `amount` | `decimal(20,4)` | | 成交额 (亿元) |
| `created_at` | `timestamp` | | 自动生成 |

---

### 2.2 市场流动性统计表 (`fupan_market_liquidity`)
**设计说明**: 宽表结构。记录市场整体能级趋势。

| 字段名 | 类型 | 约束 | 备注 |
| :--- | :--- | :--- | :--- |
| `trade_date` | `date` | `PRI` | 交易日期 |
| `turnover_total` | `decimal(20,4)` | | 全市场成交额 (亿元) |
| `turnover_ma5` | `decimal(20,4)` | | 5日成交均量 |
| `turnover_ma20` | `decimal(20,4)` | | 20日成交均量 |
| `turnover_pct_vs_ma20` | `decimal(8,4)` | | 相对20日均线偏离度 |
| `turnover_pctile_1y` | `decimal(6,4)` | | 近1年成交额分位数 |
| `turnover_rate_avg` | `decimal(8,4)` | | 全市场加权换手率 |
| `volume_ratio_avg` | `decimal(8,4)` | | 平均量比 |

---

### 2.3 市场情绪与统计表 (`fupan_market_sentiment`)
**设计说明**: 宽表结构。承载 L1/L4 层级的核心情绪指标。

| 字段名 | 类型 | 备注 |
| :--- | :--- | :--- |
| `trade_date` | `date` | `PRI` |
| `up_count` / `down_count` | `int` | 上涨/下跌家数 |
| `limit_up_count` / `limit_down_count` | `int` | 涨跌停家数 (不含ST) |
| `st_limit_up_count` / `st_limit_down_count` | `int` | ST 涨跌停家数 |
| `broken_board_count` | `int` | 炸板家数 |
| `broken_board_rate` | `decimal(6,4)` | 炸板率 |
| `high_60d_count` / `low_60d_count` | `int` | 创60日新高/新低家数 |
| `yesterday_zt_avg_return` | `decimal(8,4)` | 昨日涨停平均收益 |
| `max_board_height` | `int` | 最高板高度 |
| `market_regime` | `varchar(20)` | 市场风格 (普涨/普跌/结构/低量) |
| `board_ladder` | `json` | 连板梯队分布 |
| `pct_chg_distribution` | `json` | 涨跌分布直方图数据 |

---

### 2.4 行业指标表现表 (`fupan_sector_indicators`)
**设计说明**: 纵表结构。记录各行业/板块的内生广度与估值。

| 字段名 | 类型 | 约束 | 备注 |
| :--- | :--- | :--- | :--- |
| `trade_date` | `date` | `PRI` | 交易日期 |
| `ts_code` | `varchar(20)` | `PRI` | 行业代码 |
| `name` | `varchar(50)` | | 行业名称 |
| `close` | `decimal(16,4)` | | 收盘价 (指数) |
| `pct_chg` | `decimal(8,4)` | | 涨跌幅 |
| `amount` | `decimal(20,4)` | | 成交额 (亿元) |
| `amount_pct` | `decimal(6,4)` | | 成交额占全市场比例 |
| `up_count` / `down_count` | `int` | | 行业内涨跌家数对比 |
| `top_stock_code` | `varchar(20)` | | 领涨股代码 |
| `top_stock_name` | `varchar(50)` | | 领涨股名称 |
| `pe_pctile_10y` | `decimal(6,4)` | | 行业10年估值分位 |
| `momentum_score` | `decimal(8,4)` | | 动能评分 |

---

### 2.5 个股复盘指标表 (`fupan_stock_indicators`)
**设计说明**: 纵表结构。记录具有“复盘价值”的异动/热点个股。

| 字段名 | 类型 | 约束 | 备注 |
| :--- | :--- | :--- | :--- |
| `trade_date` | `date` | `PRI` | 交易日期 |
| `ts_code` | `varchar(20)` | `PRI` | 股票代码 |
| `name` | `varchar(50)` | | 股票名称 |
| `close` | `decimal(16,4)` | | 收盘价 |
| `pct_chg` | `decimal(8,4)` | | 涨跌幅 |
| `turnover_rate` | `decimal(8,4)` | | 换手率 |
| `lhb_net_buy_score` | `decimal(8,4)` | | 龙虎榜净买入打分 |
| `margin_buy_score` | `decimal(8,4)` | | 融资买入打分 |
| `north_funds_chg` | `decimal(20,4)` | | 北向资金变动 (万元) |
| `board_height` | `int` | | 连板高度 |
| `yjyg_magnitude` | `decimal(10,4)` | | 业绩预告量级 |
| `anomaly_type` | `varchar(50)` | | 异动类型 (如“爆量突破”) |

---

### 2.6 估值与宏观表 (`fupan_market_macro`)
| 字段名 | 类型 | 备注 |
| :--- | :--- | :--- |
| `trade_date` | `date` | `PRI` |
| `pe_pctile_10y` | `decimal(6,4)` | 全 A 10年 PE 分位 |
| `erp_wind_a` | `decimal(8,4)` | 风险溢价 (ERP) |
| `hstech_pct` | `decimal(8,4)` | 恒生科技涨幅 |
| `usdcny_diff` | `decimal(10,4)` | 汇率价差 |
| `cn_us_10y_spread` | `decimal(10,4)` | 中美利差 |
| `monitor_health_score` | `decimal(6,2)` | 系统综合健康分 |

---

### 2.7 复盘综述表 (`fupan_summary`)
| 字段名 | 类型 | 备注 |
| :--- | :--- | :--- |
| `trade_date` | `date` | `PRI` |
| `market_summary_text` | `text` | 综述文案 |
| `hot_themes` | `json` | 今日强势主线 |
| `watchlist_next_day` | `json` | 次日观察标的 |

---

## 3. SQL 实施脚本 (已严格校对)

```sql
-- 1. 纵表: 市场指数
CREATE TABLE IF NOT EXISTS `fupan_market_index` (
    `trade_date` DATE NOT NULL,
    `ts_code` VARCHAR(20) NOT NULL,
    `index_name` VARCHAR(50),
    `close` DECIMAL(16,4),
    `pct_chg` DECIMAL(8,4),
    `amount` DECIMAL(20,4),
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`trade_date`, `ts_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. 宽表: 流动性
CREATE TABLE IF NOT EXISTS `fupan_market_liquidity` (
    `trade_date` DATE NOT NULL,
    `turnover_total` DECIMAL(20,4),
    `turnover_ma5` DECIMAL(20,4),
    `turnover_ma20` DECIMAL(20,4),
    `turnover_pct_vs_ma20` DECIMAL(8,4),
    `turnover_pctile_1y` DECIMAL(6,4),
    `turnover_rate_avg` DECIMAL(8,4),
    `volume_ratio_avg` DECIMAL(8,4),
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. 宽表: 市场情绪
CREATE TABLE IF NOT EXISTS `fupan_market_sentiment` (
    `trade_date` DATE NOT NULL,
    `up_count` INT,
    `down_count` INT,
    `flat_count` INT,
    `up_down_ratio` DECIMAL(8,4),
    `limit_up_count` INT,
    `limit_down_count` INT,
    `st_limit_up_count` INT,
    `st_limit_down_count` INT,
    `broken_board_count` INT,
    `broken_board_rate` DECIMAL(6,4),
    `high_60d_count` INT,
    `low_60d_count` INT,
    `yesterday_zt_avg_return` DECIMAL(8,4),
    `max_board_height` INT,
    `market_regime` VARCHAR(20),
    `board_ladder` JSON,
    `pct_chg_distribution` JSON,
    `profit_effect_score` DECIMAL(6,2),
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. 纵表: 行业指标
CREATE TABLE IF NOT EXISTS `fupan_sector_indicators` (
    `trade_date` DATE NOT NULL,
    `ts_code` VARCHAR(20) NOT NULL,
    `name` VARCHAR(50),
    `close` DECIMAL(16,4),
    `pct_chg` DECIMAL(8,4),
    `amount` DECIMAL(20,4),
    `amount_pct` DECIMAL(6,4),
    `up_count` INT,
    `down_count` INT,
    `top_stock_code` VARCHAR(20),
    `top_stock_name` VARCHAR(50),
    `pe_pctile_10y` DECIMAL(6,4),
    `momentum_score` DECIMAL(8,4),
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`trade_date`, `ts_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. 纵表: 个股指标
CREATE TABLE IF NOT EXISTS `fupan_stock_indicators` (
    `trade_date` DATE NOT NULL,
    `ts_code` VARCHAR(20) NOT NULL,
    `name` VARCHAR(50),
    `close` DECIMAL(16,4),
    `pct_chg` DECIMAL(8,4),
    `turnover_rate` DECIMAL(8,4),
    `lhb_net_buy_score` DECIMAL(8,4),
    `margin_buy_score` DECIMAL(8,4),
    `north_funds_chg` DECIMAL(20,4),
    `board_height` INT,
    `yjyg_magnitude` DECIMAL(10,4),
    `anomaly_type` VARCHAR(50),
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`trade_date`, `ts_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. 宽表: 估值宏观
CREATE TABLE IF NOT EXISTS `fupan_market_macro` (
    `trade_date` DATE NOT NULL,
    `pe_pctile_10y` DECIMAL(6,4),
    `erp_wind_a` DECIMAL(8,4),
    `hstech_pct` DECIMAL(8,4),
    `usdcny_diff` DECIMAL(10,4),
    `cn_us_10y_spread` DECIMAL(10,4),
    `monitor_health_score` DECIMAL(6,2),
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. 宽表: 复盘汇总
CREATE TABLE IF NOT EXISTS `fupan_summary` (
    `trade_date` DATE NOT NULL,
    `market_summary_text` TEXT,
    `hot_themes` JSON,
    `watchlist_next_day` JSON,
    `strategy_focus` TEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```
