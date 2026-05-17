# -*- coding: utf-8 -*-
"""
[E14-S2-P3-T1] SCF 云函数政策采集模块 policy_collector/index.py
专门负责政策高频并发去重采集。
"""

import sys
import os

# 0. 强制重定向环境路径 (解决 SCF 只读文件系统报错)
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

# 强制从当前目录/项目根目录加载 .env (优先于本地环境变量)
from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, '.env'), override=True)
load_dotenv(os.path.join(current_dir, '.env'), override=True)

# 初始化日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 引入模块
from shared.collectors.policy.gov_collector import GovCollector
from shared.collectors.policy.csrc_collector import CsrcCollector
from shared.db.dao import StockDAO
from shared.db.connection import DBManager

async def async_handler(event, context):
    request_id = getattr(context, 'request_id', f"coll_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
    biz_date = datetime.date.today().strftime('%Y-%m-%d')
    logger.info(f"[{request_id}] Starting decoupled Policy Collector task...")
    
    gov_collector = GovCollector()
    csrc_collector = CsrcCollector()
    
    gov_new = 0
    csrc_new = 0
    
    try:
        # 1. 记录运行状态为 RUNNING
        await StockDAO.log_pipeline_run_v2(
            pipeline_id="policy_collector",
            status="RUNNING",
            run_id=request_id,
            biz_date=biz_date,
            output_summary={"started": True}
        )
        
        # 2. 运行中国政府网采集（含央行与高阶政策识别）
        gov_new = await gov_collector.run()
        logger.info(f"[{request_id}] GovCollector completed. New: {gov_new}")
        
        # 3. 运行证监会官网高频通告采集
        csrc_new = await csrc_collector.run()
        logger.info(f"[{request_id}] CsrcCollector completed. New: {csrc_new}")
        
        total_new = gov_new + csrc_new
        summary = {
            "gov_new": gov_new,
            "csrc_new": csrc_new,
            "total_new": total_new,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # 4. 落地 SUCCESS 结构化流水成果数据
        await StockDAO.log_pipeline_run_v2(
            pipeline_id="policy_collector",
            status="SUCCESS",
            run_id=request_id,
            biz_date=biz_date,
            output_summary=summary
        )
        
        return {
            "status": "success",
            "new_policies_count": total_new,
            "summary": summary,
            "request_id": request_id
        }
        
    except Exception as e:
        err_msg = f"Policy Collector failed: {str(e)}"
        logger.error(f"[{request_id}] {err_msg}")
        
        # 记录 FAILED 状态流水
        try:
            await StockDAO.log_pipeline_run_v2(
                pipeline_id="policy_collector",
                status="FAILED",
                error_message=err_msg,
                run_id=request_id,
                biz_date=biz_date,
                output_summary={"error": err_msg}
            )
        except Exception as log_err:
            logger.error(f"Failed to write failed log: {log_err}")
            
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
        request_id = "local_manual_collector"
    print(asyncio.run(async_handler({}, FakeContext())))
