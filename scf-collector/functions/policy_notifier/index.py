# -*- coding: utf-8 -*-
"""
[E14-S2-P3-T3 & T4] SCF 云函数政策分发预警模块 policy_notifier/index.py
负责重要政策研报（WeChat/HTML Email）的渲染与分发，并标记已发去重。
"""

import sys
import os

# 0. 强制重定向环境路径
os.environ['HOME'] = '/tmp'

import logging
import asyncio
import datetime
import json
from typing import Dict, Any, List

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
from shared.utils.notifier import WeChatNotifier, EmailNotifier

def _format_summary_html(summary_raw: str) -> str:
    """
    格式化三句话摘要为 HTML 序号列表
    """
    try:
        sentences = json.loads(summary_raw)
    except Exception:
        # 如果不是标准 JSON 数组，直接以分号分割格式化
        sentences = [s.strip() for s in summary_raw.split("。") if s.strip()]
        
    html = "<ol style='margin: 0; padding-left: 20px; font-size: 14px; color: #444;'>"
    for s in sentences:
        if s:
            html += f"<li style='margin-bottom: 6px;'>{s}。</li>"
    html += "</ol>"
    return html

def _format_sectors_html(sectors_pos_raw: str) -> str:
    """
    渲染受益板块及标为现代 Fintech Badge 样式
    """
    try:
        sectors = json.loads(sectors_pos_raw)
    except Exception:
        sectors = []
        
    if not sectors:
        return "<span style='color: #888; font-style: italic;'>暂无显著受益申万二级板块</span>"
        
    html = "<div style='display: flex; flex-wrap: wrap; gap: 8px;'>"
    for s in sectors:
        stocks_str = f" <span style='color:#d9534f;font-weight:bold;margin-left:4px;'>(龙头: {s.get('representative_stocks')})</span>" if s.get('representative_stocks') else ""
        html += f"""
        <div style='background-color: #fff3f3; border: 1px solid #ffcccc; color: #c9302c; padding: 6px 10px; border-radius: 4px; font-size: 13px; font-weight: 500;'>
            <strong>{s.get('sector_name', 'N/A')} ({s.get('sector_code_sw', 'N/A')})</strong>{stocks_str}
        </div>
        """
    html += "</div>"
    return html

def _format_diff_table_html(diff_raw: str) -> str:
    """
    绘制上期/本期对比措辞删除线 side-by-side 表格
    """
    try:
        diffs = json.loads(diff_raw)
    except Exception:
        diffs = []
        
    if not diffs:
        return ""
        
    html = """
    <div style='margin-top: 10px; border: 1px solid #dee2e6; border-radius: 6px; overflow: hidden;'>
        <table style='width: 100%; border-collapse: collapse; font-size: 13px; text-align: left;'>
            <tr style='background-color: #f8f9fa; border-bottom: 2px solid #dee2e6;'>
                <th style='padding: 8px; font-weight: bold; color: #495057; width: 80px;'>对比主题</th>
                <th style='padding: 8px; font-weight: bold; color: #495057;'>措辞变化 (上期 vs 本期)</th>
                <th style='padding: 8px; font-weight: bold; color: #495057; width: 120px;'>隐含市场影响</th>
            </tr>
    """
    for d in diffs:
        html += f"""
        <tr style='border-bottom: 1px solid #dee2e6;'>
            <td style='padding: 8px; font-weight: bold; color: #212529; background-color: #fcfcfc;'>{d.get('topic', 'N/A')}</td>
            <td style='padding: 8px;'>
                <div style='color: #888; text-decoration: line-through; margin-bottom: 4px;'>上期: {d.get('previous', '无')}</div>
                <div style='color: #d9534f; font-weight: bold;'>本期: {d.get('current', '无')}</div>
            </td>
            <td style='padding: 8px; color: #495057;'>{d.get('implication', 'N/A')}</td>
        </tr>
        """
    html += "</table></div>"
    return html

async def async_handler(event, context):
    request_id = getattr(context, 'request_id', f"note_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
    biz_date = datetime.date.today().strftime('%Y-%m-%d')
    logger.info(f"[{request_id}] Starting decoupled Policy Notifier task...")
    
    try:
        # 1. 记录运行状态为 RUNNING
        await StockDAO.log_pipeline_run_v2(
            pipeline_id="policy_notifier",
            status="RUNNING",
            run_id=request_id,
            biz_date=biz_date,
            output_summary={"started": True}
        )
        
        # 2. 捞取所有已完成 AI 分析但尚未通知的明细记录 (pending 状态)
        sql_find = """
        SELECT a.*, p.title, p.publish_date, p.ts_code, p.policy_type
        FROM dwd_policy_analysis a
        JOIN ods_policy_info p ON a.policy_id = p.id
        WHERE a.analysis_status = 'pending'
          AND a.is_deleted = 0
        ORDER BY a.id ASC
        """
        pending_notifies = await execute_query(sql_find, is_select=True)
        logger.info(f"[{request_id}] Found {len(pending_notifies)} pending records for notification.")
        
        if not pending_notifies:
            # 队列无通知任务，顺利完成
            await StockDAO.log_pipeline_run_v2(
                pipeline_id="policy_notifier",
                status="SUCCESS",
                run_id=request_id,
                biz_date=biz_date,
                output_summary={"processed_count": 0, "msg": "No pending notifications."}
            )
            return {
                "status": "success",
                "notified_count": 0,
                "request_id": request_id
            }
            
        success_ids = []
        skipped_ids = []
        
        for row in pending_notifies:
            analysis_id = row['id']
            policy_id = row['policy_id']
            title = row['title']
            importance_level = row['importance_level']
            intensity_change = row['intensity_change']
            ts_code = row['ts_code']
            
            # 3. 门警规则过滤：我们仅对重要性评级 >= 3，或者是人行 (PBC) 发布的高优先级宏观政策进行推送
            # 低评级且非核心发布方的记录，直接在后台标为 notified 跳过，避免日常频繁轰炸
            if importance_level < 3 and ts_code != "PBC":
                logger.info(f"[{request_id}] Skipping low importance notify for ID {analysis_id} (Level: {importance_level})")
                await execute_query(
                    "UPDATE dwd_policy_analysis SET analysis_status = 'notified' WHERE id = %s",
                    (analysis_id,), is_select=False
                )
                skipped_ids.append(analysis_id)
                continue
                
            logger.info(f"[{request_id}] Sending alerts for high priority policy ID {analysis_id}...")
            
            # 4. 组装微信简报数据
            # 解析摘要用于微信展示
            try:
                sentences = json.loads(row['summary'])
                wechat_summary_text = "\n".join([f"{i+1}. {s}。" for i, s in enumerate(sentences)])
            except Exception:
                wechat_summary_text = row['summary']
                
            wechat_title = f"📢 政策智能研报: {title}"
            wechat_content = (
                f"**发布单位**: {ts_code} | **发布日期**: {row['publish_date']}\n"
                f"**重要性评级**: {'⭐' * importance_level} ({importance_level} 级)\n"
                f"**政策强度变动**: {intensity_change}\n\n"
                f"💡 **AI 三句话核心研报**:\n{wechat_summary_text}\n\n"
                f"📊 **市场隐含指引说明**: {row['implication']}"
            )
            
            # 5. 组装响应式 HTML 邮件数据
            # 核心变色判断
            intensity_color = "#6c757d"
            intensity_label = "持平 ⚪"
            if any(w in intensity_change for w in ["增强", "strengthened", "stronger"]):
                intensity_color = "#dc3545"
                intensity_label = "增强 🔴"
            elif any(w in intensity_change for w in ["减弱", "weakened", "weaker"]):
                intensity_color = "#28a745"
                intensity_label = "减弱 🟢"
                
            intensity_html = f"<span style='color: {intensity_color}; font-weight: bold;'>{intensity_label} ({intensity_change})</span>"
            importance_html = f"<span style='color: #ffc107; font-weight: bold;'>{'★' * importance_level}{'☆' * (5 - importance_level)} ({importance_level} 级)</span>"
            
            summary_html = _format_summary_html(row['summary'])
            sectors_html = _format_sectors_html(row['sectors_positive'])
            diff_table_html = _format_diff_table_html(row['key_differences'])
            
            email_context = {
                "政策标题": title,
                "发布日期": str(row['publish_date']),
                "发布单位": ts_code,
                "政策强度变化": intensity_html,
                "重要性评级": importance_html,
                "评级原因": row['importance_reason'] or "无特定说明。",
                "三句话研报摘要": summary_html,
                "受益板块与龙头": sectors_html,
                "市场隐含指引说明": row['implication'] or "暂无隐含指引。"
            }
            
            # 如果存在措辞比对记录，动态加入侧边比对表
            if diff_table_html:
                email_context["核心措辞比对详情"] = diff_table_html
                
            email_level = "SUCCESS"
            if importance_level >= 4:
                email_level = "WARN" # 高亮红色预警主题色
                
            email_title = f"📢 政策追踪预警: {title} ({importance_level}级研报)"
            
            # 6. 分级分发通知 (Differentiated Notification Triggers)
            # Email: 宽口径 (Level >= 3 或 PBC 政策) 投研异步深读，保留全面信息流
            # WeChat: 窄口径 (Level >= 4 重要政策，或 Level >= 3 PBC 央行宏观变动) 手机同步强预警，坚决杜绝日常消息轰炸
            should_send_wechat = (importance_level >= 4) or (ts_code == "PBC" and importance_level >= 3)
            
            if should_send_wechat:
                await WeChatNotifier.send_msg(wechat_title, wechat_content)
                logger.info(f"[{request_id}] WeChat notification sent for ID {analysis_id}.")
            else:
                logger.info(f"[{request_id}] WeChat notification bypassed for ID {analysis_id} (Level {importance_level}, non-PBC) to prevent mobile alert fatigue.")
                
            await EmailNotifier.send_report(email_level, email_title, email_context)
            
            # 7. 标记状态为已发送 (notified)
            await execute_query(
                "UPDATE dwd_policy_analysis SET analysis_status = 'notified' WHERE id = %s",
                (analysis_id,), is_select=False
            )
            success_ids.append(analysis_id)
            
        summary = {
            "processed_count": len(pending_notifies),
            "notified_count": len(success_ids),
            "skipped_count": len(skipped_ids),
            "notified_ids": success_ids,
            "skipped_ids": skipped_ids,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # 8. 记录 SUCCESS 状态流水
        await StockDAO.log_pipeline_run_v2(
            pipeline_id="policy_notifier",
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
        err_msg = f"Policy Notifier failed: {str(e)}"
        logger.error(f"[{request_id}] {err_msg}")
        
        # 记录 FAILED 状态流水
        try:
            await StockDAO.log_pipeline_run_v2(
                pipeline_id="policy_notifier",
                status="FAILED",
                error_message=err_msg,
                run_id=request_id,
                biz_date=biz_date,
                output_summary={"error": err_msg}
            )
        except Exception as log_err:
            logger.error(f"Failed to write notifier failed log: {log_err}")
            
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
        request_id = "local_manual_notifier"
    print(asyncio.run(async_handler({}, FakeContext())))
