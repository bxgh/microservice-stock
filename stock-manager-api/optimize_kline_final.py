import asyncio
import aiomysql
import sys
import time
from datetime import datetime

sys.path.append('/app')
from app.config import settings

async def optimize():
    print(f"[{datetime.now()}] 启动 stock_kline_daily 深度优化任务 (V2 - 增强超时兼容版)...")
    
    try:
        conn = await aiomysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            db=settings.DB_NAME,
            autocommit=True
        )
        
        async with conn.cursor() as cur:
            # 关键：设置会话级别超时，防止 Lost connection
            print("正在设置会话超时限制...")
            await cur.execute("SET SESSION net_read_timeout = 7200")
            await cur.execute("SET SESSION net_write_timeout = 7200")
            await cur.execute("SET SESSION wait_timeout = 7200")
            await cur.execute("SET SESSION interactive_timeout = 7200")
            
            sql = """
            ALTER TABLE stock_kline_daily
                DROP PRIMARY KEY,
                DROP INDEX uk_code_date,
                DROP COLUMN id,
                DROP COLUMN code,
                ADD PRIMARY KEY (ts_code, trade_date),
                ROW_FORMAT=COMPRESSED;
            """
            
            start_time = time.time()
            print(f"[{datetime.now()}] 正在执行 ALTER TABLE，此过程约需 30-60 分钟，请耐心等待...")
            
            await cur.execute(sql)
            
            end_time = time.time()
            print(f"[{datetime.now()}] 优化成功！总耗时: {end_time - start_time:.2f} 秒")
            
        conn.close()
        
    except Exception as e:
        print(f"[{datetime.now()}] 优化过程中发生错误: {e}")
        # 如果还是 Lost connection，建议联系腾讯云控制台调大全局 net_read_timeout
        if "2013" in str(e):
            print("提示：检测到连接丢失。如果此问题持续出现，可能是云数据库网关层的硬性限制，建议在凌晨业务低峰期再次尝试。")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(optimize())
