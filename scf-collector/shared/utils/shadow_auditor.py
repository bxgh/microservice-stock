import json
import logging
import asyncio
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
from shared.db.dao import StockDAO
from shared.collectors.akshare_adapter import AkShareAdapter

logger = logging.getLogger(__name__)

class ShadowAuditor:
    """
    影子审计引擎：对比主源 (DB 中已入库数据) 与备份源 (AkShare 实时接口)
    产出对账报告并存库
    """

    @staticmethod
    def _fetch_akshare_spot_sync():
        """同步拉取 AkShare 全量快照（在线程池中运行）"""
        import akshare as ak
        # 优先尝试 EM 源，失败后回退 Sina 源
        try:
            df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                return df, 'em'
        except Exception as em_e:
            logger.warning(f"EM source failed: {em_e}. Falling back to Sina...")
        
        df = ak.stock_zh_a_spot()
        return df, 'sina'

    async def run_audit(self, trade_date: str) -> Dict[str, Any]:
        """执行全量 7 维对账流程"""
        logger.info(f"Starting 7D shadow audit for {trade_date}...")

        # 1. 获取主源数据 (DB)
        primary_data = await StockDAO.get_kline_daily(trade_date)
        if not primary_data:
            logger.warning(f"No primary data in DB for {trade_date}, skipping audit.")
            return {"status": "SKIPPED", "message": "No primary data", "trade_date": trade_date}

        # 2. 拉取备份源 (AkShare)
        try:
            raw_df, source_type = await asyncio.get_running_loop().run_in_executor(None, self._fetch_akshare_spot_sync)
        except Exception as e:
            logger.error(f"Failed to fetch AkShare data: {e}")
            return {"status": "ERROR", "message": f"AkShare fetch failed: {e}", "trade_date": trade_date}

        if raw_df is None or raw_df.empty:
            return {"status": "ERROR", "message": "AkShare returned empty data", "trade_date": trade_date}

        # 3. 适配转换
        records = raw_df.to_dict(orient='records')
        cols = raw_df.columns.tolist()
        if '代码' in cols:
            ak_models = AkShareAdapter.from_em_spot_records(records, trade_date)
            source_type = 'em' # 以列名判定结果为准，强制覆盖探测值
        else:
            ak_models = AkShareAdapter.from_spot_records(records, trade_date)
            source_type = 'sina'

        if not ak_models:
            return {"status": "ERROR", "message": "Adaptation failed", "trade_date": trade_date}

        # [E7-S4] 加载盘前基准快照
        snapshot = await StockDAO.get_universe_snapshot(trade_date)
        baseline_n = snapshot['expected_count'] if snapshot else len(df_p)
        baseline_codes = set(snapshot['codes']) if snapshot else set(df_p['ts_code'].tolist())

        # 4. 内存对账 (Pandas)
        df_p = pd.DataFrame(primary_data)
        df_s = pd.DataFrame([m.model_dump() for m in ak_models])

        # 定义对账字段矩阵
        audit_fields = ['open', 'high', 'low', 'close', 'volume', 'amount', 'pct_chg']
        
        # 强制类型转换并合并
        for f in audit_fields + ['ts_code']:
            df_p[f] = pd.to_numeric(df_p[f], errors='coerce') if f != 'ts_code' else df_p[f].astype(str)
            df_s[f] = pd.to_numeric(df_s[f], errors='coerce') if f != 'ts_code' else df_s[f].astype(str)

        merged = pd.merge(df_p[['ts_code'] + audit_fields],
                          df_s[['ts_code'] + audit_fields],
                          on='ts_code', suffixes=('_p', '_s'))

        overlap_count = len(merged)
        if overlap_count == 0:
            return {"status": "FAIL", "message": "Zero overlap between sources", "trade_date": trade_date}

        # 计算 7 维 MAE
        mae_results = {}
        for f in audit_fields:
            mae_results[f"{f}_mae"] = float((merged[f'{f}_p'] - merged[f'{f}_s']).abs().mean())

        # 异常值捕获：收盘价偏差 > 1%
        merged['price_diff_rate'] = (merged['close_p'] - merged['close_s']).abs() / merged['close_p']
        outliers = merged[merged['price_diff_rate'] > 0.01]
        outlier_count = len(outliers)

        # 5. 判定状态
        # 修改为基于 09:30 基准的覆盖率判定
        primary_codes = set(df_p['ts_code'].tolist())
        coverage_rate = len(primary_codes) / baseline_n if baseline_n > 0 else 0
        diff_list = list(baseline_codes - primary_codes) if snapshot else []

        status = "PASS"
        if coverage_rate < 0.98: status = "WARNING"
        if coverage_rate < 0.95: status = "FAIL"
        if mae_results['close_mae'] > 0.05: status = "FAIL"
        if outlier_count > 10: status = "FAIL"

        # 6. 生成报告内容
        report_content = self._generate_report_v2(
            trade_date, df_p, df_s, merged, mae_results, outlier_count, status, source_type, 
            baseline_n, coverage_rate
        )

        # 7. 存库
        audit_result = {
            "trade_date": trade_date,
            "task_name": "ShadowAudit",
            "primary_source": "Tushare",
            "secondary_source": f"AkShare({source_type})",
            "primary_count": len(df_p),
            "secondary_count": len(df_s),
            "overlap_count": overlap_count,
            "expected_count": baseline_n, 
            "coverage_rate": round(coverage_rate, 4),
            "status": status,
            "report_path": "",
            "report_content": report_content,
            "outlier_count": outlier_count,
            "diff_list": json.dumps(diff_list[:1000]), # 限制存储长度
            "source_tag": "TUSHARE_P0", # 默认标记，Fail-over 时由 index.py 覆盖
            **{k: round(v, 6) for k, v in mae_results.items()}
        }
        
        try:
            await StockDAO.save_audit_log(audit_result)
        except Exception as db_e:
            logger.error(f"Failed to save audit log: {db_e}")

        logger.info(f"Audit completed: {status}. Overlap: {overlap_count}, Close MAE: {mae_results['close_mae']:.4f}")
        return audit_result

    def _generate_report_v2(self, date, df_p, df_s, merged, mae_res, outlier_count, status, src_type, baseline_n, coverage) -> str:
        """生成增强版 Markdown 报告"""
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 提取价格异常样本预览
        outlier_sample = "无"
        if outlier_count > 0:
            sample_df = merged[merged['price_diff_rate'] > 0.01].sort_values('price_diff_rate', ascending=False).head(10)
            outlier_sample = sample_df[['ts_code', 'close_p', 'close_s', 'price_diff_rate']].to_markdown(index=False)

        # 提取成交量误差 Top 5
        merged['vol_diff'] = (merged['volume_p'] - merged['volume_s']).abs()
        vol_top5 = merged.sort_values('vol_diff', ascending=False).head(5)
        vol_sample = vol_top5[['ts_code', 'volume_p', 'volume_s', 'vol_diff']].to_markdown(index=False)

        content = f"""# 影子审计报告 (Shadow Audit Report)
        
## 1. 基础信息
- **交易日期**: {date}
- **审计时间**: {now_str}
- **判定结论**: **{status}**
- **备份源类型**: AkShare ({src_type})

## 2. 完整性审计 (Integrity)
| 指标 | 数值 | 备注 |
| :--- | :--- | :--- |
| **理论应采 (09:30 基准)** | **{baseline_n}** | meta_universe_snapshot |
| 实际入库 (主源) | {len(df_p)} | 数据库已入库 |
| **最终覆盖率** | **{coverage*100:.2f}%** | 熔断阈值: 95% |
| 影子源 (AkShare) | {len(df_s)} | 接口实时抓取 |
| 重叠样本数 | {len(merged)} | 参与对账总数 |

## 3. 7维对账矩阵 (7D MAE Matrix)
| 字段 | 平均绝对误差 (MAE) | 状态 |
| :--- | :--- | :--- |
| 开盘价 (Open) | {mae_res['open_mae']:.4f} | {"-" if mae_res['open_mae'] < 0.1 else "WARN"} |
| 最高价 (High) | {mae_res['high_mae']:.4f} | {"-" if mae_res['high_mae'] < 0.1 else "WARN"} |
| 最低价 (Low) | {mae_res['low_mae']:.4f} | {"-" if mae_res['low_mae'] < 0.1 else "WARN"} |
| **收盘价 (Close)** | **{mae_res['close_mae']:.4f}** | **{"PASS" if mae_res['close_mae'] < 0.05 else "FAIL"}** |
| 成交量 (Volume) | {mae_res['volume_mae']:.2f} | 手 |
| 成交额 (Amount) | {mae_res['amount_mae']:.2f} | 元 |
| 涨跌幅 (PctChg) | {mae_res['pct_chg_mae']:.6f} | 小数 |

## 4. 风险预警 (Risk Alerts)
- **价格异常值数量**: {outlier_count} (偏差 > 1%)
- **价格异常样本预览 (Top 10)**:
{outlier_sample}

- **成交量误差 Top 5 (定位量纲异常)**:
{vol_sample}

---
*Generated by ShadowAuditor v1.3 - Persistence Layer Ready*
"""
        return content
