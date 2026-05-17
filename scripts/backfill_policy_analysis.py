# -*- coding: utf-8 -*-
"""
E14-S2 Phase 4: A 股政策 AI 追踪分析系统离线历史回填脚本
回填近一周内未被 AI 分析的政策数据，支持 ¥1.0 元防线硬预算熔断与速率限制。
"""

import sys
import os
import asyncio
import time
import datetime
import logging

# 将 scf-collector 添加到系统路径，以便导入 shared 模块
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scf-collector'))

# 加载 .env 环境变量
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scf-collector', '.env')
load_dotenv(env_path)

# 配置独立日志输出
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("backfill")

from shared.db.connection import execute_query, DBManager
from shared.utils.policy_analyzer import PolicyAnalyzer

async def main():
    logger.info("====== STARTING POLICY ANALYSIS BACKFILL SCRIPT ======")
    
    # 预算上限设定，支持通过环境变量重写，默认 ¥1.0 元硬防线限制
    BUDGET_LIMIT = float(os.getenv("BACKFILL_BUDGET_LIMIT", 1.0))
    logger.info(f"Budget Limit set to: {BUDGET_LIMIT:.2f} CNY")
    
    # 1. 捞取最近 7 天内未被 AI 分析的政策数据
    sql = """
    SELECT ods.*
    FROM ods_policy_info ods
    LEFT JOIN dwd_policy_analysis dwd 
      ON ods.id = dwd.policy_id 
    WHERE dwd.id IS NULL
      AND ods.publish_date >= DATE_SUB(CURRENT_DATE, INTERVAL 7 DAY)
      AND ods.is_deleted = 0
    ORDER BY ods.publish_date DESC;
    """
    
    try:
        pending_rows = await execute_query(sql, is_select=True)
    except Exception as e:
        logger.error(f"Failed to query pending policies for backfill: {e}")
        return
        
    total_pending = len(pending_rows)
    logger.info(f"Found {total_pending} pending policies from the last 7 days.")
    
    if total_pending == 0:
        logger.info("No policies require backfill. Exiting.")
        return
        
    analyzer = PolicyAnalyzer()
    accumulated_cost = 0.0
    processed_count = 0
    success_count = 0
    failed_count = 0
    
    # 2. 串行回填逻辑并包含预算限额检查
    for idx, row in enumerate(pending_rows):
        pid = row['id']
        title = row['title']
        publish_date = row.get('publish_date')
        
        # 预算硬核熔断防御
        if accumulated_cost >= BUDGET_LIMIT:
            logger.warning(
                f"[CRITICAL] 历史回填已达预设 {BUDGET_LIMIT:.2f} CNY 预算防线，脚本主动安全挂起。"
                f"当前累计费用: {accumulated_cost:.6f} CNY"
            )
            break
            
        logger.info(f"[{idx+1}/{total_pending}] Processing Policy ID {pid} | Publish Date: {publish_date} | Title: '{title}'")
        
        try:
            res = await analyzer.analyze_policy(row)
            cost = float(res.get("cost_cny", 0.0))
            accumulated_cost += cost
            processed_count += 1
            success_count += 1
            logger.info(f"Successfully processed ID {pid}. Cost: {cost:.6f} CNY | Accumulated Cost: {accumulated_cost:.6f} CNY")
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to analyze Policy ID {pid}: {e}")
            # 回填出错时，将该记录更新为 failed 状态防止卡死
            try:
                await execute_query(
                    "UPDATE ods_policy_info SET analysis_status = 'failed' WHERE id = %s",
                    (pid,),
                    is_select=False
                )
            except Exception as update_err:
                logger.error(f"Failed to update failed status for ID {pid}: {update_err}")
                
        # 防火墙时延，规避大模型高频 429 报错
        await asyncio.sleep(1.0)
        
    logger.info("====== BACKFILL PROCESS SUMMARY ======")
    logger.info(f"Total Pending: {total_pending}")
    logger.info(f"Processed: {processed_count}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {failed_count}")
    logger.info(f"Total Cost: {accumulated_cost:.6f} CNY")
    logger.info("======================================")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Backfill script interrupted by user.")
    finally:
        # 安全断开数据库连接池
        asyncio.run(DBManager.close_pool())
