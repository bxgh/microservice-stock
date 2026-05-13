---
name: 腾讯云 SCF 部署与调试 (scf-deployment)
description: 指导 Agent 如何通过腾讯云 SDK 直接完成 SCF 的全流程部署（代码更新、Layer 打包发布及绑定），以及解决跨平台依赖与只读环境问题的关键策略。
---

# 腾讯云 SCF 部署规范与实战避坑指南

当用户要求部署、重构、或测试基于腾讯云 Serverless 的架构时，请严格遵守以下基于真实环境实战总结的操作规程。本规范推荐使用 **Tencent Cloud SDK (Python)** 直接部署，而非笨重的 Serverless CLI。

## 1. 核心环境约束与解决方案 (Critical)

- **运行环境**: 腾讯云函数底层为只读文件系统 (`/home/qcloud` 等路径不可写)，仅 `/tmp` 具有写权限。
  - **🚨 避坑方案 (Mootdx 等底层包报错)**: 必须在入口文件 (`index.py`) **任何第三方库导入之前**，强制重定向内核环境变量：
    ```python
    import os
    os.environ['HOME'] = '/tmp'
    os.environ['MOOTDX_CACHE_DIR'] = '/tmp'
    ```
- **网络隔离 (VPC)**: 绑定 VPC 访问私有数据库后，SCF 会失去默认公网访问能力。必须显式开启 `PublicNetConfig` 才能访问外部数据源 API。
- **生命周期 (Asyncio)**: 在 `asyncio.run` 环境下，必须显式在 `finally` 中关闭异步连接池，防止 Event Loop 关闭后的 GC 报错。
- **无状态设计**: SCF 实例随时可能被销毁，严禁将持久状态保存在内存中。
- **调度剥离**: 严禁使用 `APScheduler` 等长驻轮询，改用 SCF Timer 触发器或外部事件流。

## 2. API-Driven 全流程部署策略 (取代 serverless.yml)

相比维护 `serverless.yml` 并依赖 CLI，在微服务架构中，强烈建议直接编写自动化部署脚本 (`deploy.py`, `deploy_layer.py`)。

### 核心 SDK 方法：
1. **代码发布**: `client.UpdateFunctionCode(req)` (将代码 zip 转 base64 上传)
2. **Layer 发布**: `client.PublishLayerVersion(req)` (上传 layer.zip)
3. **Layer 绑定**: `client.UpdateFunctionConfiguration(req)` (更新 Layers 配置数组)

**注意**: 更新 Layer 配置后，云端已有容器可能不会立刻挂载新层。**最佳实践是在绑定新 Layer 之后，立刻执行一次 `UpdateFunctionCode` 强制刷新容器实例 (Cold Start)。**

## 3. Layer (层) 打包实战：彻底解决跨平台编译循环

在 Windows 环境下打包包含 C 扩展（如 Pandas, Cryptography）的库供云端 Linux 使用时，极易陷入 `pip` 解析死循环。

### 策略 A：增量纯 Python 补丁层 (Patch Layer) - 首选！
如果云端已经存在一个包含庞大底层库（Pandas/Numpy）的底层 Layer，并且你只需新增轻量级包（如 EasyQuotation），**绝对不要尝试重新打全量包**。
- **做法**: 仅针对缺失包打增量 Layer。
- **关键指令**: 必须加上 `--no-deps` 防止它递归下载本地系统不兼容的底层 C 库：
  `pip install easyquotation mootdx -t layers/python --no-cache-dir --no-deps`

### 策略 B：Docker Linux 环境原生构建
若必须打包全量 C 扩展库，严禁在 Windows 主机直接使用 `--platform manylinux2014_x86_64`。必须启动临时 Docker 容器构建：
```python
docker_cmd = [
    'docker', 'run', '--rm',
    '-v', f"{mount_path}:/app", # 注意：Windows 挂载目录应为 /e/xxx/ 格式防止 invalid mode
    '-w', '/app',
    'python:3.10-slim',
    'pip', 'install', '-r', 'requirements.txt', '-t', 'layers/python'
]
```

## 4. 远程验证与 Debug (Remote Trigger)

完成部署后，**必须**编写远程触发脚本，使用 `models.InvokeRequest()` 同步触发 SCF，并将返回值与详细报错信息打印到本地。
这能 100% 暴露出因网络隔离、端口拦截（如 7709 被封）或 Layer 版本缺失导致的云端真实问题，避免被本地代理造成的“伪连通”误导。

## 5. 核心避坑指南 (Hard-won Lessons)

### 5.1 VPC 环境下的公网访问
**陷阱**：SCF 绑定 VPC 访问私有数据库后，会默认失去公网访问权限，导致请求外部数据源 API 失败。
**方案**：在 `UpdateFunctionConfiguration` 时必须显式配置：
```python
req.PublicNetConfig = models.PublicNetConfigIn()
req.PublicNetConfig.PublicNetStatus = "ENABLE"
req.PublicNetConfig.EipConfig = models.EipConfigIn()
req.PublicNetConfig.EipConfig.EipStatus = "DISABLE" # 使用共享公网 IP
```

### 5.2 异步连接池的优雅退出
**陷阱**：使用 `asyncio.run` 时，Loop 会在任务结束时关闭，而 `aiomysql` 的 GC 可能在关闭后触发，产生 `RuntimeError: Event loop is closed`。
**方案**：在业务逻辑的 `finally` 块中显式关闭连接池：
```python
try:
    # 业务代码
finally:
    await DBManager.close_pool() # 必须在 asyncio.run 退出前完成
```

### 5.3 定时触发器 (Timer Trigger) 的参数嵌套陷阱 ⭐
**陷阱**：在 SCF 控制台配置的“附加信息”（CustomArgument）不会直接映射到 `event` 根对象。腾讯云会将其作为字符串封装在 `event["Message"]` 字段中。如果直接使用 `event.get("param")`，会因为拿不到值而误触发代码中的默认逻辑。

**方案**：所有 `index.py` 入口函数必须包含“解包”逻辑，且严禁在未确认参数的情况下使用业务默认值：
```python
import json

def main_handler(event, context):
    # 1. 尝试从 Message 字段解包 (兼容 Timer Trigger)
    if 'Message' in event:
        try:
            msg_data = json.loads(event['Message'])
            if isinstance(msg_data, dict):
                event.update(msg_data)
        except Exception as e:
            print(f"Warning: Failed to parse Message field: {e}")
    
    # 2. 获取参数，缺失则显式报错，避免静默失败
    op = event.get('op')
    if not op:
         # 抛出异常或记录 unknown，严禁静默执行默认任务
        raise Exception("Missing required parameter: 'op'")
```
