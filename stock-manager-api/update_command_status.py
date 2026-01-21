
import asyncio
from app.utils.database import db

async def update_status():
    await db.connect()
    try:
        await db.execute("UPDATE task_commands SET status='RUNNING' WHERE id=28")
        print("Updated command 28 to RUNNING")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(update_status())
