-- [E8-S2-T1] Deprecate fore_adjust_factor and back_adjust_factor
-- Created at: 2026-05-13

ALTER TABLE stock_adjust_factor
    MODIFY COLUMN fore_adjust_factor DECIMAL(20, 6) NULL
        COMMENT '已废弃。前复权因子不可静态存储，请用 adjust_factor / latest_adjust_factor 实时计算',
    MODIFY COLUMN back_adjust_factor DECIMAL(20, 6) NULL
        COMMENT '累积后复权因子，与 adjust_factor 同值，保留用于 legacy 兼容';
