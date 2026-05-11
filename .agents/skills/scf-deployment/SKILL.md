---
name: 腾讯云 SCF 部署与调试 (scf-deployment)
description: 指导 Agent 如何编写 serverless.yml、打包 Layer 以及在腾讯云 SCF (Serverless Cloud Function) 上部署和调试应用。
---

# 腾讯云 SCF 部署规范与工作流

当用户要求部署、重构、或测试基于腾讯云 Serverless 的架构时，请严格遵守以下操作规程。

## 1. 核心约束
- **运行环境**: 原生环境仅支持至 `Python 3.10`。
- **无状态设计**: SCF 实例随时可能被销毁，**严禁**将临时文件或全局状态保存在内存中。持久化需依赖 MySQL 或 COS（对象存储）。
- **调度剥离**: **严禁**在代码中使用 `APScheduler`、`time.sleep()` 轮询等长驻模式。必须配置 `timer` 触发器交由云端调度。

## 2. Serverless 框架结构 (serverless.yml)
编写或修改 `serverless.yml` 时，必须符合腾讯云组件规范 (`component: scf`)。

### 基础模板参考:
```yaml
component: scf
name: stock-scf-app

inputs:
  name: function-name
  src:
    src: ./src        # 代码源目录
    exclude:
      - .env          # 严禁将 .env 传至云端
      - .git/**
  region: ap-guangzhou
  runtime: Python3.10
  memorySize: 256
  timeout: 900
  
  # VPC 配置 (连接内网数据库必填)
  vpcConfig:
    vpcId: vpc-xxx
    subnetId: subnet-xxx

  # 层配置 (加速部署与冷启动)
  layers:
    - name: data-science-layer
      version: 1

  # 触发器配置
  triggers:
    - timer:
        name: daily_task
        parameters:
          cronExpression: '0 30 15 * * MON-FRI *'
          enable: true
          argument: '{"action": "collect"}'
```

## 3. Layer (层) 分离策略
为防止部署包体积过大导致报错或冷启动慢，对于 `mootdx`、`pandas` 等依赖包：
1. **禁止** 将它们直接放在代码的 `src/` 根目录。
2. **要求** 将它们安装在一个单独的目录（如 `layers/`），并作为 SCF Layer 上传。
3. Agent 操作指令：使用 `pip install -r requirements.txt -t layers/python/` 组织依赖。

## 4. 调试与排错 (Troubleshooting)
- **依赖不兼容**: Windows 环境下安装的 C 语言扩展库 (如 NumPy/Pandas) 上传到基于 Linux 的 SCF 可能会报错。**解决思路**：必须下载 `manylinux` 的 whl 包，或者利用腾讯云在线依赖安装功能。
- **冷启动超时**: 遇到首屏响应慢的问题，检查 `pool_recycle` 配置并确认数据库唤醒重试逻辑已激活。
- **日志断层**: 提醒用户或通过代码接入腾讯云 CLS 日志系统，使用标准 `logging` 模块即可自动上报。

## 5. 参考资源
- [TencentCloud Serverless 官方 GitHub](https://github.com/TencentCloud/serverless)
