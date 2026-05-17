-- Migration: V1.7_E14_S2_Sector_Impact
-- Description: Create dwd_policy_sector_impact & dim_policy_keyword_sector & Seed default mappings
-- Created At: 2026-05-17

-- 1. 新建政策板块影响明细扁平表 dwd_policy_sector_impact
CREATE TABLE IF NOT EXISTS `dwd_policy_sector_impact` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `policy_id` INT NOT NULL COMMENT '关联 ods_policy_info.id',
    `analysis_id` INT NOT NULL COMMENT '关联 dwd_policy_analysis.id',
    `sector_code_sw` VARCHAR(20) NOT NULL COMMENT '申万二级代码 (例如 801120 代表半导体)',
    `sector_name` VARCHAR(50) COMMENT '申万板块名称',
    `impact_direction` VARCHAR(10) NOT NULL COMMENT 'positive/negative/neutral',
    `impact_strength` TINYINT DEFAULT 3 COMMENT '影响强度 1-5',
    `representative_stocks` VARCHAR(500) COMMENT '代表性标的列表 (逗号分割，Tushare口径)',
    `mapping_source` VARCHAR(20) DEFAULT 'merged' COMMENT 'llm/rule/merged',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `is_deleted` TINYINT(1) DEFAULT 0,
    KEY `idx_policy_id` (`policy_id`),
    KEY `idx_sector` (`sector_code_sw`, `impact_direction`),
    KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='政策申万板块影响明细';

-- 2. 新建政策板块关键词映射维度规则种子表 dim_policy_keyword_sector
CREATE TABLE IF NOT EXISTS `dim_policy_keyword_sector` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `keyword` VARCHAR(50) NOT NULL COMMENT '政策行业敏感词',
    `sector_code_sw` VARCHAR(20) NOT NULL COMMENT '申万二级代码',
    `sector_name` VARCHAR(50) COMMENT '申万二级名称',
    `representative_stocks` VARCHAR(255) COMMENT '默认映射代表性龙头股票列表 (逗号分隔，Tushare口径)',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `is_deleted` TINYINT(1) DEFAULT 0,
    UNIQUE KEY `uk_keyword_sector` (`keyword`, `sector_code_sw`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='政策板块关键词规则配置表';

-- 3. 预置申万行业核心规则种子数据 (Seed Data)
INSERT INTO `dim_policy_keyword_sector` (`keyword`, `sector_code_sw`, `sector_name`, `representative_stocks`) VALUES
-- 敏感性货政/银行板块
('普惠金融', '801780', '银行', '601398.SH,601288.SH,601939.SH'),
('支农支小', '801780', '银行', '601658.SH,002142.SZ'),
('信贷结构', '801780', '银行', '600036.SH,601169.SH'),
-- 半导体/高科技板块
('集成电路', '801120', '半导体', '688981.SH,603501.SH,002049.SZ'),
('芯片', '801120', '半导体', '688981.SH,603501.SH,688012.SH'),
('半导体', '801120', '半导体', '688046.SH,600584.SH,688981.SH'),
-- 人工智能/数字经济
('人工智能', '801750', '计算机设备', '601360.SH,300059.SZ,300078.SZ'),
('大模型', '801750', '计算机设备', '002230.SZ,300033.SZ'),
('数据要素', '801760', '软件开发', '600718.SH,300229.SZ'),
('数字经济', '801760', '软件开发', '000977.SZ,600845.SH'),
-- 新能源/电网/电力
('光伏', '801730', '光伏设备', '601012.SH,300274.SZ,600438.SH'),
('风电', '801730', '风电设备', '601615.SH,300129.SZ'),
('智能电网', '801730', '电网设备', '600406.SH,600517.SH'),
('新型储能', '801730', '电池', '300750.SZ,002594.SZ'),
-- 环保与双碳
('碳达峰', '801190', '环保', '600323.SH,600008.SH'),
('绿色信贷', '801780', '银行', '601398.SH,600036.SH'),
-- 证券/非银板块 (证监会减持、两融等利好)
('股份减持', '801193', '证券', '600030.SH,600837.SH,000776.SZ'),
('两融', '801193', '证券', '601688.SH,601211.SH'),
('融资融券', '801193', '证券', '600030.SH,601211.SH'),
('红筹企业', '801193', '证券', '600030.SH,601066.SH'),
-- 传统顺周期板块
('房地产', '801180', '房地产开发', '000002.SZ,600048.SH,602018.SH'),
('基建', '801710', '基础建设', '601668.SH,601186.SH'),
('地方债', '801710', '基础建设', '601186.SH,601390.SH')
ON DUPLICATE KEY UPDATE 
    `sector_name` = VALUES(`sector_name`), 
    `representative_stocks` = VALUES(`representative_stocks`);
