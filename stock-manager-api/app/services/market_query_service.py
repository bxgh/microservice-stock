import datetime
from typing import Dict, Any, List, Optional
from app.utils.database import db
from app.utils.logger import get_logger

logger = get_logger("stock-manager.market_query")


class MarketQueryService:
    async def get_l1_overview(
            self, target_date: str = None) -> Optional[Dict[str, Any]]:
        """获取 L1 市场全景数据"""
        try:
            if not target_date:
                # 获取最新日期
                sql_latest = "SELECT MAX(trade_date) FROM ads_l1_market_overview"
                res = await db.execute(sql_latest)
                target_date = str(res[0][0]) if res and res[0][0] else None

            logger.info(f"Fetching L1 overview for date: {target_date}")

            if not target_date:
                return None

            # 1. 获取主记录 (使用显式列名，确保映射正确)
            columns = [
                'trade_date',
                'idx_sh_close',
                'idx_sh_pct',
                'idx_sz_close',
                'idx_sz_pct',
                'idx_cyb_close',
                'idx_cyb_pct',
                'idx_kc50_close',
                'idx_kc50_pct',
                'idx_bz50_close',
                'idx_bz50_pct',
                'idx_hs300_close',
                'idx_hs300_pct',
                'idx_zz500_close',
                'idx_zz500_pct',
                'idx_zz1000_close',
                'idx_zz1000_pct',
                'idx_zz2000_close',
                'idx_zz2000_pct',
                'idx_winda_close',
                'idx_winda_pct',
                'turnover_total',
                'turnover_ma5',
                'turnover_ma20',
                'turnover_pct_vs_ma20',
                'turnover_pctile_1y',
                'up_count',
                'down_count',
                'flat_count',
                'up_down_ratio',
                'limit_up_count',
                'limit_down_count',
                'blast_count',
                'lian_count',
                'max_board_height',
                'high_60d_count',
                'low_60d_count',
                'market_breadth',
                'market_regime']
            col_str = ", ".join(columns)
            sql_main = f"SELECT {col_str} FROM ads_l1_market_overview WHERE trade_date = %s"
            rows = await db.execute(sql_main, (target_date,))
            if not rows:
                return None

            data = dict(zip(columns, rows[0]))

            # 2. 获取核心指数列表 (从 ODS 同步)
            sql_indices = """
                SELECT b.name, d.close, d.pct_chg
                FROM ods_index_daily d
                JOIN index_basic b ON d.ts_code = b.ts_code
                WHERE d.trade_date = %s AND b.is_core = 1
                ORDER BY b.display_order ASC
            """
            idx_rows = await db.execute(sql_indices, (target_date,))
            indices = []
            for ir in idx_rows:
                pct = float(ir[2]) if ir[2] is not None else 0
                indices.append({
                    "name": ir[0],
                    "close": f"{float(ir[1]):,.2f}" if ir[1] is not None else "-",
                    "pct": pct,
                    "pct_display": f"{pct * 100:+.2f}%"
                })

            # 3. 格式化数据 (增加空值处理)
            def safe_float(val, default=0.0):
                try:
                    return float(val) if val is not None else default
                except (ValueError, TypeError):
                    return default

            def safe_int(val, default=0):
                try:
                    return int(val) if val is not None else default
                except (ValueError, TypeError):
                    return default

            turnover_val = safe_float(data.get('turnover_total')) / 1e12
            ma5 = safe_float(data.get('turnover_ma5'))
            ma20 = safe_float(data.get('turnover_ma20'))

            regime_map = {
                "broad_up": {"label": "普涨行情", "desc": "市场广度极高，赚钱效应显著。"},
                "broad_down": {"label": "普跌行情", "desc": "市场情绪低迷，风险偏好收缩。"},
                "low_vol": {"label": "地量震荡", "desc": "成交额极低，处于变盘边缘。"},
                "structural": {"label": "结构分化", "desc": "涨跌互现，资金集中于局部主线。"},
                "normal": {"label": "常规震荡", "desc": "市场波动率正常，无极值表现。"}
            }
            regime_key = data.get('market_regime', 'normal')

            # 计算百分比变化
            vs_ma5 = "-"
            vs_ma5_color = "neutral"
            if ma5 > 0:
                diff = (turnover_val * 1e12 - ma5) / ma5
                vs_ma5 = f"{diff:+.1f}%"
                vs_ma5_color = "up" if diff > 0 else "down"

            vs_ma20 = "-"
            vs_ma20_color = "neutral"
            if ma20 > 0:
                diff = (turnover_val * 1e12 - ma20) / ma20
                vs_ma20 = f"{diff:+.1f}%"
                vs_ma20_color = "up" if diff > 0 else "down"

            return {
                "trade_date": str(data['trade_date']),
                "indices": indices,
                "turnover": {
                    "total": f"{turnover_val:.2f}",
                    "vs_ma5": vs_ma5,
                    "vs_ma5_color": vs_ma5_color,
                    "vs_ma20": vs_ma20,
                    "vs_ma20_color": vs_ma20_color,
                    "pctile": f"{safe_float(data.get('turnover_pctile_1y')) * 100:.1f}%"
                },
                "breadth": {
                    "up": safe_int(data.get('up_count')),
                    "down": safe_int(data.get('down_count')),
                    "flat": safe_int(data.get('flat_count')),
                    "limit_up": safe_int(data.get('limit_up_count')),
                    "limit_down": safe_int(data.get('limit_down_count')),
                    "blast": safe_int(data.get('blast_count')),
                    "ratio": f"{safe_float(data.get('up_down_ratio')):.2f}" if data.get('up_down_ratio') is not None else "-",
                    "ratio_color": "up" if safe_float(data.get('up_down_ratio')) > 1 else "down",
                    "max_board": safe_int(data.get('max_board_height')),
                    "high_60d": safe_int(data.get('high_60d_count')),
                    "low_60d": safe_int(data.get('low_60d_count'))
                },
                "regime": regime_map.get(regime_key, {"label": regime_key, "desc": ""})
            }
        except Exception as e:
            logger.error(f"获取 L1 Overview 失败: {e}")
            raise
