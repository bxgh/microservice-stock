ALTER TABLE meta_pipeline_run 
ADD COLUMN retry_count INT DEFAULT 0 AFTER duration_sec,
ADD COLUMN max_retry INT DEFAULT 3 AFTER retry_count,
ADD COLUMN error_stack TEXT AFTER error_message,
ADD COLUMN output_summary JSON AFTER error_stack;
