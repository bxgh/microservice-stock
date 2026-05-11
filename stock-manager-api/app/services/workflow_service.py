import logging
import datetime
from datetime import date
from typing import List, Dict, Any, Optional
from app.services.pipeline_service import pipeline_service
from app.services.task_command_service import TaskCommandService
from app.utils.logger import get_logger

logger = get_logger("stock-manager.workflow")

class WorkflowService:
    """云端三阶段流水线管理器"""
    
    # 流水线 ID
    PIPELINE_POST_MARKET = "post_market_cloud"
    PIPELINE_MORNING = "morning_prep"
    PIPELINE_MAINTENANCE = "night_maintenance"
    
    # 阶段定义 - Post Market
    STAGE_A = "STAGE_A_COLLECTION"  # 基础采集 (K线/指数/停复牌)
    STAGE_B = "STAGE_B_SYNTHESIS"   # 核心综述 (L1/L2 因子计算)
    STAGE_C = "STAGE_C_QA_AUDIT"    # 质量审计
    STAGE_D = "STAGE_D_HANDOVER"    # 跨网接力

    # 阶段定义 - Morning
    STAGE_M1 = "STAGE_M1_BASIC_SYNC"      # 基础信息同步
    STAGE_M2 = "STAGE_M2_PRE_MARKET_SYNC" # 早盘信息 (停牌/业绩预告)
    STAGE_M3 = "STAGE_M3_DQ_REPORT"       # 数据质量报告 (T-1)

    # 阶段定义 - Maintenance
    STAGE_N1 = "STAGE_N1_FINANCE_SYNC"    # 财务数据同步
    STAGE_N2 = "STAGE_N2_INFORMATION_SYNC"# 机构/评级同步
    STAGE_N3 = "STAGE_N3_SHAREHOLDER_SYNC"# 股东数据同步

    def __init__(self):
        self.command_service = TaskCommandService()

    async def process_morning_trigger(self, biz_date: datetime.date):
        """处理晨间就绪信号 (08:00 - 09:30)"""
        biz_date_str = biz_date.isoformat()
        logger.info(f"【Workflow】触发晨间预就绪流水线: {biz_date_str}")
        
        # 1. M1: 基础信息同步 (P0)
        if not await pipeline_service.is_stage_success(self.PIPELINE_MORNING, biz_date_str, self.STAGE_M1):
            await self.execute_stage(self.STAGE_M1, biz_date, self.PIPELINE_MORNING)
            
        # 2. M2: 早盘信息 (停牌/业绩预告)
        if await pipeline_service.is_stage_success(self.PIPELINE_MORNING, biz_date_str, self.STAGE_M1):
            if not await pipeline_service.is_stage_success(self.PIPELINE_MORNING, biz_date_str, self.STAGE_M2):
                await self.execute_stage(self.STAGE_M2, biz_date, self.PIPELINE_MORNING)
                
        # 3. M3: DQ 报告 (依赖 T-1 就绪，通常在此处检查并生成)
        if not await pipeline_service.is_stage_success(self.PIPELINE_MORNING, biz_date_str, self.STAGE_M3):
            await self.execute_stage(self.STAGE_M3, biz_date, self.PIPELINE_MORNING)

    async def process_maintenance_trigger(self, biz_date: datetime.date):
        """处理深夜维护流水线 (01:00 - 05:00)"""
        biz_date_str = biz_date.isoformat()
        logger.info(f"【Workflow】触发深夜维护流水线: {biz_date_str}")
        
        # N1 -> N2 -> N3 错峰执行
        for stage in [self.STAGE_N1, self.STAGE_N2, self.STAGE_N3]:
            if not await pipeline_service.is_stage_success(self.PIPELINE_MAINTENANCE, biz_date_str, stage):
                await self.execute_stage(stage, biz_date, self.PIPELINE_MAINTENANCE)
                # 提示：实际执行中每个 Stage 内部可以有更细的逻辑

    async def process_event(self, biz_date: datetime.date, ready_tables: List[str]):
        """根据就绪状态触发盘后流水线"""
        biz_date_str = biz_date.isoformat()
        logger.debug(f"【Workflow】接收到就绪信号: {ready_tables}", extra={"biz_date": biz_date_str, "ready_tables": ready_tables})
        
        # 2. Stage B: 核心综述 (L1/L2 计算)
        if "stock_kline_daily" in ready_tables and "ods_sw_index_daily" in ready_tables:
            if not await pipeline_service.is_stage_success(self.PIPELINE_POST_MARKET, biz_date_str, self.STAGE_B):
                await self.execute_stage(self.STAGE_B, biz_date)

        # 3. Stage C: 质量审计
        if "ads_l1_market_overview" in ready_tables and "ads_l2_industry_daily" in ready_tables:
            if await pipeline_service.is_stage_success(self.PIPELINE_POST_MARKET, biz_date_str, self.STAGE_B):
                if not await pipeline_service.is_stage_success(self.PIPELINE_POST_MARKET, biz_date_str, self.STAGE_C):
                    await self.execute_stage(self.STAGE_C, biz_date)

        # 4. Stage D: 跨网接力
        if await pipeline_service.is_stage_success(self.PIPELINE_POST_MARKET, biz_date_str, self.STAGE_C):
            if not await pipeline_service.is_stage_success(self.PIPELINE_POST_MARKET, biz_date_str, self.STAGE_D):
                await self.execute_stage(self.STAGE_D, biz_date)

    async def execute_stage(self, stage_name: str, biz_date: datetime.date, pipeline_id: Optional[str] = None):
        """执行特定阶段"""
        if pipeline_id is None:
            pipeline_id = self.PIPELINE_POST_MARKET
            
        biz_date_str = biz_date.isoformat()
        run_id = await pipeline_service.create_run(pipeline_id, biz_date_str, stage_name)
        
        logger.info(f"【Workflow】开始执行阶段: {stage_name} (Pipeline: {pipeline_id}, Date: {biz_date_str})")
        
        try:
            result = {"status": "success"}
            
            # --- Phase I: Morning ---
            if stage_name == self.STAGE_M1:
                from app.scheduler.jobs import daily_stock_basic_sync_job
                result = await daily_stock_basic_sync_job()
            elif stage_name == self.STAGE_M2:
                from app.scheduler.jobs import daily_suspension_morning_sync_job, daily_performance_forecast_sync_job
                res1 = await daily_performance_forecast_sync_job()
                res2 = await daily_suspension_morning_sync_job()
                result = {"forecast": res1, "suspension": res2}
            elif stage_name == self.STAGE_M3:
                from app.scheduler.system_jobs import daily_dq_report_job
                result = await daily_dq_report_job()

            # --- Phase II: Post Market ---
            elif stage_name == self.STAGE_A:
                from app.scheduler.jobs import daily_market_overview_sync_job, daily_fund_sync_job
                # 基金同步作为 A 的一部分或前置
                await daily_fund_sync_job()
                result = await daily_market_overview_sync_job()
                
            elif stage_name == self.STAGE_B:
                from app.services.indicator_service import IndicatorService
                indicator_service = IndicatorService()
                res_l1 = await indicator_service.calculate_l1_market_overview(biz_date_str)
                res_l2 = await indicator_service.calculate_l2_indicators_full(biz_date_str)
                from app.scheduler.jobs import _update_readiness
                await _update_readiness("ads_l1_market_overview", biz_date_str, 1)
                await _update_readiness("ads_l2_industry_daily", biz_date_str, 31)
                result = {"l1_success": res_l1, "l2_success": res_l2}
                
            elif stage_name == self.STAGE_C:
                from app.scheduler.jobs import daily_business_rule_check_job
                from app.scheduler.system_jobs import daily_audit_job
                res_check = await daily_business_rule_check_job()
                if res_check.get("status") != "success":
                    raise Exception(f"业务规则校验失败: {res_check.get('message')}")
                res_audit = await daily_audit_job()
                if res_audit.get("status") != "success":
                    raise Exception(f"日终审计失败: {res_audit.get('message')}")
                result = {"check": res_check, "audit": res_audit}

            elif stage_name == self.STAGE_D:
                task_id = "anomaly_v11"
                params = {"biz_date": biz_date_str, "mode": "event"}
                cmd_id = await self.command_service.create_command(task_id, params)
                result = {"command_id": cmd_id, "task_id": task_id}

            # --- Phase III: Maintenance ---
            elif stage_name == self.STAGE_N1:
                from app.scheduler.jobs import weekly_financial_indicators_sync_job
                result = await weekly_financial_indicators_sync_job()
            elif stage_name == self.STAGE_N2:
                from app.scheduler.jobs import daily_analyst_rating_sync_job
                result = await daily_analyst_rating_sync_job()
            elif stage_name == self.STAGE_N3:
                from app.scheduler.jobs import daily_shareholder_sync_job
                result = await daily_shareholder_sync_job()

            await pipeline_service.update_run(run_id, "SUCCESS", output_summary=result)
            logger.info(f"【Workflow】阶段 {stage_name} 执行成功")
            
        except Exception as e:
            logger.error(f"【Workflow】阶段 {stage_name} 执行异常: {e}", exc_info=True)
            await pipeline_service.update_run(run_id, "FAILED", error_msg=str(e))

    async def send_daily_summary_report(self, biz_date: date):
        """每日任务总结报告任务
        目标表: meta_pipeline_run
        功能描述: 汇总全天所有流水线执行结果（晨间、盘后、深夜）并发送 HTML 总结邮件。
        """
        from app.services.ops_service import ops_service
        from app.utils.alerter import alerter
        
        biz_date_str = biz_date.isoformat()
        data = await ops_service.get_mission_control(biz_date_str)
        
        if "error" in data:
            logger.error(f"生成日报失败: {data['error']}")
            return

        # 1. 统计概览
        total_tasks = 0
        success_tasks = 0
        failed_tasks = 0
        total_duration = 0
        
        for p in data.get("pipelines", []):
            for s in p.get("stages", []):
                total_tasks += 1
                if s["status"] == "SUCCESS":
                    success_tasks += 1
                elif s["status"] == "FAILED" or s["status"] == "ERROR":
                    failed_tasks += 1
                if s["duration"]:
                    total_duration += s["duration"]

        # 2. 构造 HTML 明细表格
        pipeline_sections = ""
        for p in data.get("pipelines", []):
            rows_html = ""
            for s in p.get("stages", []):
                status_color = "#28a745" if s["status"] == "SUCCESS" else ("#dc3545" if s["status"] in ["FAILED", "ERROR"] else "#007bff")
                rows_html += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #dee2e6;">{s['stage']}</td>
                    <td style="padding: 8px; border: 1px solid #dee2e6; color: {status_color}; font-weight: bold;">{s['status']}</td>
                    <td style="padding: 8px; border: 1px solid #dee2e6;">{s['start']} - {s['end'] or '...'}</td>
                    <td style="padding: 8px; border: 1px solid #dee2e6;">{s['duration'] or 0}s</td>
                </tr>
                """
                # 如果失败，增加错误详情行
                if s["status"] in ["FAILED", "ERROR"] and s.get("error"):
                    rows_html += f"""
                    <tr>
                        <td colspan="4" style="padding: 8px; border: 1px solid #dee2e6; background-color: #fff5f5; color: #c92a2a; font-size: 12px;">
                            <strong>错误详情:</strong> {s['error']}
                        </td>
                    </tr>
                    """
            
            pipeline_sections += f"""
            <div style="margin-top: 20px;">
                <h4 style="margin-bottom: 10px; color: #495057; border-left: 4px solid #6c757d; padding-left: 10px;">{p['name']}</h4>
                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                    <thead style="background-color: #f8f9fa;">
                        <tr>
                            <th style="padding: 8px; border: 1px solid #dee2e6; text-align: left;">阶段 ID</th>
                            <th style="padding: 8px; border: 1px solid #dee2e6; text-align: left;">状态</th>
                            <th style="padding: 8px; border: 1px solid #dee2e6; text-align: left;">时间窗口</th>
                            <th style="padding: 8px; border: 1px solid #dee2e6; text-align: left;">耗时</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html if rows_html else '<tr><td colspan="4" style="text-align:center; padding:10px; color:#999;">暂无执行记录</td></tr>'}
                    </tbody>
                </table>
            </div>
            """

        # 3. 发送邮件
        summary_context = {
            "数据日期": biz_date_str,
            "总任务数": total_tasks,
            "成功/失败": f"{success_tasks} / {failed_tasks}",
            "累计耗时": f"{total_duration}s",
            "任务清单": f"<div style='margin-top:10px;'>{pipeline_sections}</div>"
        }
        
        level = "ERROR" if failed_tasks > 0 else "INFO"
        await alerter.alert(
            level=level,
            title=f"数据管线日终报告 ({biz_date_str})",
            context=summary_context
        )
        logger.info(f"每日执行总结报告已发送: {biz_date_str}")

workflow_service = WorkflowService()
