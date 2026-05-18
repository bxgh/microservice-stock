# E1-S3 灰度审计与正式切流开发进度跟踪

- [x] `E1-S3-T1` **影子对照表与路由校验**
  - [x] 确认物理数据库中 `dwd_policy_analysis_shadow` 表结构存在且与主表完全一致
  - [x] 验证现有 staged_analyzer 在影子模式下的静默路由行为是否正确
- [x] `E1-S3-T2` **编写比对审计脚本**
  - [x] 编写 `scf-collector/scripts/audit_policy_rules.py` 支持异步加载比对组
  - [x] 实现 5 维一致率比对：重要性星级、政策强度倾向、量纲匹配（LPR/OMO数字误差为0）、SW行业板块交并比（Jaccard）、Simhash 语义相似度
  - [x] 生成 Markdown 比对对账审计报告
- [x] `E1-S3-T3` **比对脚本单元测试**
  - [x] 编写 `scf-collector/tests/test_audit_policy_rules.py`
  - [x] 运行测试验证比对精度，验证脏数据触发 WARNING 状态
- [x] `E1-S3-T4` **编写切流与回退运维指南**
  - [x] 创建 `scf-collector/docs/features/policy-tracker/implementation_logs/E15/S3/playbook_cutover_rollback.md`
- [x] `E1-S3-T5` **文档交付与 Portal 刷新**
  - [x] 全自动编译 markdown 报告为 HTML
  - [x] 运行 `scripts/update_docs_portal.py` 同步到全局 Portal
