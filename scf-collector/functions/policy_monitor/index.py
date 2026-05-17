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
# 向上两级以确保能加载 shared
project_root = os.path.dirname(parent_dir)
for path in [current_dir, parent_dir, project_root]:
    if path not in sys.path:
        sys.path.insert(0, path)

# 强制从当前目录加载 .env (优先于本地环境变量)
from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, '.env'), override=True)
load_dotenv(os.path.join(current_dir, '.env'), override=True)

# 初始化日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 引入自定义模块
from shared.collectors.policy.gov_collector import GovCollector
from shared.collectors.policy.csrc_collector import CsrcCollector
from shared.utils.notifier import WeChatNotifier, EmailNotifier
from shared.db.connection import DBManager

async def async_handler(event, context):
    request_id = getattr(context, 'request_id', 'local_test')
    logger.info(f"[{request_id}] Starting AI Policy Monitor task...")
    
    gov_collector = GovCollector()
    csrc_collector = CsrcCollector()
    gov_new = 0
    csrc_new = 0
    
    try:
        # 1. 运行中国政府网采集（含央行与高阶政策识别）
        gov_new = await gov_collector.run()
        logger.info(f"[{request_id}] GovCollector executed successfully. New policies: {gov_new}")
        
        # 2. 运行证监会官网高频通告采集
        csrc_new = await csrc_collector.run()
        logger.info(f"[{request_id}] CsrcCollector executed successfully. New policies: {csrc_new}")
        
        new_count = gov_new + csrc_new
        
        if new_count > 0:
            # 1. 发送微信通知
            wechat_title = f"📢 发现 {new_count} 条新政策！"
            wechat_content = (
                f"政策跟踪系统于 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 抓取到新政策：\n"
                f"- 中国政府网 (含央行/高阶政策): {gov_new} 条\n"
                f"- 中国证监会: {csrc_new} 条\n"
                f"已全部去重入库，准备进行 AI 深度分析。"
            )
            await WeChatNotifier.send_msg(wechat_title, wechat_content)
            
            # 2. 发送邮件通知
            email_title = f"📢 政策跟踪预警: 发现 {new_count} 条最新政策"
            context_data = {
                "任务名称": "宏观及监管政策多源联合采集",
                "采集时间": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "中国政府网新增": f"{gov_new} 条",
                "中国证监会新增": f"{csrc_new} 条",
                "汇总新增政策数": f"{new_count} 条",
                "状态": "SUCCESS"
            }
            await EmailNotifier.send_report("SUCCESS", email_title, context_data)

            
        return {
            "status": "success",
            "new_policies_count": new_count,
            "request_id": request_id
        }
        
    except Exception as e:
        err_msg = f"Policy Monitor task failed: {str(e)}"
        logger.error(f"[{request_id}] {err_msg}")
        
        # 异常告警
        try:
            await WeChatNotifier.send_msg("❌ 政策监控任务异常", err_msg)
            await EmailNotifier.notify_failure("政策监控任务", datetime.datetime.now().strftime('%Y-%m-%d'), err_msg)
        except Exception as notify_err:
            logger.error(f"Failed to send failure notification: {notify_err}")
            
        return {
            "status": "error",
            "message": err_msg,
            "request_id": request_id
        }
    finally:
        # 显式关闭连接池，防止连接泄漏
        await DBManager.close_pool()

def main_handler(event, context):
    return asyncio.run(async_handler(event, context))

if __name__ == "__main__":
    # 本地直接执行测试
    logging.basicConfig(level=logging.INFO)
    class FakeContext:
        request_id = "local_manual_test"
    print(asyncio.run(async_handler({}, FakeContext())))
