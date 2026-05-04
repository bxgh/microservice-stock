import asyncio
from app.utils.database import db

async def main():
    await db.connect()
    rows = await db.execute("SHOW TABLES")
    for r in rows:
        print(r[0])
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
