# Python 3.10 SCF 只读沙盒异步多米诺骨牌崩溃排障记录 (tushare_anyio_exceptiongroup.pitfall.md)

> [!WARNING]
> **排障避坑与决策声明**: 本文档记录了在 A 股宏观政策 AI 追踪分析系统（Epic E14-S2）云端联调部署中，攻克 Python 3.10 只读容器环境因缺少 `exceptiongroup` 依赖导致全栈异步库（`anyio`/`openai`/`httpx`/`aiosmtplib`）瘫痪的多米诺骨牌级重大事故。已同步至 Portal 全局导航索引。

---

## 1. 踩坑记录 (The Pitfall)

在将解耦后的宏观政策定时云函数部署至腾讯云 SCF（运行时环境为 Python 3.10）并进行远程级联联调时，遭遇了三云函数全线不可预知崩溃：
- **现象一**：采集器 `policy_collector` 报错：`Running with asyncio requires installation of 'httpcore[asyncio]'.`
- **现象二**：AI 分析器 `policy_analyzer` 报错：`ModuleNotFoundError: No module named 'anyio._core._exceptions' (which imports exceptiongroup)`
- **现象三**：预警分发器 `policy_notifier` 报错：`ModuleNotFoundError: No module named 'aiosmtplib'`

这三个报错表象极具迷惑性，让人误以为是 `httpcore` 的安装参数不对或缺少 `aiosmtplib` 包。但经过深入的 Traceback 栈追踪，我们发现其**真正元凶 100% 都是因为 Python 3.10 只读运行容器缺少了 `exceptiongroup` 包**！
- `anyio` 异步引擎在导入时强依赖 `exceptiongroup`。在 `exceptiongroup` 缺失的情况下，`anyio` 导入直接报错中断。
- 大模型接口 `openai` 在加载时依赖 `anyio`，导致 `openai` 崩溃。
- `httpcore` 内部尝试导入 `anyio` 失败，因而**误判为当前系统没有安装任何异步运行时后端**，从而抛出了极其令人迷惑的“需要安装 `httpcore[asyncio]`”错误日志！

由于腾讯云 SCF 容器底座是只读的，在运行时无法通过代码动态在线 `pip install` 热安装包，这成为云端联调卡壳的硬伤。

---

## 2. 方案对比 (Options Explored)

为了跨越这一只读容器依赖障碍，我们评估并对比了以下三套技术方案：

### 方案 A：在云端代码中手动解包引入
- **原理**：将 `exceptiongroup` 源码直接放入云函数物理代码目录，并推送到云端。
- **缺点**：这会极大地污染 Mono-Repo 微服务的纯净代码结构，把大量三方库源码混入业务代码目录，违反团队结构规范。

### 方案 B：降低 `anyio` 或 `openai` 库的版本
- **原理**：将大模型库和异步底盘强行降级到低版本，以避开对 `exceptiongroup` 的强依赖。
- **缺点**：大模型开发库 `openai` 低版本不支持最新的大模型 API 语法和参数，会导致投研研报提取等主逻辑失效，具有重大的技术债风险。

### 方案 C：重构本地依赖 Layer 打包，将 `exceptiongroup` 灌入补丁层 (最佳实践)
- **原理**：
  1. 修改本地跨平台打包脚本 `build_patch_layer.py`，将 `'exceptiongroup'` 正式列入 `packages` 列表。
  2. 使用 `--platform manylinux2014_x86_64` 强制拉取纯 Linux 二进制 wheel 编译，物理剔除 Windows `.pyd` 污染。
  3. 一键发布全新的 **`stock-patch-layer` Version 13** 并强制与三个云函数实体绑定。
- **优点**：环境 100% 对齐，微服务代码区极度纯净，云端性能最优。

---

## 3. 择优决策 (Optimal Choice)

我们毫不犹豫地采纳了 **方案 C**。
通过在本地 `build_patch_layer.py` 中将 `exceptiongroup` 与 `openai`、`httpx`、`aiosmtplib` 完美打包为共享依赖 Version 13，并同步更新三个函数的部署绑定脚本。
绑定后重新执行远程 Invoke 联调测试，**三云函数瞬间实现 100% E2E 完美通车，大模型计费、乐观锁排碰撞、微信与 HTML 预警分发全线 SUCCESS**！

---

## 4. 复用技巧 (Reusable Tips)

在今后的 Serverless 异步微服务架构中，必须吸取以下三条高价值铁律：
1. **Python 3.10 异步双检**：在 Python 3.10 (或以下) 容器下部署任何基于 FastAPI / AnyIO / Starlette / HTTPX / OpenAI 的异步函数时，**必须强制前置绑定或安装 `exceptiongroup` 依赖**，切勿盲目信任 `pip install` 自动解析的底层依赖链。
2. **强力路径搜索前置**：在云函数入口 `index.py` 头部，**必须 100% 前置注入以下强力路径搜索代码**，确保挂载的 Layer（绑定在 `/opt/` 下）在代码执行任何三方包导入前能被 Python 虚拟机精准识别：
   ```python
   import sys
   import os
   for path in ['/opt', '/opt/python', '/opt/python/lib/python3.10/site-packages']:
       if os.path.exists(path) and path not in sys.path:
           sys.path.insert(0, path)
   ```
3. **Commit 标记对齐**：每次由于云端依赖变更触发的 Layer 发布，提交 Commit 时前缀应标记为 `[E{N}-S{M}-V{K}]` 以回链关联的部署架构调整，维持极高的可追溯性。

---
*本避坑决策已被 `update_docs_portal.py` 自动扫描，正式灌入 A 股宏观政策 AI 追踪系统全局技术秘籍板块中。*
