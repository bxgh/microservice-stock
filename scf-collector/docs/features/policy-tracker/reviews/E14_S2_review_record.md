# Epic E14-S2 宏观政策 AI 智能分析系统技术评审记录

> [!NOTE]
> 本文件为 `scf-collector` 微服务 `policy-tracker` 特征域下 Epic E14-S2 的技术评审归口存证。

---

## 1. 评审基本信息

- **项目/特征域**: `scf-collector` / `policy-tracker` (A 股宏观政策智能追踪系统)
- **评审主题**: 定时解耦微服务重构、AI 分析主逻辑与云端 Serverless 只读容器依赖部署
- **评审日期**: 2026-05-17
- **评审状态**: **🟢 APPROVED (通过并准入生产)**
- **Story 列表状态**:
  - `E14-S2-P1` (大模型计费审计基建): **ok**
  - `E14-S2-P2` (AI 措辞分析与申万融合): **ok**
  - `E14-S2-P3` (定时云函数物理解耦与 HTML side-by-side 对比发送): **ok**
  - `E14-S2-P4` (历史回填、CLS 可观测性与 Version 13 补丁依赖层部署): **ok**

---

## 2. 关键设计审查点与结论

### 2.1 计费防爆与安全限额设计
- **审查点**：如何防止大模型（OpenAI/DeepSeek）在高频采集或历史回填时由于并发过多而造成超额扣费？
- **设计结论**：
  - 在 `llm_client.py` 底层集成 `meta_llm_daily_cost` 计费日志写入，每日调用前计算天级总开销。
  - 在增量历史回填中灌入前置 **`1.0 CNY`** 硬限额防火墙。一旦当天累计费用超限，立即主动挂起。
  - 评审结果：**通过**，安全措施极度到位。

### 2.2 Serverless 乐观防碰撞锁设计
- **审查点**：多定时触发器（如每 5 分钟）是否会导致多个 analyzer 云函数同时并发运行，从而竞争同一批政策导致 LLM 重复扣费？
- **设计结论**：
  - 基于 MySQL `meta_pipeline_run` 实现了**分布式乐观排碰撞锁**。
  - 启动前查询 10 分钟内是否有 `RUNNING` 实例，若存在则跳过本次执行；正常抢占锁后标记为 `RUNNING`，完工后 `ON DUPLICATE KEY UPDATE` 更新为 `SUCCESS` 并释放锁。
  - 评审结果：**通过**，确保了在高度并发和重叠加载下的数据一致性与计费安全性。

### 2.3 只读云环境 Python 依赖补丁包设计
- **审查点**：腾讯云只读运行容器无法热装包，`openai` / `httpx` 在 Python 3.10 下因缺少异步底层依赖崩溃如何解决？
- **设计结论**：
  - 本地启动 Docker 编译环境（或强制指定 Linux x86_64 二进制 wheel 平台审计）排除 Windows 二进制 `.pyd` 文件混入。
  - 针对 Python 3.10 只读 Serverless 容器，我们在 **`stock-patch-layer` Version 13** 依赖层中物理打包进 `exceptiongroup`。
  - 这彻底根治了 `anyio` 异步引擎的导入报错，进而完美自愈了 `httpcore[asyncio]`、`openai` 及 `aiosmtplib` 库的多米诺骨牌级崩溃红线。
  - 评审结果：**通过**，完美攻克了云端联调最大的物理阻碍。

---

## 3. 反馈闭环与修改追踪

| 序号 | 评审反馈意见 | 状态 | 落地位置与修改摘要 |
|---|---|---|---|
| 1 | 板块影响方向 `impact_direction` 超长引发落库崩溃 | **已修复** | 物理执行 SQL 扩容 `dwd_policy_sector_impact.impact_direction` 为 `VARCHAR(50)`，并在 `policy_analyzer.py` 中对大模型输出进行归一化清洗拦截。 |
| 2 | Windows CMD 控制台打印大写 `¥` 符号报错 | **已修复** | 将所有本地控制台与对账日志中的大写 `¥` 符号重构为 `CNY` 字符表示，完全规避了 Windows Console 的 GBK 局限。 |
| 3 | 三函数解耦后云端绑定 Version 12 不兼容 | **已修复** | 升级并重新发布补丁 Layer **Version 13**，将三个云函数的部署脚本统一刷新绑定为最新 v13 版本，已在云端级联测试成功。 |

---
*本记录由 AI Agent Antigravity 整理自动建档，已向全局导航门户同步。*
