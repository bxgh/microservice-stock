import logging
import datetime
from typing import List, Dict, Any, Optional
from app.services.pipeline_service import pipeline_service
from app.services.task_command_service import TaskCommandService
from app.utils.logger import get_logger

logger = get_logger("stock-manager.workflow")

class WorkflowService:
    """云端四阶段流水线管理器"""
    
    PIPELINE_ID = "post_market_cloud"
    
    # 阶段定义
    STAGE_A = "STAGE_A_COLLECTION"  # 基础采集 (K线/指数/停复牌)
    STAGE_B = "STAGE_B_SYNTHESIS"   # 核心综述 (L1/L2 因子计算)
    STAGE_C = "STAGE_C_QA_AUDIT"    # 质量审计
    STAGE_D = "STAGE_D_HANDOVER"    # 跨网接力

    def __init__(self):
        self.command_service = TaskCommandService()

    async def process_event(self, biz_date: datetime.date, ready_tables: List[str]):
        """根据就绪状态触发流水线"""
        biz_date_str = biz_date.isoformat()
        logger.debug(f"【Workflow】接收到就绪信号: {ready_tables}", extra={"biz_date": biz_date_str, "ready_tables": ready_tables})
        
        # 1. Stage A: 基础采集 (当探测到外部源就绪时触发，通常由 readiness_prober 触发或手动)
        # 注意: Stage A 本身会产出 stock_kline_daily 等，所以它不依赖 ready_tables 里的这些表
        # 这里由 readiness_prober 检测到 Canary 就绪后直接调用 execute_stage(STAGE_A)
        
        # 2. Stage B: 核心综述 (L1/L2 计算)
        # 条件: K线就绪 且 申万指数就绪 且 Stage A 成功 (或直接看表状态)
        if "stock_kline_daily" in ready_tables and "ods_sw_index_daily" in ready_tables:
            if not await pipeline_service.is_stage_success(self.PIPELINE_ID, biz_date_str, self.STAGE_B):
                await self.execute_stage(self.STAGE_B, biz_date)

        # 3. Stage C: 质量审计
        # 条件: Stage B 成功 且 L1综述就绪 且 L2行业就绪
        if "ads_l1_market_overview" in ready_tables and "ads_l2_industry_daily" in ready_tables:
            if await pipeline_service.is_stage_success(self.PIPELINE_ID, biz_date_str, self.STAGE_B):
                if not await pipeline_service.is_stage_success(self.PIPELINE_ID, biz_date_str, self.STAGE_C):
                    await self.execute_stage(self.STAGE_C, biz_date)

        # 4. Stage D: 跨网接力
        # 条件: Stage C 成功
        if await pipeline_service.is_stage_success(self.PIPELINE_ID, biz_date_str, self.STAGE_C):
            if not await pipeline_service.is_stage_success(self.PIPELINE_ID, biz_date_str, self.STAGE_D):
                await self.execute_stage(self.STAGE_D, biz_date)

    async def execute_stage(self, stage_name: str, biz_date: datetime.date):
        """执行特定阶段"""
        biz_date_str = biz_date.isoformat()
        run_id = await pipeline_service.create_run(self.PIPELINE_ID, biz_date_str, stage_name)
        
        logger.info(f"【Workflow】开始执行阶段: {stage_name} ({biz_date_str})")
        
        try:
            result = {"status": "success"}
            
            if stage_name == self.STAGE_A:
                from app.scheduler.jobs import daily_market_overview_sync_job
                result = await daily_market_overview_sync_job()
                
            elif stage_name == self.STAGE_B:
                from app.services.indicator_service import IndicatorService
                indicator_service = IndicatorService()
                
                # 计算 L1 全景指标
                res_l1 = await indicator_service.calculate_l1_market_overview(biz_date_str)
                # 计算 L2 行业/因子指标
                res_l2 = await indicator_service.calculate_l2_indicators_full(biz_date_str)
                
                # 主动申报就绪 (由内部函数执行，此处记录结果)
                # 注意：calculate_l1/l2 内部通常已经写了数据库，我们需要显式申报 meta_data_readiness
                from app.scheduler.jobs import _update_readiness
                await _update_readiness("ads_l1_market_overview", biz_date_str, 1)
                await _update_readiness("ads_l2_industry_daily", biz_date_str, 31)
                
                result = {"l1_success": res_l1, "l2_success": res_l2}
                
            elif stage_name == self.STAGE_C:
                from app.scheduler.jobs import daily_business_rule_check_job
                from app.scheduler.system_jobs import daily_audit_job
                
                # 顺序执行 业务校验 -> 审计
                res_check = await daily_business_rule_check_job()
                if res_check.get("status") != "success":
                    raise Exception(f"业务规则校验失败: {res_check.get('message')}")
                
                res_audit = await daily_audit_job()
                if res_audit.get("status") != "success":
                    raise Exception(f"日终审计失败: {res_audit.get('message')}")
                
                result = {"check": res_check, "audit": res_audit}

            elif stage_name == self.STAGE_D:
                # 下发内网指令
                # 示例任务：异动扫描 v1.1
                task_id = "anomaly_v11"
                params = {"biz_date": biz_date_str, "mode": "event"}
                cmd_id = await self.command_service.create_command(task_id, params)
                result = {"command_id": cmd_id, "task_id": task_id}

            await pipeline_service.update_run(run_id, "SUCCESS", output_summary=result)
            logger.info(f"【Workflow】阶段 {stage_name} 执行成功", extra={"stage": stage_name, "biz_date": biz_date_str})
            
        except Exception as e:
            logger.error(f"【Workflow】阶段 {stage_name} 执行异常: {e}", extra={"stage": stage_name, "biz_date": biz_date_str}, exc_info=True)
            await pipeline_service.update_run(run_id, "FAILED", error_msg=str(e))

workflow_service = WorkflowService()
