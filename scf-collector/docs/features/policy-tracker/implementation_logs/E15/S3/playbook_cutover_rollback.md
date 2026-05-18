# E15-S3: 零成本规则直切正式切流与一键回退运维指南 (Cutover & Rollback Playbook)

> **版本**: v1.0  
> **分类**: 运维发布方案 / Runbook  
> **状态**: Ready for Staging/Production  
> **生效时间**: 2026-05-18  

---

## 1. 业务切流就绪标准 (Cutover Readiness Standards)

在将规则路径升级为生产正式直切前，必须通过以下硬性门槛：
1. **对照数据充足**: `dwd_policy_analysis_shadow` 影子表和主表比对样本数连续 7 天累计 **≥ 30 组** 对照数据.
2. **审计通过红线**: 运行 `python scf-collector/scripts/audit_policy_rules.py`，输出判定状态为 **`AUDIT STATUS: PASS`**（五维一致率 **≥ 95%**）.
3. **接口兼容通过**: 验证前端小程序与后端 API 对规则直切写入 `dwd_policy_analysis` 中的结构化格式解析正常，无白屏或阻断异常.

---

## 2. 正式切流步骤 (Hot-swap Cutover Steps)

本项目采用**纯环境变量无缝无停机热切流**机制，无需修改代码或重新部署二进制包。

### 步骤 1: 修改环境变量
在腾讯云 Serverless (SCF) 控制台或腾讯云轻量托管的 `.env` 配置文件中，修改以下环境变量：
```ini
# 原灰度影子双写模式
# RULE_BASED_PATH_ENABLED="shadow"

# 切换为生产正式直切模式
RULE_BASED_PATH_ENABLED="production"
```

### 步骤 2: 触发热载入与实例重启
- **Serverless (SCF)**: 直接点击“发布新版本”或更新函数环境变量，SCF 将自动对容器实例进行零停机灰度扩缩，通常在 **3 - 5 秒内** 完成全实例切流.
- **本地/独立容器**: 重启数据同步进程或触发热重载：
  ```bash
  docker-compose restart scf-collector
  ```

### 步骤 3: 生产切流验证 (Verification)
1. **影子表静默**: 确认影子表 `dwd_policy_analysis_shadow` 不再写入新的记录。
2. **主表直切写入**: 查询生产主表 `dwd_policy_analysis`，确认最新的 LPR/OMO 等政策的记录中，**`analysis_path` 字段为 `"rule"`** 且 **`cost_cny` 为 `0.000000`**。
   - 验证 SQL:
     ```sql
     SELECT id, policy_id, analysis_path, summary, cost_cny, created_at 
     FROM dwd_policy_analysis 
     WHERE analysis_path = 'rule' 
     ORDER BY created_at DESC 
     LIMIT 5;
     ```
3. **API 状态核验**: 访问 `/api/v1/health` 及前端政策追踪流，确保页面加载正常，交互无延迟。

---

## 3. 一键紧急回退方案 (1-Second Rollback Playbook)

> [!WARNING]
> **回退触发红线**
> - 生产主表发生规则写入抛错（如字段缺失或 Jaccard 相似度骤降）.
> - 前端小程序在渲染规则输出的 summary 时因中文字符编码或字段名不兼容出现白屏 crash。
> - 央行突发极其复杂的非标结构政策（例如创设新型特种流动性工具），规则提取器未匹配成功导致重要度判定失真。

### 步骤 1: 恢复原大模型路径
在配置中立即将变量改回 `"shadow"`（继续对照）或 `"disabled"`（彻底关闭规则旁路，强制 100% 走 LLM 原始路径）：
```ini
# 立即紧急切回大模型，确保 100% 生产兜底防裸奔
RULE_BASED_PATH_ENABLED="shadow"
```

### 步骤 2: 触发极速载入
更新环境变量并保存，SCF 控制台热加载将在 **1 秒内** 阻断规则路由并强制切回大模型。

### 步骤 3: 验证回退状态
查询物理库确认后续分析的 `analysis_path` 已经平滑恢复为 `"llm"` 或 `"cache"`，且单条分析成本 `cost_cny` 恢复正常数值。
   - 验证 SQL:
     ```sql
     SELECT id, policy_id, analysis_path, cost_cny, created_at 
     FROM dwd_policy_analysis 
     ORDER BY created_at DESC 
     LIMIT 5;
     ```

---
*Created by Devops and Production Security Guard v1.0 - Modular Playbook Standard*
