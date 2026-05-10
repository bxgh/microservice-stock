# 数据采集与接入 QC 检查清单 (QC Checklist)

本指南旨在规范所有 `ods_` 层数据的接入流程，确保数据从 API 到数据库的完整性与准确性。

## 1. 开发期：映射矩阵验证 (Mapping Matrix)

在编写 `FinancialDataService` 或类似同步服务时，必须执行以下步骤：

- [ ] **API 结构普查**: 使用 `scratch/check_api_cols.py` 输出原始 API 返回的所有 Key。
- [ ] **字段对齐**: 将 API Key 与数据库 Schema 列名进行一一映射，记录在 `implementation_plan.md` 中。
- [ ] **首条记录验证**:
    - 选取 1 条典型记录。
    - 打印其 API 返回的 JSON。
    - 打印其入库后的 SQL Row。
    - 验证关键数值（如金额、单价、每股收益）是否一致。

## 2. 部署前：灰度同步验证 (Grey-scale Sync)

严禁直接启动针对数千只股票的全量回填。

- [ ] **样本同步**: 选取 10-50 只具有代表性的股票（包含主板、科创板、ST 股等）。
- [ ] **空值审计**: 运行 SQL 检查该样本集中的核心字段是否有 NULL。
    ```sql
    SELECT COUNT(*) FROM table WHERE core_field IS NULL;
    ```
- [ ] **业务逻辑审计**:
    - 检查日期格式（YYYY-MM-DD）。
    - 检查单位（元 vs 万元）。
    - 检查小数精度。

## 3. 运行期：全量回填 QC (Post-Backfill Audit)

全量回填完成后，必须产出 QC 报告并嵌入 `walkthrough.md`。

- [ ] **总量统计**: 对比 API 预期总数与 DB 实际总数。
- [ ] **覆盖度检查**: 检查是否覆盖了预期的年份区间（如 2010-2026）。
- [ ] **异常分布检查**:
    - 检查 0 值比例。
    - 检查 NULL 值比例。
    - 检查重复项 (`ts_code`, `end_date` / `trade_date`)。

## 4. 故障复盘与闭环 (Feedback Loop)

- [ ] 若发现映射错误，必须更新 `FinancialDataService` 并编写 `repair_*.py` 脚本进行增量修复，严禁在未修复代码的情况下手动修改数据库。
