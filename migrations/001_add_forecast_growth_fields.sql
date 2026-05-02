-- 迁移脚本: 001_add_forecast_growth_fields.sql
-- 目标表: stock_performance_forecast
-- 描述: 增加业绩变动数值字段 growth_min 和 growth_max

ALTER TABLE stock_performance_forecast 
ADD COLUMN growth_min DECIMAL(16,4) DEFAULT NULL AFTER type,
ADD COLUMN growth_max DECIMAL(16,4) DEFAULT NULL AFTER growth_min;

-- 记录迁移历史 (如果表不存在则创建)
CREATE TABLE IF NOT EXISTS migrations_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    migration_name VARCHAR(255) NOT NULL,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_migration (migration_name)
);

INSERT INTO migrations_history (migration_name) VALUES ('001_add_forecast_growth_fields');
