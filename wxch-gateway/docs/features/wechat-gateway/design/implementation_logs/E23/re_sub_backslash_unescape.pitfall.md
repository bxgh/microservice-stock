# 踩坑记录：Python re.sub 模板替换中的反斜杠二次解析与 JavaScript 注入白屏故障

在 A 股盘后系统微服务开发及自动化文档编译工具链的维护中，针对 JSON/Markdown 文本进行正则模板替换时，容易遭遇 Python `re.sub` 特有的反斜杠二次解析陷阱。该陷阱会导致合法的 JSON 转义字符被还原为物理控制字符（如 `\n` 被还原为真实换行），进而在前端渲染或脚本中引发 JavaScript `SyntaxError`，导致整个页面彻底白屏。

---

## 1. 踩坑记录 (The Pitfall)

### 1.1 业务场景
在 Epic E23 的编译流程中，编译脚本 [parse_epic.py](file:///e:/gitee/microservice-stock/.agents/skills/epic-story-doc/parse_epic.py) 负责解析 `maxim-check.md` 并使用 JSON 格式的 `DOC_DATA` 注入到 HTML 评审模板中。为了支持对带空格占位符（如 `{{EPIC_DATA}}` 与 `{{ EPIC_DATA }}`）的稳健替换，编译脚本从简单的 `str.replace()` 升级为了正则表达式替换：
```python
html = re.sub(r'{{\s*EPIC_DATA\s*}}', json.dumps(data, ensure_ascii=False), template)
```

### 1.2 异常现象
重新生成的 `review_E23.html` 在浏览器中打开后为完全空白的页面，控制台报如下致命错误：
`Uncaught SyntaxError: Invalid or unexpected token`

### 1.3 原因剖析
通过提取生成的 HTML 文件发现，JSON 串中的 Markdown 段落（如 `E23-S1` 的 `desc`，包含换行符 `\n`）在注入后，原本合法的 JS 字符串 `\\n` 变成了真实的物理换行：
```javascript
// 崩溃的生成产物：
"desc": "**作为** 用户  
**我希望** 看到的格言有质量、有深度并自动分类  
**以便** 每天...
```
这导致 JavaScript 解析器无法在单行内找到双引号的闭合标记，抛出 `SyntaxError` 语法错误。

这源于 Python `re.sub` 的机制：**当第二个参数 `repl` 是一个普通的字符串时，`re.sub` 会自动解析其中的反斜杠转义序列。**
例如：
* `json.dumps` 序列化时将换行符转义为两个字符的字符串 `\n`（即 `\\n`）。
* `re.sub` 接收该字符串后，将 `\\n` 二次解析为单个物理换行符 `\n`。
* 结果是，本应输出在 HTML 里的 `\\n` 文本变成了真实的物理回车，彻底破坏了 JavaScript 代码的语法结构。

---

## 2. 方案对比 (Options Explored)

为了避免 `re.sub` 对替换字符串中反斜杠进行二次转义解析，我们评估了以下三种应对方案：

| 方案 | 具体实现 | 优点 | 缺点 |
|---|---|---|---|
| **方案 A: 双重转义** | 在 `json.dumps` 后使用 `replace('\\', '\\\\')` 强行将单个反斜杠替换为双反斜杠 | 实现简单，不改变 `re.sub` 参数类型 | 不够稳健，若未来 JSON 中包含其他特殊反斜杠组合，极易造成逻辑混乱和漏防 |
| **方案 B: 放弃正则，退回普通替换** | 退回到 `template.replace('{{EPIC_DATA}}', json_str)` 逻辑 | 绝对不会解析反斜杠 | 无法包容占位符中的各种空格排版变化，容错性低 |
| **方案 C: 使用 Lambda 包装替换值 (推荐)** | 将 `repl` 参数修改为 Callable（Lambda 函数）：<br>`re.sub(pattern, lambda m: json_str, template)` | **最稳健**。Python 官方规定：若 `repl` 为可调用对象，则其返回值将被视为 **字面量原始字符串**，绝不对其中的反斜杠做任何二次解析。同时保留了正则匹配的灵活性。 |

---

## 3. 择优决策 (Optimal Choice)

最终选择 **方案 C（Lambda 函数封装）**。这是最优雅、最高效且最稳健的 Pythonic 解决方案。

### 修复后的核心代码
```python
# 使用 lambda 避免 re.sub 自动解析 JSON 字符串中的反斜杠（如 \n 变为换行）
html = re.sub(r'{{\s*EPIC_DATA\s*}}', lambda m: json.dumps(data, ensure_ascii=False), template)
```
通过采用该方法，即使 JSON 数据包含再多复杂的 Markdown 换行符（`\\n`）、Windows 路径（`\\\\`）或特殊字符，编译出的 HTML 也绝不会失真退化。

---

## 4. 复用技巧 (Reusable Tips)

1. **Python 正则替换准则**：在 Python 中，只要使用 `re.sub` 进行任何大文本或结构化数据（如 JSON、XML、代码片段）的模板注入，**一律使用 Lambda 包装替换值**：
   * ❌ *错误*：`re.sub(pattern, payload, template)` （会导致 `payload` 中的 `\n`、`\t` 等惨遭二次解析）
   *  *正确*：`re.sub(pattern, lambda m: payload, template)` （原汁原味注入字面量，100% 安全）
2. **多端排查闭环**：当生成的 HTML 页面出现空白时，切忌盲目猜测，应当：
   * 在 Chrome/Edge 控制台查看 `Console` 报错（可立即定位 `SyntaxError` 所在行数）。
   * 在 Python 中使用 `repr(lines[n])` 打印 HTML 文件的原始字符表示，能够瞬间揭示隐藏的物理换行或隐藏转义字符。
