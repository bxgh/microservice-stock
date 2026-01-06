#!/usr/bin/env python3
"""查询腾讯云MySQL monitoring数据库"""
import asyncio
import aiomysql
import os

async def check_monitoring_db():
    """检查monitoring数据库"""
    conn = await aiomysql.connect(
        host='sh-cdb-h7flpxu4.sql.tencentcdb.com',
        port=26300,
        user='root',
        password='alwaysup@888',
        charset='utf8mb4'
    )
    
    try:
        async with conn.cursor() as cursor:
            # 1. 显示所有数据库
            print("=" * 60)
            print("所有数据库:")
            print("=" * 60)
            await cursor.execute("SHOW DATABASES")
            databases = await cursor.fetchall()
            for db in databases:
                print(f"  - {db[0]}")
            
            # 2. 检查monitoring数据库是否存在
            db_names = [db[0] for db in databases]
            if 'monitoring' in db_names:
                print("\n" + "=" * 60)
                print("monitoring数据库 - 表列表:")
                print("=" * 60)
                await cursor.execute("USE monitoring")
                await cursor.execute("SHOW TABLES")
                tables = await cursor.fetchall()
                for table in tables:
                    print(f"  - {table[0]}")
                
                # 3. 查看每个表的结构和数据量
                print("\n" + "=" * 60)
                print("表详情:")
                print("=" * 60)
                for table in tables:
                    table_name = table[0]
                    # 获取行数
                    await cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = await cursor.fetchone()
                    
                    # 获取表结构
                    await cursor.execute(f"DESCRIBE {table_name}")
                    columns = await cursor.fetchall()
                    
                    print(f"\n表名: {table_name}")
                    print(f"记录数: {count[0]}")
                    print("字段:")
                    for col in columns:
                        print(f"  - {col[0]}: {col[1]} {col[2]} {col[3]}")
                    
                    # 显示最近几条记录
                    if count[0] > 0:
                        await cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
                        rows = await cursor.fetchall()
                        print("最近5条记录:")
                        for row in rows:
                            print(f"  {row}")
            else:
                print("\n⚠️ monitoring数据库不存在!")
                print("可用的数据库:", db_names)
    
    finally:
        conn.close()

if __name__ == "__main__":
    asyncio.run(check_monitoring_db())
