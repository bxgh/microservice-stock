-- 002_add_forecast_growth_fields.sql
-- 为业绩预告表增加高精度数值字段

ALTER TABLE stock_performance_forecast 
ADD COLUMN growth_min DECIMAL(16,4) DEFAULT NULL AFTER type,
ADD COLUMN growth_max DECIMAL(16,4) DEFAULT NULL AFTER growth_min;
