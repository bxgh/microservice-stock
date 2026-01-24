from app.utils.database import db
import asyncio

async def check():
    await db.connect()
    r1 = await db.execute("SELECT COUNT(*) FROM stock_restricted_release")
    r2 = await db.execute("SELECT COUNT(*) FROM stock_block_trade")
    print(f"Restricted Release rows: {r1[0][0]}")
    print(f"Block Trade rows: {r2[0][0]}")
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(check())
