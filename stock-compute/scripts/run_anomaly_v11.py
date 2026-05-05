import asyncio
import sys
import os
from datetime import date

# 将 app 目录加入路径
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.scheduler.pipeline_runner import PipelineRunner
from app.sync.cloud_to_local import CloudDataSyncer
from app.common.global_gate import GlobalTaskGate
from app.utils.database import cloud_db, internal_db

# 任务定义 (从设计文档 E5-S2 镜像)
ANOMALY_V11_TASKS = [
    {
        "task_id": "compute_derived_metrics",
        "type": "python_isolated",
        "script": "scripts/anomaly/compute_derived_metrics.py",
        "mem_limit_mb": 1500,
        "timeout_sec": 600,
        "retry": 2,
    },
    {
        "task_id": "compute_market_state",
        "type": "python_isolated",
        "script": "scripts/anomaly/compute_market_state.py",
        "mem_limit_mb": 300,
        "timeout_sec": 120,
    },
    # ... 后续任务可按需添加
]

async def main():
    biz_date_str = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    biz_date = date.fromisoformat(biz_date_str)
    
    print(f"开始执行异动管线 v1.1 | 业务日期: {biz_date}")
    
    # 1. 初始化
    import redis.asyncio as redis
    redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    gate = GlobalTaskGate(redis_client)
    syncer = CloudDataSyncer()
    runner = PipelineRunner("anomaly_v11", ANOMALY_V11_TASKS, gate)
    
    try:
        # 2. 同步数据
        print("Step 1: 同步云端数据...")
        await syncer.sync_for_compute(biz_date)
        
        # 3. 运行管线
        print("Step 2: 启动异动计算管线...")
        await runner.run(biz_date)
        
        print("异动管线执行成功!")
    except Exception as e:
        print(f"管线执行失败: {e}")
    finally:
        await cloud_db.pool.close() if cloud_db.pool else None
        await internal_db.pool.close() if internal_db.pool else None

if __name__ == "__main__":
    asyncio.run(main())
