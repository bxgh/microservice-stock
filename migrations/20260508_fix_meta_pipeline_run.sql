-- 修复 meta_pipeline_run 表结构，对齐 AGENTS.md v0.8 规范
DROP TABLE IF EXISTS meta_pipeline_run;
CREATE TABLE meta_pipeline_run (
    run_id VARCHAR(64) PRIMARY KEY,
    pipeline_id VARCHAR(128),
    biz_date DATE,
    task_id VARCHAR(128),
    status VARCHAR(16),
    started_at DATETIME,
    finished_at DATETIME,
    duration_sec INT,
    error_message TEXT,
    output_summary JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) DEFAULT 0,
    KEY idx_mpr_updated_at (updated_at),
    KEY idx_mpr_is_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC;
