-- ==============================================================================
-- Epic E23-S1: 每日格言打卡 · 数据库表结构 DDL (MySQL 5.7)
-- ==============================================================================

-- 1. 格言与金句词库主表
CREATE TABLE IF NOT EXISTS `diary_quote_lib` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '格言唯一主键',
  `owner_user_id` bigint(20) NOT NULL DEFAULT '1' COMMENT '归属用户ID',
  `content` text NOT NULL COMMENT '格言正文',
  `source_author` varchar(64) DEFAULT NULL COMMENT '格言原作者(如巴菲特、芒格等，未知可为空)',
  `source_book` varchar(128) DEFAULT NULL COMMENT '来源书籍、文章或媒体渠道',
  `category` tinyint(4) NOT NULL DEFAULT '1' COMMENT '1=经典名言, 2=大佬语录, 3=历史教训, 4=用户摘录, 5=自己写的金句',
  `base_weight` int(11) NOT NULL DEFAULT '50' COMMENT '用户设定的基础曝光权重(1-100)',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` tinyint(4) NOT NULL DEFAULT '0' COMMENT '逻辑删除标识',
  PRIMARY KEY (`id`),
  KEY `idx_user_category` (`owner_user_id`, `category`),
  KEY `idx_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='格言与金句词库主表';

-- 2. 用户格言行为状态与计数表
CREATE TABLE IF NOT EXISTS `diary_quote_user_state` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id` bigint(20) NOT NULL DEFAULT '1' COMMENT '用户ID',
  `quote_id` bigint(20) NOT NULL COMMENT '关联的格言ID',
  `is_favorited` tinyint(4) NOT NULL DEFAULT '0' COMMENT '是否收藏: 1=已收藏, 0=未收藏',
  `is_disliked` tinyint(4) NOT NULL DEFAULT '0' COMMENT '是否永久屏蔽: 1=已屏蔽, 0=正常',
  `consecutive_skip_count` int(11) NOT NULL DEFAULT '0' COMMENT '连续跳过次数',
  `expose_count` int(11) NOT NULL DEFAULT '0' COMMENT '累计曝光轮询次数',
  `insight_count` int(11) NOT NULL DEFAULT '0' COMMENT '用户累计针对该格言写过的见解数',
  `deep_insight_count` int(11) NOT NULL DEFAULT '0' COMMENT '字数超过50字的深度见解感悟数',
  `last_exposed_at` timestamp NULL DEFAULT NULL COMMENT '最近一次被曝光的时间戳',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_quote` (`user_id`, `quote_id`),
  KEY `idx_user_expose` (`user_id`, `last_exposed_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户格言行为状态与计数表';

-- 3. 每日打卡任务锁定状态表
CREATE TABLE IF NOT EXISTS `diary_checkin_lock` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id` bigint(20) NOT NULL DEFAULT '1' COMMENT '用户ID',
  `business_date` date NOT NULL COMMENT '业务日期(以凌晨4:00作为切分基准)',
  `checkin_type` tinyint(4) NOT NULL DEFAULT '2' COMMENT '打卡类型: 2=格言打卡',
  `locked_target_id` bigint(20) DEFAULT NULL COMMENT '锁定的格言ID(对应diary_quote_lib.id)',
  `status` tinyint(4) NOT NULL DEFAULT '0' COMMENT '打卡状态: 0=待打卡, 1=已完成, 2=已跳过',
  `completed_diary_id` bigint(20) DEFAULT NULL COMMENT '生成的日记ID(打卡成功后回填)',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_date_type` (`user_id`, `business_date`, `checkin_type`),
  KEY `idx_user_status` (`user_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='每日打卡任务锁定状态表';
