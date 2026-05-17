# E14-S2 Phase 1: 数据库迁移与大模型客户端基建 (物理设计书)

本阶段聚焦于物理 DDL 落地、依赖引入，以及高稳定、防超支的统一异步 `LLMClient` 基建开发，并**全面升级补充自研 JSON 状态机流水（`meta_pipeline_run`）的写入审计**。

## 1. 数据库升级设计 (DDL 审计)
我们保证在 MySQL 5.7 实例上运行，完美符合 `AGENTS.md` 命名规范。

### 1.1 待扩展表 (ods_policy_info)
在原有表上增加 `policy_type` 与 `analysis_status` 控制字段，确保可异步追踪：
```sql
ALTER TABLE ods_policy_info 
    ADD COLUMN policy_type VARCHAR(50) DEFAULT 'other' COMMENT '政策分类，关联 dim_policy_type' AFTER ts_code,
    ADD COLUMN analysis_status VARCHAR(20) DEFAULT 'pending_analysis' COMMENT 'AI分析状态' AFTER content_md5,
    ADD INDEX idx_analysis_status (analysis_status),
    ADD INDEX idx_policy_type (policy_type);
```

### 1.2 新建 AI 明细分析表 (dwd_policy_analysis)
```sql
CREATE TABLE IF NOT EXISTS `dwd_policy_analysis` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `policy_id` INT NOT NULL COMMENT '关联 ods_policy_info.id',
    
    -- AI 成果
    `summary` VARCHAR(1500) NOT NULL COMMENT 'AI 三句话摘要 (JSON数组)',
    `importance_level` TINYINT COMMENT '重要性评级 1-5',
    `importance_reason` VARCHAR(500) COMMENT '评级理由',
    `sectors_positive` MEDIUMTEXT COMMENT '受益板块及标的 (JSON)',
    `sectors_negative` MEDIUMTEXT COMMENT '受损板块 (JSON)',
    
    -- 措辞对比
    `intensity_change` VARCHAR(20) DEFAULT 'N/A' COMMENT '强度变化：增强/持平/减弱/不适用',
    `key_differences` MEDIUMTEXT COMMENT '措辞文字差异详情 (JSON)',
    `implication` VARCHAR(1000) COMMENT '市场隐含影响说明',
    `contrast_baseline_id` INT DEFAULT NULL COMMENT '对比基准政策 id',
    `segment_used` MEDIUMTEXT COMMENT '实际截取用于分析的段落',
    `segment_extracted` TINYINT(1) DEFAULT 1 COMMENT '关键段落是否提取成功',
    `input_truncated` TINYINT(1) DEFAULT 0 COMMENT '输入是否被物理截断',
    
    -- MLOps 追踪
    `prompt_name` VARCHAR(50) NOT NULL COMMENT 'Prompt 分类',
    `prompt_version` VARCHAR(10) NOT NULL COMMENT 'Prompt 版本',
    `model_name` VARCHAR(50) NOT NULL COMMENT '使用的物理模型名',
    `thinking_enabled` TINYINT(1) DEFAULT 0 COMMENT '是否启用 thinking',
    `reasoning_effort` VARCHAR(10) DEFAULT NULL COMMENT '思考档位 low/medium/high',
    
    -- Token 消耗与计费 (6位小数)
    `input_cache_hit_tokens` INT DEFAULT 0 COMMENT '缓存命中输入 token',
    `input_cache_miss_tokens` INT DEFAULT 0 COMMENT '缓存未命中输入 token',
    `output_tokens` INT DEFAULT 0 COMMENT '输出 token',
    `reasoning_tokens` INT DEFAULT 0 COMMENT '深度思考 token',
    `cost_cny` DECIMAL(10,6) DEFAULT 0.000000 COMMENT '单次调用实际成本 (CNY)',
    
    -- 调试
    `raw_response` MEDIUMTEXT COMMENT 'LLM 原始返回 (异常排查)',
    `reasoning_content` MEDIUMTEXT COMMENT '思考链中间输出',
    `analysis_duration_ms` INT DEFAULT 0 COMMENT '调用耗时 (ms)',
    
    -- 状态与重试
    `analysis_status` VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '处理状态',
    `error_message` VARCHAR(500) DEFAULT NULL COMMENT '错误报错描述',
    `retry_count` TINYINT DEFAULT 0 COMMENT '重试次数',
    
    -- DDL 三件套
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `is_deleted` TINYINT(1) DEFAULT 0,
    
    UNIQUE KEY `uk_policy_prompt` (`policy_id`, `prompt_name`, `prompt_version`),
    KEY `idx_intensity_change` (`intensity_change`),
    KEY `idx_importance_level` (`importance_level`),
    KEY `idx_analysis_status` (`analysis_status`),
    KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='政策 AI 分析明细';
```

### 1.3 新建日成本审计表 (meta_llm_daily_cost)
```sql
CREATE TABLE IF NOT EXISTS `meta_llm_daily_cost` (
    `cost_date` DATE PRIMARY KEY,
    `total_cost_cny` DECIMAL(10,4) DEFAULT 0.0000,
    `total_calls` INT DEFAULT 0,
    `total_input_tokens` BIGINT DEFAULT 0,
    `total_output_tokens` BIGINT DEFAULT 0,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='LLM 日累计成本审计表';
```

### 1.4 新建申万板块映射表与规则表 (dwd_policy_sector_impact, dim_policy_keyword_sector)
```sql
CREATE TABLE IF NOT EXISTS `dwd_policy_sector_impact` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `policy_id` INT NOT NULL,
    `analysis_id` INT NOT NULL COMMENT '关联 dwd_policy_analysis.id',
    `sector_code_sw` VARCHAR(20) NOT NULL COMMENT '申万二级代码',
    `sector_name` VARCHAR(50) COMMENT '行业名称',
    `impact_direction` VARCHAR(10) NOT NULL COMMENT 'positive/negative/neutral',
    `impact_strength` TINYINT DEFAULT 3 COMMENT '影响强度 1-5',
    `representative_stocks` VARCHAR(500) COMMENT '代表性标的列表 (逗号分割)',
    `mapping_source` VARCHAR(20) DEFAULT 'merged' COMMENT 'llm/rule/merged',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `is_deleted` TINYINT(1) DEFAULT 0,
    KEY `idx_policy_id` (`policy_id`),
    KEY `idx_sector` (`sector_code_sw`, `impact_direction`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='政策申万板块影响明细';

CREATE TABLE IF NOT EXISTS `dim_policy_keyword_sector` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `keyword` VARCHAR(50) NOT NULL COMMENT '政策行业关键词',
    `sector_code_sw` VARCHAR(20) NOT NULL COMMENT '申万二级代码',
    `sector_name` VARCHAR(50) COMMENT '申万板块名称',
    `representative_stocks` VARCHAR(255) COMMENT '默认映射股票列表 (逗号分隔)',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `is_deleted` TINYINT(1) DEFAULT 0,
    UNIQUE KEY `uk_keyword_sector` (`keyword`, `sector_code_sw`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='政策板块关键词规则配置表';
```

---

## 2. 统一异步 LLMClient 接口设计
在 `shared/utils/llm_client.py` 中实现：

```python
class LLMClient:
    def __init__(self):
        # 必须从环境变量安全加载，杜绝硬编码
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        self.daily_cost_limit = float(os.getenv("LLM_DAILY_COST_LIMIT_CNY", 5.0))

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        mode: Literal["flash", "pro", "pro-thinking"] = "flash",
        reasoning_effort: Optional[str] = None
    ) -> dict:
        ...
```

---

## 3. 自研 JSON 状态流水（`meta_pipeline_run`）接口升级

目前存量的 `StockDAO.log_pipeline_run` 缺乏对 `output_summary JSON` 字段的写入支持。我们将在 `scf-collector/shared/db/dao.py` 中重构扩展此接口：

```python
    @staticmethod
    async def log_pipeline_run_v2(
        run_id: str,
        pipeline_id: str,
        biz_date: str,
        status: str,
        error_message: Optional[str] = None,
        output_summary: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        [E14-S2-P1-T4] 升级版任务流水审计接口，完整支持 JSON 格式的状态机输出落地
        """
        sql = """
        INSERT INTO meta_pipeline_run (
            run_id, pipeline_id, biz_date, status, error_message, output_summary, started_at, finished_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        ) ON DUPLICATE KEY UPDATE 
            status = VALUES(status), 
            error_message = VALUES(error_message),
            output_summary = VALUES(output_summary),
            finished_at = CURRENT_TIMESTAMP
        """
        summary_str = json.dumps(output_summary) if output_summary else None
        params = (run_id, pipeline_id, biz_date, status, error_message, summary_str)
        return await execute_query(sql, params, is_select=False)
```

---

## 4. 第一阶段验收指标 (AC)
- **AC1.1 (DDL 审计合格)**: SQL 迁移文件在测试环境导入成功，无任何语法冲突。
- **AC1.2 (计费精确)**: LLMClient 返回的数据能精确计算至小数点后 6 位，精度误差 ≤ 0.000001。
- **AC1.3 (JSON 状态流水支持)**: 触发升级后的 `log_pipeline_run_v2`，能正确向 `meta_pipeline_run.output_summary` 中写入标准的 JSON 内容且能使用 `JSON_EXTRACT` 正常检索。
