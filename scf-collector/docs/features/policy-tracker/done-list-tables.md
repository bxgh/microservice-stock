# 已就绪采集表清单 (Done List Tables)

记录 `scf-collector` 微服务下已实现并稳定运行的数据库采集表与任务状态。

## 1. 采集数据表注册

| 表名 | 业务说明 | 采集数据源 | 采集频率 | 状态 | 关键 AC 达成情况 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ods_policy_info` | 宏观及监管政策信息表 | 中国政府网 (Gov.cn)<br>中国人民银行 (PBC)<br>中国证监会 (CSRC) | 每日/盘后 (17:30) | **已就绪 (Completed)** | 1. 一级 URL 去重已达成<br>2. 二级 MD5 内容去重已达成<br>3. 央行(PBC)高容错动态映射已达成<br>4. 证监会(CSRC) JSON 接口高频同步已达成<br>5. 多通道(微信/邮件)预警分发已达成 |

---

## 2. 字段审计对照矩阵

对于 `ods_policy_info` 表，已实现字段与业务实体对照关系：

| 字段名 | 类型 | 约束 / 索引 | 业务映射说明 |
| :--- | :--- | :--- | :--- |
| `id` | `INT` | `AUTO_INCREMENT PRIMARY KEY` | 自增主键 ID |
| `ts_code` | `VARCHAR(10)` | `INDEX` | 机构编码：`GOV_CN`(政府网), `PBC`(央行), `CSRC`(证监会) |
| `title` | `VARCHAR(255)` | `NOT NULL` | 政策法规/通告标题 |
| `publish_date` | `DATE` | `INDEX` | 发布日期，格式 `YYYY-MM-DD` |
| `source_url` | `VARCHAR(512)` | `UNIQUE KEY` | 源网页 URL (一级唯一索引去重) |
| `content_text` | `TEXT` | `NOT NULL` | 提取剥离的政策干净文本正文 |
| `content_md5` | `VARCHAR(32)` | `INDEX` | 正文 MD5 指纹 (二级特征去重) |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | 采集时间 (审计字段) |
| `updated_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP ON UPDATE` | 更新时间 (审计字段) |
| `is_deleted` | `TINYINT(1)` | `DEFAULT 0` | 软删除标志，默认 0 (审计字段) |

---

## 3. 双源数据量现状统计

* **全量历史回填 (Gov.cn)**: `1,046` 条。
* **增量高频采集 (CSRC)**: `15` 条 (首批次高频同步)。
* **数据总计**: `1,061` 条。
