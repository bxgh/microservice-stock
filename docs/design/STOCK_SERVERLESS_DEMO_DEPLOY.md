# Stock-Serverless-Collector 部署示例 (serverless.yml)

## 1. 核心概念
在新项目中，我们将使用 **Serverless Framework** 来管理函数。它允许我们通过一个 YAML 文件定义函数的所有属性。

## 2. 示例配置文件 `serverless.yml`

```yaml
# serverless.yml

# 项目名称
component: scf
name: stock-serverless-collector

# 全局配置
inputs:
  name: data-hub-service
  src: 
    src: ./src           # 代码所在目录
    exclude:
      - .env
      - tests/**
  region: ap-guangzhou   # 您的腾讯云地域
  runtime: Python3.10    # 使用 Python 3.10 原生运行时
  memorySize: 256        # 内存配置 (MB)
  timeout: 900           # 超时时间 (s)
  
  # 环境变量
  environment:
    variables:
      LOG_LEVEL: INFO
      DB_HOST: ${env:DB_HOST}  # 从本地环境变量或密钥管理读取
      TUSHARE_TOKEN: ${env:TUSHARE_TOKEN}
      TZ: Asia/Shanghai

  # 网络配置 (必须关联 VPC 才能访问内网数据库)
  vpcConfig:
    vpcId: vpc-xxxxxx    # 替换为您的 VPC ID
    subnetId: subnet-xxxx # 替换为您的子网 ID

  # 依赖层 (Layers) - 将 Pandas 等重型库放在层里，加快部署
  layers:
    - name: pandas-layer
      version: 1

  # 触发器配置
  triggers:
    - timer: # 每日盘后自动运行
        name: daily_collect_timer
        parameters:
          cronExpression: '0 30 15 * * MON-FRI *' # 周一至周五 15:30
          enable: true
          argument: '{"task": "daily_kline"}' # 传递给函数的参数

    - apigw: # 支持手动触发 (HTTP)
        name: manual_trigger_gw
        parameters:
          protocols:
            - http
            - https
          endpoints:
            - path: /collect
              method: POST
```

## 3. 函数入口代码示例 `src/index.py`

```python
import json
import logging
from datetime import datetime

logger = logging.getLogger()

def main_handler(event, context):
    """
    SCF 函数入口
    event: 触发器传来的参数
    context: 运行时上下文 (包含 requestId 等)
    """
    request_id = context.get_request_id()
    logger.info(f"Task started. RequestId: {request_id}")
    
    # 解析参数 (从定时器或 API 网关)
    try:
        if "body" in event: # API 网关触发
            args = json.loads(event["body"])
        else: # 定时器触发
            args = event.get("Message", {})
            if isinstance(args, str):
                args = json.loads(args)
    except Exception:
        args = {}

    task_type = args.get("task", "unknown")
    
    # 业务逻辑执行
    # ... 调用 data_collector.run(task_type) ...
    
    return {
        "isBase64Encoded": False,
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "status": "success",
            "task": task_type,
            "requestId": request_id
        })
    }
```

## 4. 如何部署？

1. 安装 Serverless Framework: `npm install -g serverless`
2. 在项目根目录执行: `scf deploy` (需先配置 `TENCENT_SECRET_ID` 和 `TENCENT_SECRET_KEY`)

---
*Created by Antigravity AI - 2026-05-11*
