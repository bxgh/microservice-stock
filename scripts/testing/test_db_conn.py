import os
import pymysql
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def test_db_connection():
    print("--- 数据库连接测试 ---")
    host = os.getenv("DB_HOST")
    port = int(os.getenv("DB_PORT", 3306))
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    db_name = os.getenv("DB_NAME")

    print(f"尝试连接: {host}:{port}, 用户: {user}, 数据库: {db_name}")

    try:
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=db_name,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10
        )
        print("✓ 连接成功!")
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION() as version")
            result = cursor.fetchone()
            print(f"✓ 数据库版本: {result['version']}")
            
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"✓ 发现数据表数量: {len(tables)}")
            if tables:
                print("  示例表名:", tables[0])

        connection.close()
    except Exception as e:
        print(f"✗ 连接失败: {e}")

if __name__ == "__main__":
    test_db_connection()
