import asyncio
import aiomysql
import os

SQL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS `dim_style_factor` (
      `factor_code`     VARCHAR(30)   NOT NULL                COMMENT '因子代码, 如 large_vs_small',
      `factor_name`     VARCHAR(50)                           COMMENT '因子中文名, 如 大小盘强弱',
      `long_index`      VARCHAR(20)                           COMMENT '多头指数代码 (对应 index_basic)',
      `long_name`       VARCHAR(50)                           COMMENT '多头指数名称',
      `short_index`     VARCHAR(20)                           COMMENT '空头指数代码 (对应 index_basic)',
      `short_name`      VARCHAR(50)                           COMMENT '空头指数名称',
      `description`     VARCHAR(200)                          COMMENT '因子说明',
      `display_order`   INT           DEFAULT 999             COMMENT '展示顺序',
      `is_active`       TINYINT(1)    DEFAULT 1               COMMENT '是否启用',
      `created_at`      TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
      `updated_at`      TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (`factor_code`),
      KEY `idx_active_order` (`is_active`, `display_order`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
      COMMENT='DIM: 风格因子定义';
    """,
    """
    INSERT IGNORE INTO `dim_style_factor` 
      (factor_code, factor_name, long_index, long_name, short_index, short_name, description, display_order)
    VALUES
      ('large_vs_small',    '大小盘',   '000300.SH',  '沪深300',   '932000.CSI', '中证2000',  '大盘 - 小盘', 1),
      ('value_vs_growth',   '价值成长', '000919.CSI', '300价值',   '000918.CSI', '300成长',   '价值 - 成长', 2),
      ('dividend_vs_micro', '红利微盘', '000922.CSI', '中证红利',   '8841431.WI', '万得微盘股', '红利 - 微盘', 3),
      ('north_vs_south',    '主板创业', '000001.SH',  '上证综指',   '399006.SZ',  '创业板指',   '上证 - 创业', 4);
    """,
    """
    CREATE TABLE IF NOT EXISTS `ods_sw_index_daily` (
      `trade_date`     DATE          NOT NULL,
      `ts_code`        VARCHAR(20)   NOT NULL                COMMENT '行业代码, 如 801010.SI',
      `name`           VARCHAR(50),
      `level`          VARCHAR(10)   NOT NULL                COMMENT 'l1=一级, l2=二级',
      `open`           DECIMAL(16,4),
      `high`           DECIMAL(16,4),
      `low`            DECIMAL(16,4),
      `close`          DECIMAL(16,4),
      `pre_close`      DECIMAL(16,4),
      `pct_chg`        DECIMAL(10,6)                         COMMENT '涨跌幅(小数)',
      `vol`            DECIMAL(20,2)                         COMMENT '成交量(手)',
      `amount`         DECIMAL(20,2)                         COMMENT '成交额(元)',
      `pe_ttm`         DECIMAL(12,4)                         COMMENT '滚动市盈率',
      `pb`             DECIMAL(12,4)                         COMMENT '市净率',
      `dv_ratio`       DECIMAL(10,6)                         COMMENT '股息率(小数)',
      `data_source`    VARCHAR(20)   DEFAULT 'akshare',
      `created_at`     TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (`trade_date`, `ts_code`),
      KEY `idx_level_date` (`level`, `trade_date`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
      COMMENT='ODS: 申万一级/二级行业指数日线';
    """,
    """
    CREATE TABLE IF NOT EXISTS `ods_concept_kline_daily` (
      `trade_date`        DATE          NOT NULL,
      `concept_code`      VARCHAR(30)   NOT NULL                COMMENT '对应 stock_sector_ths.id',
      `concept_name`      VARCHAR(80),
      `open`              DECIMAL(16,4),
      `high`              DECIMAL(16,4),
      `low`               DECIMAL(16,4),
      `close`             DECIMAL(16,4),
      `pct_chg`           DECIMAL(10,6),
      `amount`            DECIMAL(20,2)                         COMMENT '成交额(元)',
      `up_count`          INT                                   COMMENT '上涨家数',
      `down_count`        INT                                   COMMENT '下跌家数',
      `constituent_count` INT                                   COMMENT '成分股总数',
      `data_source`       VARCHAR(20)   DEFAULT 'akshare',
      `created_at`        TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (`trade_date`, `concept_code`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
      COMMENT='ODS: 概念板块日线行情';
    """,
    """
    CREATE TABLE IF NOT EXISTS `ads_l2_industry_daily` (
      `trade_date`             DATE          NOT NULL,
      `industry_code`          VARCHAR(20)   NOT NULL,
      `industry_name`          VARCHAR(50),
      `close`                  DECIMAL(16,4),
      `pct_chg`                DECIMAL(10,6),
      `amount`                 DECIMAL(20,2),
      `internal_breadth`       DECIMAL(10,6)                       COMMENT '内部广度 (up/total)',
      `top_stock_code`         VARCHAR(20)                         COMMENT '领涨股代码',
      `top_stock_name`         VARCHAR(50),
      `top_stock_pct`          DECIMAL(10,6),
      `rank_today`             INT                                 COMMENT '当日涨幅排名',
      `rank_diff_5d`           INT                                 COMMENT '5日排名变化(负数代表走强)',
      `pe_pctile_5y`           DECIMAL(10,6)                       COMMENT 'PE 5年分位',
      `heat_label`             VARCHAR(20)                         COMMENT 'hot/warm/normal/cold',
      `compute_version`        VARCHAR(20)   DEFAULT 'v1',
      `created_at`             TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (`trade_date`, `industry_code`),
      KEY `idx_date_rank` (`trade_date`, `rank_today`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
      COMMENT='ADS: 行业 L2 结构指标';
    """,
    """
    CREATE TABLE IF NOT EXISTS `ads_l2_concept_daily` (
      `trade_date`             DATE          NOT NULL,
      `concept_code`           VARCHAR(30)   NOT NULL,
      `concept_name`           VARCHAR(80),
      `pct_chg`                DECIMAL(10,6),
      `amount`                 DECIMAL(20,2),
      `internal_breadth`       DECIMAL(10,6),
      `limit_up_count`         INT                                 COMMENT '概念内涨停数',
      `persistence_score`      DECIMAL(10,6)                       COMMENT '持续性评分(0-1)',
      `theme_label`            VARCHAR(20)                         COMMENT 'main_theme/one_day/etc',
      `created_at`             TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (`trade_date`, `concept_code`),
      KEY `idx_date_pct` (`trade_date`, `pct_chg`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
      COMMENT='ADS: 概念 L2 结构指标';
    """,
    """
    CREATE TABLE IF NOT EXISTS `ads_l2_style_factor` (
      `trade_date`         DATE          NOT NULL,
      `factor_code`        VARCHAR(30)   NOT NULL,
      `factor_name`        VARCHAR(50),
      `long_pct`           DECIMAL(10,6),
      `short_pct`          DECIMAL(10,6),
      `spread_today`       DECIMAL(10,6)                           COMMENT '多头涨幅 - 空头涨幅',
      `spread_5d`          DECIMAL(10,6)                           COMMENT '5日累计差值',
      `direction`          VARCHAR(20)                             COMMENT 'long_dominant/short_dominant',
      `created_at`         TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (`trade_date`, `factor_code`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
      COMMENT='ADS: 风格 L2 结构指标';
    """
]

async def init_db():
    try:
        conn = await aiomysql.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT")),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            db=os.getenv("DB_NAME"),
            charset=os.getenv("DB_CHARSET", "utf8mb4"),
            autocommit=True
        )
        async with conn.cursor() as cur:
            for sql in SQL_STATEMENTS:
                print(f"Executing: {sql[:100].strip()}...")
                await cur.execute(sql)
        conn.close()
        print("Chapter 2 database initialization completed successfully.")
    except Exception as e:
        print(f"Error during database initialization: {e}")

if __name__ == "__main__":
    asyncio.run(init_db())
