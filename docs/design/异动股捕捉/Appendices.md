## 附录

### 附录 A · 标签字典完整列表 (部分摘录)

v1.1 包含约 80 个标签,核心分类如下:

| 类别 | 核心标签示例 | 说明 |
|---|---|---|
| **价格行为** | `zt`, `dt`, `first_board`, `breakout_60d` | 基础行情状态 |
| **资金流向** | `main_inflow_strong`, `lhb_inst_buy`, `capital_rank_jump` | 核心资金面异动 |
| **板块地位** | `sector_leader`, `mainline_resonance` | 个股与板块的联动 |
| **形态特征** | `pre_zt_consolidation`, `zt_one_word`, `breakout_box_60d` | 技术形态识别 |
| **异常状态** | `st`, `new_stock`, `micro_cap` | 用于排除或特殊标注 |
| **外部共振** | `sox_up_overnight`, `us_tech_strong` | 跨市场印证信号 |

> **注**: 完整 80 条 INSERT 语句见 `scripts/anomaly/init_tag_dict.sql` (待生成)。

---

### 附录 B · 预设 Profile 配置

系统预设 5 套筛选模板,满足不同研究场景:

1.  **profile_default (新手默认)**: 标准过滤,排除 ST/次新/极低成交。
2.  **profile_short_term (短线接力派)**: 侧重连板梯队、板块龙头及高共振信号。
3.  **profile_value_observer (中线机构派)**: 侧重机构席位买入、业绩超预期及年线突破。
4.  **profile_sector_research (板块研究派)**: 强力加权板块共振标签,忽略孤立异动。
5.  **profile_research_mode (全量研究模式)**: 不进行任何过滤,展示全量三池数据。

---

### 附录 C · 信号生命周期 (阶段 2 预留)

**本期仅建表 (`log_signal_lifecycle`),不实现自动填充逻辑。**

#### 设计意图
不仅记录"今天触发了什么",更要追踪"3 日前、5 日前触发的信号现在的演化状态"(如:持续走强、转弱中断、趋势反转)。这是构建长期认知训练系统的核心数据基础。

```sql
CREATE TABLE `log_signal_lifecycle` (
  `id`               BIGINT UNSIGNED  AUTO_INCREMENT PRIMARY KEY,
  `original_id`      BIGINT UNSIGNED  NOT NULL COMMENT '关联统一信号表 id',
  `tracked_date`     DATE             NOT NULL,
  `state`            VARCHAR(20)      NOT NULL COMMENT 'active/continuing/reversed/failed',
  `delta_metrics`    JSON             COMMENT '相对触发日的变化指标'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```
