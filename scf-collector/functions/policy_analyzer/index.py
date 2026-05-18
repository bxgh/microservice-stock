# -*- coding: utf-8 -*-
"""
[E14-S2-P3-T1 & T2] SCF 云函数政策分析模块 policy_analyzer/index.py
包含并发乐观锁、LIMIT 5 串行批队列与单条异常状态隔离。
"""

import sys
import os

# 0. 强制重定向环境路径
os.environ['HOME'] = '/tmp'

import logging
import asyncio
import datetime
from typing import Dict, Any

# 1. 强力路径搜索（确保 Layer 挂载被识别）
for path in ['/opt', '/opt/python', '/opt/python/lib/python3.10/site-packages']:
    if os.path.exists(path) and path not in sys.path:
        sys.path.insert(0, path)

# 2. 本地相对路径搜索
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(parent_dir)
for path in [current_dir, parent_dir, project_root]:
    if path not in sys.path:
        sys.path.insert(0, path)

# 强制从当前目录/项目根目录加载 .env
from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, '.env'), override=True)
load_dotenv(os.path.join(current_dir, '.env'), override=True)

# 初始化日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 引入模块
from shared.db.connection import execute_query, DBManager
from shared.db.dao import StockDAO
from shared.utils.staged_analyzer import StagedAnalyzer

async def async_handler(event, context):
    request_id = getattr(context, 'request_id', f"analy_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
    biz_date = datetime.date.today().strftime('%Y-%m-%d')
    logger.info(f"[{request_id}] Starting decoupled Policy Analyzer task...")
    
    try:
        # 1. 并发防重入乐观锁校验 (MySQL Distributed Lock)
        # 查找是否有 10 分钟内处于 RUNNING 状态的 analyzer 任务
        sql_check = """
        SELECT COUNT(*) as active_count FROM meta_pipeline_run 
        WHERE pipeline_id = 'policy_analyzer' 
          AND status = 'RUNNING' 
          AND updated_at > NOW() - INTERVAL 10 MINUTE
        """
        rows = await execute_query(sql_check, is_select=True)
        if rows and rows[0]['active_count'] > 0:
            logger.warning(f"[{request_id}] Another policy_analyzer instance is running. Exiting to prevent collision.")
            return {
                "status": "skipped",
                "message": "Another instance is active.",
                "request_id": request_id
            }
            
        # 2. 抢占锁：记录运行状态为 RUNNING
        await StockDAO.log_pipeline_run_v2(
            pipeline_id="policy_analyzer",
            status="RUNNING",
            run_id=request_id,
            biz_date=biz_date,
            output_summary={"started": True}
        )
        
        # 3. 批拉取最多 5 条待处理政策进行串行解析
        sql_fetch = """
        SELECT * FROM ods_policy_info 
        WHERE analysis_status = 'pending_analysis' 
          AND is_deleted = 0 
        ORDER BY publish_date DESC, id DESC 
        LIMIT 5
        """
        pending_policies = await execute_query(sql_fetch, is_select=True)
        logger.info(f"[{request_id}] Mapped {len(pending_policies)} pending policies in queue.")
        
        if not pending_policies:
            # 队列无任务，顺利完成
            await StockDAO.log_pipeline_run_v2(
                pipeline_id="policy_analyzer",
                status="SUCCESS",
                run_id=request_id,
                biz_date=biz_date,
                output_summary={"processed_count": 0, "msg": "Queue empty."}
            )
            return {
                "status": "success",
                "processed_count": 0,
                "request_id": request_id
            }
            
        analyzer = StagedAnalyzer()
        success_ids = []
        failed_ids = []
        total_cost = 0.0
        
        # 串行分析，保障 SCF 耗时安全及大模型流控
        for row in pending_policies:
            pid = row['id']
            title = row['title']
            logger.info(f"[{request_id}] Processing Policy ID {pid}: '{title}'...")
            try:
                # 执行 AI 措辞比对/摘要主引擎
                result = await analyzer.analyze_policy(row)
                success_ids.append(pid)
                total_cost += float(result.get("cost_cny", 0.0))
                logger.info(f"[{request_id}] Successfully analyzed ID {pid}. Cost: ¥{result.get('cost_cny', 0.0):.6f}")
            except Exception as single_err:
                logger.error(f"[{request_id}] Failed to analyze ID {pid}: {single_err}")
                failed_ids.append(pid)
                # 隔离失败记录：将该项状态设为 failed，防止它卡在 pending 队列导致死循环堆积
                await execute_query(
                    "UPDATE ods_policy_info SET analysis_status = 'failed' WHERE id = %s",
                    (pid,), is_select=False
                )
                
        summary = {
            "processed_count": len(pending_policies),
            "success_count": len(success_ids),
            "failed_count": len(failed_ids),
            "success_ids": success_ids,
            "failed_ids": failed_ids,
            "total_cost_cny": total_cost,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # 4. 释放锁并记录 SUCCESS 状态
        await StockDAO.log_pipeline_run_v2(
            pipeline_id="policy_analyzer",
            status="SUCCESS",
            run_id=request_id,
            biz_date=biz_date,
            output_summary=summary
        )
        
        return {
            "status": "success",
            "summary": summary,
            "request_id": request_id
        }
        
    except Exception as e:
        err_msg = f"Policy Analyzer task collapsed: {str(e)}"
        logger.error(f"[{request_id}] {err_msg}")
        
        # 释放锁并标记 FAILED 状态
        try:
            await StockDAO.log_pipeline_run_v2(
                pipeline_id="policy_analyzer",
                status="FAILED",
                error_message=err_msg,
                run_id=request_id,
                biz_date=biz_date,
                output_summary={"error": err_msg}
            )
        except Exception as log_err:
            logger.error(f"Failed to write analyzer failed log: {log_err}")
            
        return {
            "status": "error",
            "message": err_msg,
            "request_id": request_id
        }
    finally:
        await DBManager.close_pool()

def main_handler(event, context):
    return asyncio.run(async_handler(event, context))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    class FakeContext:
        request_id = "local_manual_analyzer"
    print(asyncio.run(async_handler({}, FakeContext())))
