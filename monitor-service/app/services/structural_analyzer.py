import json
import logging
from typing import Dict, Any, List
from app.utils.database import db

logger = logging.getLogger("monitor-service.structural")

class StructuralAnalyzer:
    """第 2 章：结构分化与旋转分析器 (ADS 层计算)"""

    async def run_daily_analysis(self, target_date: str):
        """执行每日结构化分析"""
        logger.info(f"开始计算 {target_date} 的结构分化指标...")
        
        await self.analyze_industry_rotation(target_date)
        await self.analyze_concept_rotation(target_date)
        await self.analyze_style_rotation(target_date)
        
        # 保存全景快照供前端一键调用
        await self.save_structural_snapshot(target_date)
        
        logger.info(f"{target_date} 结构分化指标计算完成")

    async def analyze_industry_rotation(self, target_date: str):
        """分析申万行业旋转 (5日排名变化 + 领涨股)"""
        # SQL 逻辑参考 E2_indicators.md
        query = """
        INSERT INTO ads_l2_industry_rotation (trade_date, ts_code, name, pct_chg, rank_current, rank_5d_change, leader_stock, pe_percentile)
        WITH daily_rank AS (
            SELECT 
                trade_date, ts_code, name, pct_chg, pe_ttm,
                RANK() OVER(PARTITION BY trade_date ORDER BY pct_chg DESC) as rnk
            FROM ods_sw_index_daily
            WHERE level = 'l1'
        )
        SELECT 
            t1.trade_date, t1.ts_code, t1.name, t1.pct_chg, 
            t1.rnk as rank_current,
            CAST(t2.rnk AS SIGNED) - CAST(t1.rnk AS SIGNED) as rank_5d_change,
            'N/A' as leader_stock, -- 领涨股需额外逻辑或简化处理
            0.0 as pe_percentile -- 估值分位需历史对比
        FROM daily_rank t1
        LEFT JOIN daily_rank t2 ON t1.ts_code = t2.ts_code 
            AND t2.trade_date = (SELECT MAX(trade_date) FROM ods_sw_index_daily WHERE trade_date < t1.trade_date ORDER BY trade_date DESC LIMIT 4,1)
        WHERE t1.trade_date = %s
        ON DUPLICATE KEY UPDATE 
            pct_chg=VALUES(pct_chg), 
            rank_current=VALUES(rank_current), 
            rank_5d_change=VALUES(rank_5d_change)
        """
        # 注意: MySQL 5.7 不支持 OVER()，需要改写为传统 SQL
        # 考虑到性能和 128MB 限制，我将使用 Python 处理排名逻辑
        
        try:
            # 1. 获取今日数据
            rows_today = await db.execute("SELECT ts_code, name, pct_chg, pe_ttm FROM ods_sw_index_daily WHERE trade_date = %s AND level = 'l1' ORDER BY pct_chg DESC", (target_date,))
            if not rows_today: return
            
            # 2. 获取 5 日前日期
            row_5d = await db.execute("SELECT DISTINCT trade_date FROM ods_sw_index_daily WHERE trade_date < %s ORDER BY trade_date DESC LIMIT 4,1", (target_date,))
            date_5d = row_5d[0][0] if row_5d else None
            
            # 3. 获取 5 日前排名
            rank_5d_map = {}
            if date_5d:
                rows_5d = await db.execute("SELECT ts_code, pct_chg FROM ods_sw_index_daily WHERE trade_date = %s AND level = 'l1' ORDER BY pct_chg DESC", (date_5d,))
                for i, r in enumerate(rows_5d):
                    rank_5d_map[r[0]] = i + 1
            
            # 4. 计算并保存
            insert_data = []
            for i, r in enumerate(rows_today):
                ts_code, name, pct_chg, pe = r
                rank_curr = i + 1
                rank_5d = rank_5d_map.get(ts_code, rank_curr)
                rank_chg = rank_5d - rank_curr
                
                # 简化领涨股: 此处暂设为 N/A，后续可通过 akshare 实时补全
                insert_data.append((target_date, ts_code, name, pct_chg, rank_curr, rank_chg, 'N/A', 0.0))
            
            sql = """
            INSERT INTO ads_l2_industry_rotation (trade_date, ts_code, name, pct_chg, rank_current, rank_5d_change, leader_stock, pe_percentile)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                pct_chg=VALUES(pct_chg), rank_current=VALUES(rank_current), rank_5d_change=VALUES(rank_5d_change)
            """
            await db.execute_many(sql, insert_data)
        except Exception as e:
            logger.error(f"分析行业旋转失败: {e}")

    async def analyze_concept_rotation(self, target_date: str):
        """分析概念板块旋转"""
        try:
            # 逻辑同行业，针对 ods_concept_kline_daily
            rows_today = await db.execute("SELECT concept_code, concept_name, pct_chg FROM ods_concept_kline_daily WHERE trade_date = %s ORDER BY pct_chg DESC", (target_date,))
            if not rows_today: return
            
            row_5d = await db.execute("SELECT DISTINCT trade_date FROM ods_concept_kline_daily WHERE trade_date < %s ORDER BY trade_date DESC LIMIT 4,1", (target_date,))
            date_5d = row_5d[0][0] if row_5d else None
            
            rank_5d_map = {}
            if date_5d:
                rows_5d = await db.execute("SELECT concept_code FROM ods_concept_kline_daily WHERE trade_date = %s ORDER BY pct_chg DESC", (date_5d,))
                for i, r in enumerate(rows_5d):
                    rank_5d_map[r[0]] = i + 1
            
            insert_data = []
            for i, r in enumerate(rows_today):
                code, name, pct_chg = r
                rank_curr = i + 1
                rank_5d = rank_5d_map.get(code, rank_curr)
                insert_data.append((target_date, code, name, pct_chg, rank_curr, rank_5d - rank_curr))
            
            sql = """
            INSERT INTO ads_l2_concept_rotation (trade_date, ts_code, name, pct_chg, rank_current, rank_5d_change)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                pct_chg=VALUES(pct_chg), rank_current=VALUES(rank_current), rank_5d_change=VALUES(rank_5d_change)
            """
            await db.execute_many(sql, insert_data)
        except Exception as e:
            logger.error(f"分析概念旋转失败: {e}")

    async def analyze_style_rotation(self, target_date: str):
        """分析风格旋转 (Value vs Growth, Big vs Small)"""
        try:
            # 这里的 ts_code 对应 dim_style_factor 中的定义
            # 399370 国证价值, 399371 国证成长
            # 399311 国证1000, 399300 沪深300
            
            # 简化逻辑: 获取涨跌幅并存储
            # 注意: 风格指数数据目前在 ods_sw_index_daily (level='style') 中
            rows = await db.execute("SELECT ts_code, name, pct_chg FROM ods_sw_index_daily WHERE trade_date = %s AND level = 'style'", (target_date,))
            if not rows: return
            
            insert_data = []
            for r in rows:
                insert_data.append((target_date, r[0], r[1], r[2]))
            
            sql = """
            INSERT INTO ads_l2_style_rotation (trade_date, ts_code, name, pct_chg)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE pct_chg=VALUES(pct_chg)
            """
            await db.execute_many(sql, insert_data)
        except Exception as e:
            logger.error(f"分析风格旋转失败: {e}")

    async def save_structural_snapshot(self, target_date: str):
        """将结构化分析结果打包成 JSON 快照存入 ADS 层"""
        try:
            # 1. 获取行业 Top/Bottom
            industries_top = await db.execute(
                "SELECT name, pct_chg, rank_current, rank_5d_change, leader_stock, pe_percentile FROM ads_l2_industry_rotation WHERE trade_date = %s ORDER BY pct_chg DESC LIMIT 5",
                (target_date,)
            )
            industries_bottom = await db.execute(
                "SELECT name, pct_chg, rank_current, rank_5d_change, leader_stock, pe_percentile FROM ads_l2_industry_rotation WHERE trade_date = %s ORDER BY pct_chg ASC LIMIT 5",
                (target_date,)
            )
            
            # 2. 概念 Top
            concepts_top = await db.execute(
                "SELECT name, pct_chg, rank_current, rank_5d_change FROM ads_l2_concept_rotation WHERE trade_date = %s ORDER BY pct_chg DESC LIMIT 10",
                (target_date,)
            )
            
            # 3. 风格
            styles = await db.execute(
                "SELECT name, pct_chg FROM ads_l2_style_rotation WHERE trade_date = %s",
                (target_date,)
            )
            
            # 4. 组装 Payload
            payload = {
                "trade_date": target_date,
                "industry": {
                    "top": [{"name": r[0], "pct": float(r[1]) if r[1] is not None else 0.0, "rank": r[2], "rank_chg": r[3], "leader": r[4], "pe_pctile": float(r[5]) if r[5] is not None else 0.0} for r in industries_top],
                    "bottom": [{"name": r[0], "pct": float(r[1]) if r[1] is not None else 0.0, "rank": r[2], "rank_chg": r[3], "leader": r[4], "pe_pctile": float(r[5]) if r[5] is not None else 0.0} for r in industries_bottom]
                },
                "concept": {
                    "top": [{"name": r[0], "pct": float(r[1]) if r[1] is not None else 0.0, "rank": r[2], "rank_chg": r[3]} for r in concepts_top]
                },
                "style": [{"name": r[0], "pct": float(r[1]) if r[1] is not None else 0.0} for r in styles]
            }
            
            # 5. 自动生成摘要文案
            summary = self._generate_auto_summary(payload)
            
            # 6. 存入数据库
            sql = """
            INSERT INTO ads_l2_structural_snapshot (trade_date, snapshot_payload, summary_text)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE snapshot_payload=VALUES(snapshot_payload), summary_text=VALUES(summary_text)
            """
            await db.execute(sql, (target_date, json.dumps(payload, ensure_ascii=False), summary))
            logger.info(f"结构化分析全景快照保存成功: {target_date}")
            
        except Exception as e:
            logger.error(f"保存全景快照失败: {e}", exc_info=True)

    def _generate_auto_summary(self, payload: Dict[str, Any]) -> str:
        """根据数据自动生成结构化复盘摘要"""
        try:
            top_ind = payload["industry"]["top"][0]["name"] if payload["industry"]["top"] else "无"
            top_concept = payload["concept"]["top"][0]["name"] if payload["concept"]["top"] else "无"
            return f"今日行业层面 {top_ind} 表现最强；概念层面 {top_concept} 活跃度最高。结构分化持续，建议关注主线动能。"
        except:
            return "结构分化分析已生成。"

structural_analyzer = StructuralAnalyzer()
