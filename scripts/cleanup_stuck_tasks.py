
import asyncio
import os
import aiomysql
from dotenv import load_dotenv

load_dotenv()

async def cleanup_stuck_tasks():
    run_id = '54f06d3d-f677-4fa2-9a07-c43ead672a9c'
    try:
        conn = await aiomysql.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            db=os.getenv("DB_NAME"),
            charset='utf8mb4',
            autocommit=True
        )
        async with conn.cursor() as cur:
            # 1. Update workflow_runs
            print(f"Updating workflow_runs for run_id: {run_id}")
            await cur.execute("UPDATE workflow_runs SET status = 'FAILED', end_time = NOW() WHERE run_id = %s AND status = 'RUNNING'", (run_id,))
            print(f"Affected rows in workflow_runs: {cur.rowcount}")

            # 2. Update task_commands
            print(f"Updating task_commands for run_id: {run_id}")
            await cur.execute("UPDATE task_commands SET status = 'FAILED', executed_at = NOW() WHERE run_id = %s AND status IN ('RUNNING', 'PENDING')", (run_id,))
            print(f"Affected rows in task_commands: {cur.rowcount}")

        conn.close()
    except Exception as e:
        print(f"Cleanup failed: {e}")

if __name__ == "__main__":
    asyncio.run(cleanup_stuck_tasks())
