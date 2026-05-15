---
name: parse-epic-story
description: 当按 Epic → Story → Task → AC(Given-When-Then)结构的设计文档实施代码时使用。设计文档由 `epic-story-doc` skill 生成，位于 docs/ 目录，文件名格式为 `draft_{EpicId}.md`，以「## E<N>」「### E<N>-S<M>」「#### 任务」「#### 验收标准(AC)」为标题模式。本 skill 把 AC 转成可执行测试用例,把 Task 转成 commit 粒度的 todo,严格遵守编号(E1-S1-T1)以便回链设计文档。在用户说「实施 E1-S1」「按这份设计实现」「跑一下这个 Story」「写这个 Epic 的代码」时主动使用。即使用户没明确说「按 Epic-Story 实施」,但读取的文档里出现 `E\d+-S\d+` / `Given-When-Then` / `验收标准(AC)` 等模式,也应主动套用本 skill 的规则。本 skill 不适用于:产出 Epic-Story 结构的设计文档(那是 `epic-story-doc` skill 的职责)、不带 Epic-Story 结构的普通需求、文档没有 AC 的探索性任务。
---

# 按 Epic-Story-Task-AC 结构产出实施代码

本 skill 是 `epic-story-doc`(设计侧产出文档)的镜像。设计侧 Claude 写文档,实施侧按文档写代码。本文件规定实施侧的「读文档 → 写代码 → 验收 → 持久化记录」纪律。

---

## 0. 实施记录本地保存 (强制)

所有实施过程产生的 Artifacts 必须保存到本地文件系统中,以便复审与归档:

- **存放路径**: `<设计文档所在目录>/implementation_logs/E<N>/S<M>/`
- **必须包含的文件**:
    - `implementation_plan.md`: 实施前设计的技术方案
    - `task.md`: 任务分解与实时进度
    - `walkthrough.md`: 实施后的功能演示与测试结果（含截图/视频链接）
- **同步时机**: 每一个 Story 开始前创建目录,结束后确保文件已全部保存。
- **索引更新**: 每一个 Story 完成后,必须在 `docs/IMPLEMENTATION_FEEDBACK.md` 中将状态更新为 `DONE`。
- **设计文档回填**: 每一个 Task 完成后,必须在原始设计文档中将对应的任务勾选（`- [ ]` → `- [x]`）。

---

## 触发后的核心心法

1. **AC 是契约,不是建议** —— 每条 Given-When-Then 都必须有对应的可执行测试
2. **Task ID 是回链锚点** —— 每个 commit 都能回到设计文档的某个 Task
3. **TBD 是停止信号,不是默认值** —— 看到 TBD 不允许编造,必须 surface
4. **Story 之间不能跳** —— 当前 Story 的所有 AC 通过前,不进入下一个 Story

---

## 1. 文档结构识别

`epic-story-doc` skill 产出两份文件，实施侧读 **MD 文件**（`draft_{EpicId}.md`）：

```
# [Epic E<N>] <Epic 标题>

## <章节名>（sections 中的非 Story 章节，如「背景」「核心算法约定」）

内容可包含：
- 普通文本
- 公式（$行内公式$ 或 $$块级公式$$）
- Mermaid 图表（```mermaid ... ```）
- 表格
- 代码块

> **评审批注**: ...（评审后重生成时可能附带，仅供阅读，不影响实施）

## E<N> <Epic 标题>

### E<N>-S<M> <Story 标题>

**作为** <角色>，**我希望** <功能>，**以便** <价值>。

> **评审备注**: ...（评审后重生成时可能附带，仅供阅读）

#### 任务清单

- [ ] **E<N>-S<M>-T1** <Task 描述>
- [ ] **E<N>-S<M>-T2** <Task 描述>

#### 验收标准

##### AC1 <AC 名称> [✓|✕ 需修改|⚠ 有疑问]

- **Given** <前提条件>
- **When** <触发动作>
- **Then** <预期结果>

> **评审意见**: ...（若有，需在实施中体现）
```

**读文档注意事项**：

- **sections 章节**（背景、目标、核心算法约定等）：仅作为上下文阅读，不产生 Task，不写代码。其中的公式和架构图是实施的重要约束，必须完整理解后再开始 Story。
- **评审批注 / 评审备注**：设计侧评审意见，若 AC 标记为 `✕ 需修改` 或 `⚠ 有疑问`，该 AC 的 Then 可能已更新，必须以最新文档为准。
- **Story 之间的 `---` 分隔线**：视觉分隔，不影响结构解析。

---

## 2. AC → 测试用例（强制映射）

每条 AC 必须转成对应测试函数,**不允许漏写**:

| AC 部分 | 测试代码部分 |
|---|---|
| `Given <前提>` | fixture / setup / mock 数据准备 |
| `When <动作>` | 被测函数 / 接口的实际调用 |
| `Then <结果>` | assert 语句 |

测试函数命名规则：`test_e<N>_s<M>_<语义描述>`，例如 AC「计算 5 日排名时如果 trade_date 缺失则跳过」对应 `test_e2_s1_skip_when_trade_date_missing`。

测试文件位置：跟被测代码同包，`tests/` 子目录，文件名 `test_<被测模块>.py`。每个 Story 至少有一个测试文件覆盖。

**反模式**：
- ❌ 多条 AC 合并写在一个测试函数里（每条 AC 独立 assert，失败信号才精确）
- ❌ 用 `# AC1: ...` 注释代替结构化测试
- ❌ 测试只 setup 不 assert（空跑测试，等于没测）

---

## 3. Task → Commit（粒度对齐）

每个 Task 对应一个 commit,**不要把多个 Task 塞进同一个 commit**。

commit message 格式（遵循 Conventional Commits）：

```
<type>(<scope>): [E<N>-S<M>-T<K>] <中文 summary>

<可选 body，描述做了什么、为什么、影响范围>
```

例：
```
feat(collector): [E8-S1-T2] 实现仅在因子变动时执行 INSERT 的判断逻辑

比对最新库存值与采集值，差值绝对值 < 1e-8 时跳过写入，返回 False。
影响 save_adj_factor 方法，幂等性由 AC1 测试覆盖。
```

`type` 取值：`feat` / `fix` / `chore` / `docs` / `test` / `refactor` / `perf`。

**反模式**：
- ❌ commit message 里没有 Task ID（无法回链设计）
- ❌ 一个 commit 包含 T1 + T2 + T3（粒度太大，review 困难）
- ❌ commit summary 用英文（本项目约定中文）
- ❌ 同一个 Task 拆 5 个 commit（粒度太碎，体现不出「任务完成」语义）

---

## 4. Story 内的执行顺序

一个 Story 包含多个 Task 时,**按文档列出的顺序执行**,不要重排。

执行流程：

```
进入 Story → 阅读所有 sections 上下文（含公式/架构图）→
在设计文档同级创建 implementation_logs/Ex/Sx/ 目录 →
初始化 Plan & Task → 按 Task 顺序写代码 → 每个 Task 完成后回填设计文档 →
全部 Task 完成 → 跑该 Story 的全部 AC 测试 → 全部通过 → 产出 Walkthrough →
更新 IMPLEMENTATION_FEEDBACK.md 状态为 DONE → 保存所有记录到本地目录
                                  ↓ 任何一条失败
                                  回到对应 Task 修复 → 重跑
```

**任何一条 AC 不通过，本 Story 不算完成**，不能进入下一 Story。

---

## 5. TBD 处理（强制流程）

文档里出现 TBD 标记的字段 / 接口名 / 默认值 / 实现细节，**绝对不允许编造**。

| TBD 类型 | 处理方式 |
|---|---|
| 字段名 / 表名 TBD | 停止该 Task，在 `task.md` 标注卡点，并在 `IMPLEMENTATION_FEEDBACK.md` 标记「暂停」 |
| 默认值 / 阈值 TBD | 同上，**不能拍脑袋选一个值**继续 |
| 接口名 TBD | 同上，**不能用 Tushare 文档搜到的相似接口名替代** |
| 实现细节 TBD（算法 / 公式） | 同上，**不能用通用做法替代** |

**唯一例外**：用户在当前对话里明确指示「按 X 假设实施，后面再改」，可以继续但 commit 必须包含：

```
chore(<scope>): [E<N>-S<M>-T<K>] 按假设 <X> 实施，待设计侧确认

TBD 标记：<原文档中的 TBD 描述>
当前假设：<你做的假设>
影响范围：<如果假设错了，需要回改哪些代码>
```

并同步在 `docs/IMPLEMENTATION_FEEDBACK.md` 追加一条「假设记录」。

---

## 6. 跨章节 / 跨表字段引用

设计文档经常引用其他章节的字段，引用前**必须先查 `docs/TABLES_INDEX.md`** 确认：

1. **字段是否存在** —— 不在索引里就停下来问设计侧
2. **单位是否一致** —— 跨表 JOIN 时单位陷阱（参考 `TABLES_INDEX.md` 第 9 节）
3. **是否软删除过滤一致** —— 引用方和被引用方都要过滤 `is_deleted = 0`
4. **数据频率是否匹配** —— T+0 表 JOIN T+1 表会有数据缺失

发现不一致 → 不要硬写代码绕过，先 surface 给设计侧。

---

## 7. 文档没有 AC 时的处理

偶尔会遇到 Story 写了 Task 但没写 AC（早期文档或紧急任务）。**不要直接开写**，以下三选一：

| 选项 | 何时用 |
|---|---|
| 主动补全 AC，提交给设计侧 review | 你能从 Task 描述推出明确的 Given-When-Then |
| 标注「无 AC」实施，在 commit 里写明并补一份「事后 AC」 | 紧急任务，设计侧已批准 |
| 拒绝实施，要求设计侧补 AC | Task 描述模糊到无法推 AC |

**默认选第三个**。AC 缺失通常意味着设计本身没想清楚，实施进去只会把锅背在自己头上。

---

## 8. 输出实施代码前的自检清单

**每开始一个 Story 前**：

- [ ] 读完了所有 sections 上下文（背景、算法约定、架构图），不是只看 Story 标题就开干？
- [ ] sections 中的公式和 Mermaid 图是否理解？实施逻辑是否与之一致？
- [ ] 全部 AC 都列出来了，准备一一对应测试？
- [ ] AC 中是否有评审意见（`> **评审意见**`）需要在实施中体现？
- [ ] Task 顺序按文档来，没有自作主张重排？
- [ ] 文档里的 TBD 已识别，有处理方案（暂停 / 假设 + 记录 / 其他）？
- [ ] 引用的跨章节字段都在 `TABLES_INDEX.md` 查过？
- [ ] 测试环境（Docker / 测试库）就绪，跑得起来？

**每完成一个 Task**：

- [ ] commit message 有 Task ID？
- [ ] commit message 是中文 summary？
- [ ] 已经在设计文档中将该 Task 标记为 `- [x]`？
- [ ] 这次改动只做了这一个 Task 的事，没顺手改无关代码？

**每完成一个 Story**：

- [ ] 全部 AC 测试都跑过，全部通过？
- [ ] 产出了完整的 Walkthrough 并保存到 `implementation_logs/Ex/Sx/`？
- [ ] 跨表字段引用没引入新问题（单位、软删除、is_deleted）？
- [ ] 在 `docs/IMPLEMENTATION_FEEDBACK.md` 更新了全局索引？

---

## 9. 不做的事

- ❌ 不在读完 sections 上下文前开始写 Story 代码（公式和架构图是约束，不是装饰）
- ❌ 不重排 Task 顺序（设计侧已经排过依赖，改顺序可能破坏前置条件）
- ❌ 不合并 AC（每条 AC 是独立验证点，合并会丢失失败信号）
- ❌ 不跳过 AC 验证直接进下一 Story
- ❌ 不在 commit message 里省略 Task ID
- ❌ 不在文档 TBD 没销账时编造默认值继续
- ❌ 不主动「优化」邻近无关代码（范围控制，只动当前 Task 涉及的代码）
- ❌ 不把 Story 拆得比文档更细（实施侧粒度跟设计侧对齐，便于回链）
- ❌ 不忽略 AC 上的评审意见标记（`⚠ 有疑问` / `✕ 需修改` 说明该 AC 已被修订，必须以最新 Then 为准）