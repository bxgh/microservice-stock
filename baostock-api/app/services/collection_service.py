
import asyncio
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
import httpx

from app.utils.logger import get_logger
from app.utils.database import db
from app.services.baostock_service import BaoStockService

logger = get_logger("baostock-api.collection")

class CollectionService:
    """
    数据采集与修复服务
    负责处理 "Remote Calibration" 请求，即按需的数据重采与修复。
    """
    
    # 内存任务注册表 (LRU-like via fixed size limit)
    # 结构: task_id -> {status, progress, result, error}
    _TASK_REGISTRY: Dict[str, Dict[str, Any]] = {}
    _MAX_REGISTRY_SIZE = 1000
    
    def __init__(self, baostock_service: BaoStockService):
        self.bs_service = baostock_service

    def _register_task(self, task_type: str, metadata: Dict[str, Any]) -> str:
        """注册新任务"""
        task_id = str(uuid.uuid4())
        
        # 简单的清理逻辑: 如果超过最大数量，清理最早的 100 个
        if len(self._TASK_REGISTRY) >= self._MAX_REGISTRY_SIZE:
            keys_to_remove = list(self._TASK_REGISTRY.keys())[:100]
            for k in keys_to_remove:
                del self._TASK_REGISTRY[k]
        
        self._TASK_REGISTRY[task_id] = {
            "id": task_id,
            "type": task_type,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "metadata": metadata,
            "progress": 0,
            "result": None,
            "error": None
        }
        return task_id

    def _update_task(self, task_id: str, status: str, progress: int = None, result: Any = None, error: str = None):
        """更新任务状态"""
        if task_id not in self._TASK_REGISTRY:
            return
        
        task_data = self._TASK_REGISTRY[task_id]
        task_data["status"] = status
        task_data["updated_at"] = datetime.now().isoformat()
        
        if progress is not None:
            task_data["progress"] = progress
        if result is not None:
            task_data["result"] = result
        if error is not None:
            task_data["error"] = error
            
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """查询任务状态"""
        return self._TASK_REGISTRY.get(task_id)

    async def run_stock_history_collection(self, task_id: str, stock_code: str, start_date: str, clear_existing: bool, callback_url: str = None, request_id: str = None):
        """
        执行个股历史数据采集任务
        """
        log_extra = {"request_id": request_id} if request_id else {}
        logger.info(f"Task[{task_id}] 开始采集: code={stock_code}, start={start_date}, clear={clear_existing}", extra=log_extra)
        self._update_task(task_id, "running", progress=0)
        
        try:
            # 1. 如果需要，清除已有数据
            if clear_existing:
                logger.info(f"Task[{task_id}] 清除旧数据: {stock_code}", extra=log_extra)
                # 使用 DELETE 语句清除 MySQL 中的数据
                # 注意: 表名需与实际一致，这里假设是 stock_kline_daily
                await db.execute("DELETE FROM stock_kline_daily WHERE code = %s", (stock_code,))
            
            self._update_task(task_id, "running", progress=10)
            
            # 2. 调用 BaoStockService 执行同步
            logger.info(f"Task[{task_id}] 调用底层同步服务...", extra=log_extra)
            # 强制使用传入的 start_date，不检查增量
            result = await self.bs_service.sync_kline_to_db(
                code=stock_code,
                start_date=start_date,
                frequency="d",
                adjust="2", # 默认前复权
                use_db_latest=False 
            )
            
            if not result["success"]:
                raise Exception(result.get("error", "Unknown sync error"))
            
            # 任务成功
            collected_count = result.get("count", 0)
            performance = result.get("performance", {})
            
            logger.info(f"Task[{task_id}] 成功: {collected_count} records", extra=log_extra)
            
            final_result = {
                "stock_code": stock_code,
                "records_collected": collected_count,
                "performance_ms": performance.get("total_ms", 0),
                "date_range": [start_date, datetime.now().strftime("%Y-%m-%d")] # 简化的范围
            }
            
            self._update_task(task_id, "success", progress=100, result=final_result)
            
            # 3. 回调通知 (Webhook)
            if callback_url:
                await self._send_webhook(callback_url, {
                    "task_id": task_id,
                    "status": "success",
                    "result": final_result
                })

        except (TimeoutError, ValueError, KeyError, ConnectionError) as e:
            logger.error(f"Task[{task_id}] 失败: {e}", exc_info=True, extra=log_extra)
            self._update_task(task_id, "failed", error=str(e))
            
            if callback_url:
                await self._send_webhook(callback_url, {
                    "task_id": task_id,
                    "status": "failed",
                    "error": str(e)
                })
        except Exception as e:
            # 捕获未预期的错误
            logger.critical(f"Task[{task_id}] 未预期错误: {e}", exc_info=True, extra=log_extra)
            self._update_task(task_id, "failed", error=f"Unexpected error: {str(e)}")
            
            if callback_url:
                await self._send_webhook(callback_url, {
                    "task_id": task_id,
                    "status": "failed",
                    "error": f"Unexpected error: {str(e)}"
                })

    async def submit_collection_task(self, stock_code: str, start_date: str = "1990-01-01", clear_existing: bool = False, callback_url: str = None) -> str:
        """提交一个新的采集任务"""
        # 标准化代码
        if not stock_code.startswith(("sh.", "sz.")):
            stock_code = f"sh.{stock_code}" if stock_code.startswith("6") else f"sz.{stock_code}"
            
        task_meta = {
            "stock_code": stock_code,
            "start_date": start_date,
            "clear_existing": clear_existing,
            "callback_url": callback_url
        }
        
        task_id = self._register_task("stock_history", task_meta)
        return task_id

    async def _send_webhook(self, url: str, payload: Dict[str, Any]):
        """发送 Webhook 回调"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(url, json=payload)
                logger.info(f"Webhook sent to {url}")
        except Exception as e:
            logger.warning(f"Webhook failed to {url}: {e}")
