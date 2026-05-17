# Tushare Pro 2000积分 接口开发与限流治理最佳实践

> **文档标识**: `tushare_api_reference.kb.md`
> **知识归属**: 全局标准 (GLOBAL) · 最佳实践 (KB)
> **状态**: 已验证 / 在线探测完成 (2026-05-17)
> **最低积分门槛**: 2000 积分

---

## 1. 2000积分核心权限概述

本项目的 A 股盘后分析系统已全面切换至 **Tushare Pro** 作为数据唯一真源。经由在线探测工具 `scratch/history/tushare_permission_prober.py` 实机验证，我们所持有的 `TUSHARE_TOKEN` **已完全解锁 2000 积分以上权限**，其网络耗时、吞吐量和接口权限处于极佳状态。

### 1.1 权限与流控指标
- **调用频次上限**: 200次/分钟。
- **单日查询上限**: 常规数据无总量上限限制（单日最大 100,000 次请求）。
- **单次请求上限**: 默认大部分接口单次返回上限为 **6000 条** 记录。对于大批量回填，必须采用**个股循环**或**交易日分块**方式进行爬取。
- **并发访问红线**: **禁止多进程/多线程高并发刷接口**。全量回填必须采用**单线程串行**策略，结合休眠机制（Throttling）避免 IP 熔断。

---

## 2. 接口图鉴与字段对齐矩阵

以下为 2000 积分所支持的核心接口及其参数矩阵，供所有数据管线开发时进行「零误判」对齐。

### 2.1 每日基本面估值指标 (`daily_basic`)
> 用于获取个股每日的 PE、PB、换手率、量比等盘后量化指标。
- **起步积分**: 2000
- **物理表映射**: `dwd_stock_daily_basic`
- **主要输入参数**:
  | 参数名称 | 类型 | 必选 | 示例 | 描述 |
  | :--- | :--- | :--- | :--- | :--- |
  | `ts_code` | str | 否 | `600519.SH` | 股票代码（支持逗号分隔多个） |
  | `trade_date` | str | 否 | `20260508` | 交易日期 (YYYYMMDD) |
  | `start_date` | str | 否 | `20260101` | 开始日期 (YYYYMMDD) |
  | `end_date` | str | 否 | `20260508` | 结束日期 (YYYYMMDD) |
- **核心输出字段与类型对齐**:
  | 字段名称 | 类型 | 物理库映射 | 换算口径/规范 | 描述 |
  | :--- | :--- | :--- | :--- | :--- |
  | `ts_code` | str | `ts_code` | `600519.SH` | 股票代码 |
  | `trade_date` | str | `trade_date` | `2026-05-08` | 转换格式为 `YYYY-MM-DD` |
  | `pe` | float | `pe` | 原始值 | 市盈率（动） |
  | `pe_ttm` | float | `pe_ttm` | 原始值 | 市盈率（TTM） |
  | `pb` | float | `pb` | 原始值 | 市净率 |
  | `ps` | float | `ps` | 原始值 | 市销率 |
  | `ps_ttm` | float | `ps_ttm` | 原始值 | 市销率（TTM） |
  | `dv_ratio` | float | `dv_ratio` | 百分比 -> 小数 (除以 100) | 股息率 (如 3.2% 存为 0.032) |
  | `dv_ttm` | float | `dv_ttm` | 百分比 -> 小数 (除以 100) | 股息率（TTM） |
  | `turnover_rate` | float | `turnover_rate` | 百分比 -> 小数 (除以 100) | 换手率 (如 1.5% 存为 0.015) |
  | `turnover_rate_f`| float | `turnover_rate_free`| 百分比 -> 小数 (除以 100) | 换手率（自由流通股） |
  | `volume_ratio` | float | `volume_ratio` | 原始值 | 量比 |

---

### 2.2 财务报表三大表 (`balancesheet` / `income` / `cashflow`)
> 财务三表是基本面分析的生命线。Tushare 支持合并报表及单体报表。
- **起步积分**: 2000
- **主要输入参数**:
  | 参数名称 | 类型 | 必选 | 示例 | 描述 |
  | :--- | :--- | :--- | :--- | :--- |
  | `ts_code` | str | 是 | `600519.SH` | 必须单只股票拉取，避免总量超限 |
  | `period` | str | 否 | `20251231` | 报告期 (YYYYMMDD，支持季报、半年报、年报) |
  | `report_type` | str | 否 | `1` | 报表类型：1合并报表，2单体报表 (默认合并) |

- **资产负债表 (`balancesheet`) 核心字段**:
  * `ann_date` (公告日期), `end_date` (报告期末), `total_assets` (资产总计), `total_liab` (负债合计), `total_hldr_eqy_exc_min_int` (股东权益合计(不含少数股东权益))。
- **利润表 (`income`) 核心字段**:
  * `n_income` (净利润), `n_income_attr_p` (归属于母公司所有者的净利润), `revenue` (营业收入), `operating_cost` (营业成本)。
- **现金流量表 (`cashflow`) 核心字段**:
  * `net_cash_flows_oper_act` (经营活动产生的现金流量净额), `net_cash_flows_inv_act` (投资活动产生的现金流量净额), `net_cash_flows_fina_act` (筹资活动产生的现金流量净额)。

> [!IMPORTANT]
> **财务三表规范三红线**:
> 1. **披露日对齐**: 必须严格区分 `ann_date` (公告日) 与 `end_date` (报告期末)。在计算回测指标时，**只允许在 `ann_date` 之后**将该财报数据计入可用状态，严禁使用 `end_date` 造成「未来函数污染」。
> 2. **金额单位**: Tushare 官方财报金额单位为 **元**。严禁进行随意的除以 `10^4` 或 `10^8` 换算，必须以「元」为统一精度。
> 3. **缺失值审计**: 部分字段在非年报中可能为 Null。回填结束后必须执行 `COUNT(*) WHERE IS NULL` 审计，区分「数据本身缺失」与「程序拉取失败」。

---

### 2.3 财务指标数据 (`fina_indicator`)
> 包含毛利率、净利率、ROE、ROA、流动比率、速动比率等已经计算好的高级财务指标。
- **起步积分**: 2000
- **物理表映射**: `dwd_stock_financial_indicators`
- **核心输出字段**:
  | 字段名称 | 类型 | 物理库映射 | 换算口径/规范 | 描述 |
  | :--- | :--- | :--- | :--- | :--- |
  | `roe` | float | `roe` | 百分比 -> 小数 (除以 100) | 净资产收益率 (ROE) |
  | `gpm` | float | `gross_profit_margin`| 百分比 -> 小数 (除以 100) | 销售毛利率 (GPM) |
  | `npm` | float | `net_profit_margin` | 百分比 -> 小数 (除以 100) | 销售净利率 (NPM) |
  | `assets_to_liabilities`| float | `debt_asset_ratio`| 百分比 -> 小数 (除以 100) | 资产负债率 |
  | `current_ratio`| float | `current_ratio` | 原始值 | 流动比率 |
  | `quick_ratio` | float | `quick_ratio` | 原始值 | 速动比率 |

---

### 2.4 业绩预告与快报 (`forecast` / `express`)
> 用于在正式财报披露前获取业绩修正及前瞻数据。
- **起步积分**: 2000
- **核心字段**:
  * `forecast`: `ann_date` (公告日期), `end_date` (报告期), `type` (业绩预告类型: 预增/预减/扭亏/亏损), `p_change_min` (净利润比上年同期增幅下限), `p_change_max` (净利润比上年同期增幅上限)。
  * `express`: `ann_date` (公告日期), `end_date` (报告期), `revenue` (营业收入), `yoy_op` (营业利润同比增长率)。

---

### 2.5 分红送股与财报披露日历 (`dividend` / `disclosure_date`)
> 用于追踪公司分红派息事件，以及预测下一次财报披露窗口。
- **起步积分**: 2000
- **核心字段**:
  * `dividend`: `imp_ann_date` (分红方案实施公告日), `base_date` (股权登记日), `ex_date` (除权除息日), `cash_div_tax` (每股派息(含税)), `cash_div` (每股派息(税后))。
  * `disclosure_date`: `end_date` (报告期), `pre_date` (预计披露日期), `actual_date` (实际披露日期)。

---

## 3. 限流治理与高可用接入规范

由于 Tushare 2000 积分有每分钟 **200次** 的严格频次限制，如果不加控制地运行全量回填或并行请求，会频繁触发 `接口调用超限` 异常。

### 3.1 异步与线程安全最佳实践 (Async standard)
由于 Tushare 官方 SDK `tushare` 是一个基于 `requests` 的**同步阻塞库**，在 FastAPI 异步服务中直接调用会阻塞整个事件循环（Event Loop）。
**黄金法则**: 必须使用 `asyncio.to_thread` 将其包装为非阻塞的异步任务。

```python
import asyncio
import tushare as ts
import pandas as pd

# 初始化 Tushare Pro 客户端
pro = ts.pro_api(TUSHARE_TOKEN)

async def async_query_tushare(api_name: str, **kwargs) -> pd.DataFrame:
    """
    非阻塞异步 Tushare 接口调用，包含退避重试与熔断保障
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 包装同步 I/O，使其运行在独立的线程池中，避免阻塞主事件循环
            df = await asyncio.to_thread(pro.query, api_name, **kwargs)
            return df
        except Exception as e:
            err_msg = str(e)
            
            # 匹配限流错误
            if any(indicator in err_msg for indicator in ["每分钟内最多查询", "频次限制", "频繁", "超限"]):
                # 指数退避等待 (1s -> 3s -> 9s)
                wait_time = 3 ** attempt
                logger.warning(f"Tushare API [{api_name}] 限流触顶，休眠 {wait_time}s 后重试 ({attempt+1}/{max_retries})...")
                await asyncio.sleep(wait_time)
                continue
                
            # 积分不足直接抛出，无需重试
            if "积分" in err_msg or "权限" in err_msg:
                logger.critical(f"Tushare 权限错误: {err_msg}")
                raise PermissionError(f"Tushare 接口 [{api_name}] 未授权: {err_msg}")
                
            raise e
            
    raise TimeoutError(f"Tushare 接口 [{api_name}] 经过 {max_retries} 次重试仍被限流")
```

### 3.2 2000积分全量回填 Throttling 策略
在进行历史（如 2010 年至今）基本面和财务数据全量回填时，请严格在循环中加入以下 Throttling 休眠，防止请求积压：

1. **`daily_basic` (估值指标)**:
   - 策略: 按交易日（`trade_date`）串行分块抓取全市场。
   - 单请求限制: 每次获取 1 个交易日（约 5000+ 条记录，不超过 6000 上限）。
   - Throttling 延时: **每次请求后强行 `await asyncio.sleep(0.35)`**。每分钟约发出 170 次请求，安全处于 200次/分钟 阈值内。

2. **财务三表 (`balancesheet`/`income`/`cashflow`)**:
   - 策略: 按个股（`ts_code`）串行抓取完整历史。
   - 单请求限制: 每次拉取 1 只股票的所有历史季度财报（约 60 条记录）。
   - Throttling 延时: 由于财务接口数据量大且积分占用敏感，**每次抓取个股后强行 `await asyncio.sleep(1.5)`**。不仅能完全规避流控，也能保障混合云写入性能。

---

## 4. 自动门户更新验证

本篇最佳实践 (`tushare_api_reference.kb.md`) 创建后，已通过以下标准管道编译进入系统门户索引：
1. 使用 `scripts/md_to_html_premium.py` 将本文档转换为高级暗黑主题 HTML 副本。
2. 运行 `scripts/update_docs_portal.py`，将本文同步载入 **全局文档门户 index.html** 和 **AI-Native 机器友好索引 docs_portal_index.json**。
3. 确保后续任何 AI Agent 会话启动时，均可通过读取 `docs_portal_index.json` 秒载本篇 Tushare API 指南，实现无缝的能力沉淀。
