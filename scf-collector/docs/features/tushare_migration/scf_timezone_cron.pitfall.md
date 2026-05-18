# 踩坑记录：腾讯云 SCF 定时触发器 UTC 时区偏差与重建覆盖方案 (SCF Timezone Trigger Pitfall)

## 1. 踩坑记录 (The Pitfall)

在 A 股盘后分析系统中，今日（2026-05-18）收盘后检查行情数据时，发现 `stock_kline_daily` 表中所有今日的数据已成功入库，但 **`adj_factor` (复权因子) 字段 100% 为 `NULL`**。而在此之前的所有交易日，复权因子均完美填充。

### 根本原因定位
1. **云端服务器主导采集**：根据 Epic E13 设计，云端服务器 (`stock-manager-api`) 上的定时任务 `daily_market_overview_sync_job` 在 15:30 - 19:00 期间通过 `readiness_prober_job` 轮询 Tushare 接口。一旦 Canary 标的 (贵州茅台) 数据就绪，便立即触发全市场 K 线同步写入。但是，服务器端的写入方法 `MarketDataService.sync_stock_daily` 仅处理原始行情列，**不包含复权因子合并逻辑**，因此写入时 `adj_factor` 默认为 `NULL`。
2. **云函数 (SCF) 严重延迟**：本应在 16:30 触发并执行“行情与复权因子合并+第二层自愈修复”的 SCF 云函数 `stock-serverless-collector` 定时触发器 `DailyKline` **在收盘后未执行**。
3. **时区配置偏差**：
   - 腾讯云 SCF 的定时触发器（Timer Trigger）默认采用 **UTC 国际协调时区** 进行评估。
   - 原 `deploy.py` 中配置 of Timer cron was `"cron": "0 30 16 * * * *"`，设计初衷是北京时间 16:30 执行。
   - 但在 UTC 时区下，`16:30 UTC` 实际对应北京时间（CST）**次日凌晨 00:30**！
   - 这导致 SCF 触发器比预定时间**延迟了整整 8 小时**。因此在收盘后（17:00-19:00）用户查验时，因子的合并自愈任务尚未触发，导致复权因子表现为全空。

---

## 2. 方案对比与择优 (Options Explored & Decisions)

为了彻底解决盘后复权因子缺失及触发器管理失效的问题，我们评估了以下三种应对方案：

| 方案 | 优点 | 缺点 | 判定 |
| :--- | :--- | :--- | :--- |
| **方案 A：在云端服务器重构 K 线写入**<br/>在 `MarketDataService` 中也加入 Tushare 复权因子拉取与内存合并逻辑。 | 服务器直接一步到位，不依赖 SCF 补全。 | 1. 造成代码冗余（与 SCF 逻辑高度重叠）。<br/>2. 增加服务器端数据库长连接压力与 API 限流风险。 | **否决** |
| **方案 B：将 SCF 触发器时区换算为 UTC，但仅做覆盖**<br/>将 Cron 表达式中的小时减去 8 小时，直接覆盖部署。 | 改动极小，逻辑最简单。 | 腾讯云 API 在触发器重名时会报 `ResourceInUse` 错误，直接覆盖部署**无法更新已存在的 Cron 表达式**。 | **否决** |
| **方案 C：UTC 时区换算 + 自动删除重建触发器 (推荐)**<br/>1. 将所有触发器的小时统一减去 8 小时（CST $\rightarrow$ UTC）。<br/>2. 在 `deploy.py` 的部署逻辑中，创建触发器前先调用 `DeleteTrigger` API 物理删除旧触发器，随后全新创建。 | **彻底闭环**。既修正了时区偏差，又保证了每次执行 `deploy.py` 时，最新的 Cron 表达式能够 100% 成功同步更新至腾讯云控制台。 | 无明显缺点。 | **采纳** |

---

## 3. 择优决策与落地实现 (Optimal Choice & Action Taken)

### 3.1 部署脚本升级
我们修改了 [deploy.py](file:///home/ubuntu/microservice-stock/scf-collector/functions/daily_quotes/deploy.py) 的 `setup_triggers` 逻辑：
1. 将所有 Timer Cron 表达式换算为 UTC 时间（北京时间 - 8 小时）。
2. 引入 `DeleteTriggerRequest` 机制，在配置同步时首先将老触发器“物理清除”，随后重建，完美规避了腾讯云 API 的 `AlreadyExists` 准入門槛限制。

```python
def setup_triggers():
    """自动化配置定时触发器 (修复 UTC 时区差，并自动重建触发器更新配置)"""
    import json
    cred = credential.Credential(secret_id, secret_key)
    client = scf_client.ScfClient(cred, region)
    
    # 腾讯云 SCF 定时触发器采用 UTC 时间，北京时间 (CST) 需减去 8 小时
    triggers = [
        {
            "name": "DailyKline",
            "cron": "0 30 8 * * * *",  # 对应北京时间 16:30 CST
            "payload": {"op": "sync_kline_daily"}
        },
        {
            "name": "DailyAdjFactor",
            "cron": "0 35 8 * * * *",  # 对应北京时间 16:35 CST (调整为紧跟 K 线同步后运行)
            "payload": {"op": "sync_adj_factor"}
        },
        {
            "name": "DailyIndex",
            "cron": "0 40 8 * * * *",  # 对应北京时间 16:40 CST
            "payload": {"op": "sync_index_daily"}
        },
        {
            "name": "IntegrityFailOver",
            "cron": "0 0 9 * * * *",   # 对应北京时间 17:00 CST
            "payload": {"op": "validate_and_failover"}
        }
    ]
    
    print(f"[Trigger] Syncing triggers for {func_name}...")
    for t in triggers:
        # 1. 尝试删除已存在的触发器以允许更新 Cron 表达式
        try:
            del_req = models.DeleteTriggerRequest()
            del_req.FunctionName = func_name
            del_req.TriggerName = t["name"]
            del_req.Type = "timer"
            client.DeleteTrigger(del_req)
            print(f"[Trigger] Deleted existing trigger: {t['name']}")
        except Exception as de:
            pass

        # 2. 创建新触发器
        req = models.CreateTriggerRequest()
        ...
```

### 3.2 线上自动部署与物理验证
执行部署脚本，成功完成代码的更新、环境变量的同步以及触发器的重建：
```bash
$ ./scf-collector/venv/bin/python scf-collector/functions/daily_quotes/deploy.py
[Mode] Target function: stock-serverless-collector (Production)
[Package] Packaging code...
[Deploy] Updating code for stock-serverless-collector in ap-shanghai...
Success: Code Updated Successfully!
Waiting for function to be active (10s)...
[Config] Environment variables synchronized for stock-serverless-collector
[Trigger] Syncing triggers for stock-serverless-collector...
[Trigger] Deleted existing trigger: DailyKline
Success: Trigger DailyKline created (0 30 8 * * * *)
[Trigger] Deleted existing trigger: DailyAdjFactor
Success: Trigger DailyAdjFactor created (0 35 8 * * * *)
[Trigger] Deleted existing trigger: DailyIndex
Success: Trigger DailyIndex created (0 40 8 * * * *)
[Trigger] Deleted existing trigger: IntegrityFailOver
Success: Trigger IntegrityFailOver created (0 0 9 * * * *)
```

---

## 4. 真实数据验证 (True Source Evidence)

### 4.1 手动触发热修复
为了验证新部署代码的正确性，并即时修复今日已缺失的复权因子，我们通过腾讯云 SDK 对 `stock-serverless-collector` 发起了手动调用（Payload 指定今日 `2026-05-18` 行情批量合并任务）：
```python
payload = {
    "op": "sync_kline_daily",
    "trade_date": "2026-05-18"
}
```

### 4.2 数据库真实状态对比 (真源审计)

我们编写了 `check_today_kline.py` 脚本直接物理查验腾讯云数据库。

*   **手动修复前**：
    `stock_kline_daily` 表中 `2026-05-18` 的记录共 **`5,499`** 条，但 `adj_factor` 的 `NULL` 数量为 **`5,499` (100% 缺失)**！
*   **手动修复后**：
    再次物理执行查询，`2026-05-18` 的复权因子 `NULL` 数量已**完美归零**！
    ```
    === 检查最新的 stock_kline_daily 记录中不同日期的 adj_factor 分布 ===
    交易日: 2026-05-18, 总记录数: 5499, NULL数: 0, 因子最小值: 1.000000, 因子最大值: 10055.640000
    交易日: 2026-05-15, 总记录数: 5495, NULL数: 0, 因子最小值: 1.000000, 因子最大值: 10055.640000
    ```

---

## 5. 复用技巧与避坑指南 (Reusable Tips)

1. **时区红线**：所有运行在第三方云服务商（如腾讯云 SCF、AWS Lambda）上的定时任务触发器，**必须前置查阅其官方文档关于时区的默认配置**。腾讯云 SCF Timer 默认且仅支持 **UTC** 时区，编写 Cron 时必须手动进行 CST - 8 小时 的换算。
2. **触发器热更新技巧**：在编写自动化云部署脚本（IaC / Deployment Script）时，遇到触发器配置，不要盲目信任“覆盖更新”逻辑。最佳实践是在创建前**显式执行一次 DeleteTrigger（捕获并忽略不存在的异常）**，再全新创建，以确保修改 100% 生效。
