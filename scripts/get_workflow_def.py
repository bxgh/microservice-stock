
import asyncio
import os
import aiomysql
from dotenv import load_dotenv

load_dotenv()

async def get_workflow_def(workflow_id):
    try:
        conn = await aiomysql.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            db=os.getenv("DB_NAME"),
            charset='utf8mb4'
        )
        async with conn.cursor() as cur:
            await cur.execute("SELECT definition FROM workflow_definitions WHERE id = %s", (workflow_id,))
            row = await cur.fetchone()
            if row:
                import json
                print(json.dumps(json.loads(row[0]), indent=2, ensure_ascii=False))
            else:
                print(f"Workflow {workflow_id} not found")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import sys
    wid = sys.argv[1] if len(sys.argv) > 1 else "pre_market_prep_4.0"
    asyncio.run(get_workflow_def(wid))
