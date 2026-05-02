import asyncio
import os
import sys
import aiomysql
from datetime import datetime

# 加载配置
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
try:
    from app.config import settings
except ImportError:
    # 兼容直接从 database 目录运行
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from app.config import settings

async def run_migrations():
    """轻量级数据库迁移工具"""
    print(f"[{datetime.now()}] 启动数据库迁移...")
    
    conn = await aiomysql.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        db=settings.DB_NAME,
        autocommit=True
    )
    
    async with conn.cursor() as cur:
        # 1. 确保迁移历史表存在
        await cur.execute("""
            CREATE TABLE IF NOT EXISTS migrations_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                migration_name VARCHAR(255) UNIQUE NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        
        # 2. 获取已应用的迁移记录
        await cur.execute("SELECT migration_name FROM migrations_history")
        applied_versions = {row[0] for row in await cur.fetchall()}
        
        # 3. 扫描迁移文件
        migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
        if not os.path.exists(migrations_dir):
            print(f"错误: 迁移目录不存在 {migrations_dir}")
            return

        files = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])
        
        for file in files:
            if file in applied_versions:
                continue
            
            print(f"正在应用迁移: {file}...")
            filepath = os.path.join(migrations_dir, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                sql = f.read()
            
            # 按分号拆分执行
            statements = [s.strip() for s in sql.split(';') if s.strip()]
            
            try:
                for statement in statements:
                    await cur.execute(statement)
                
                # 记录成功
                await cur.execute("INSERT INTO migrations_history (migration_name) VALUES (%s)", (file,))
                print(f"成功应用迁移: {file}")
            except Exception as e:
                # 如果是“列已存在”错误，视为成功并记录
                if "Duplicate column name" in str(e):
                    await cur.execute("INSERT INTO migrations_history (migration_name) VALUES (%s)", (file,))
                    print(f"迁移 {file} 中的列已存在，已标记为已应用。")
                else:
                    print(f"应用迁移 {file} 失败: {e}")
                    sys.exit(1)
                
    conn.close()
    print(f"[{datetime.now()}] 数据库迁移完成。")

if __name__ == "__main__":
    asyncio.run(run_migrations())
