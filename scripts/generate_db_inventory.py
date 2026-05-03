import asyncio
import os
import aiomysql
import datetime
from dotenv import load_dotenv

load_dotenv()

# 配置
OUTPUT_FILE = "docs/design/复盘/db_inventory.md"
DB_CONFIG = {
    'host': os.getenv("DB_HOST"),
    'port': int(os.getenv("DB_PORT", 3306)),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD"),
    'db': os.getenv("DB_NAME"),
    'charset': 'utf8mb4',
    'autocommit': True
}

# 简单的分类逻辑 (根据表名前缀或特定关键字)
CATEGORIES = {
    "行情与原始数据 (Market Raw Data)": ["daily_", "kday_", "ods_", "stock_kline", "market_"],
    "财务与基本面 (Financial Data)": ["stock_balance", "stock_cash", "stock_income", "stock_finance", "stock_shareholder", "stock_top10"],
    "监控与指标层 (Monitor & Indicators)": ["monitor_", "ads_"],
    "系统审计与元数据 (System & Metadata)": ["commands", "data_audit", "data_gate", "migrations_"],
    "股市日记与盘后复盘 (Diary & Market Review)": ["fupan_", "diary_"],
}

async def generate_markdown():
    conn = await aiomysql.connect(**DB_CONFIG)
    async with conn.cursor(aiomysql.DictCursor) as cur:
        # 1. 获取所有表的信息 (包括空间占用)
        sql_tables = f"""
        SELECT 
            TABLE_NAME, 
            TABLE_COMMENT, 
            TABLE_ROWS, 
            DATA_LENGTH / 1024 / 1024 AS DATA_MB, 
            INDEX_LENGTH / 1024 / 1024 AS INDEX_MB 
        FROM information_schema.tables 
        WHERE TABLE_SCHEMA = '{DB_CONFIG['db']}'
        ORDER BY TABLE_NAME
        """
        await cur.execute(sql_tables)
        tables = await cur.fetchall()

        # 2. 获取所有字段信息
        sql_columns = f"""
        SELECT 
            TABLE_NAME, 
            COLUMN_NAME, 
            COLUMN_TYPE, 
            IS_NULLABLE, 
            COLUMN_KEY, 
            COLUMN_COMMENT 
        FROM information_schema.columns 
        WHERE TABLE_SCHEMA = '{DB_CONFIG['db']}'
        ORDER BY TABLE_NAME, ORDINAL_POSITION
        """
        await cur.execute(sql_columns)
        all_columns = await cur.fetchall()

        # 按表组织字段
        columns_by_table = {}
        for col in all_columns:
            t_name = col['TABLE_NAME']
            if t_name not in columns_by_table:
                columns_by_table[t_name] = []
            columns_by_table[t_name].append(col)

        # 3. 构造 Markdown
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        md = [f"# 数据库表结构与空间占用报告\n"]
        md.append(f"- **生成时间**: {now}")
        md.append(f"- **数据库名**: `{DB_CONFIG['db']}`\n")

        # 归类表
        categorized_tables = {cat: [] for cat in CATEGORIES}
        categorized_tables["其他与备份 (Others/Legacy)"] = []

        for table in tables:
            t_name = table['TABLE_NAME']
            found = False
            for cat, prefixes in CATEGORIES.items():
                if any(t_name.startswith(p) for p in prefixes):
                    categorized_tables[cat].append(table)
                    found = True
                    break
            if not found:
                categorized_tables["其他与备份 (Others/Legacy)"].append(table)

        # 写入分类内容
        for cat, t_list in categorized_tables.items():
            if not t_list: continue
            md.append(f"## {cat}\n")
            for t in t_list:
                t_name = t['TABLE_NAME']
                comment = t['TABLE_COMMENT'] or "无备注"
                rows = t['TABLE_ROWS'] or 0
                data_mb = t['DATA_MB'] or 0
                index_mb = t['INDEX_MB'] or 0
                total_mb = data_mb + index_mb
                
                md.append(f"### 表: `{t_name}`")
                md.append(f"- **描述**: {comment}")
                md.append(f"- **行数**: {rows:,}")
                md.append(f"- **占用空间**: {total_mb:.2f} MB (数据: {data_mb:.2f}MB, 索引: {index_mb:.2f}MB)\n")
                
                md.append("| 字段名 | 类型 | 必填 | 键 | 备注 |")
                md.append("|---|---|---|---|---|")
                for col in columns_by_table.get(t_name, []):
                    nullable = "No" if col['IS_NULLABLE'] == "NO" else "Yes"
                    md.append(f"| {col['COLUMN_NAME']} | {col['COLUMN_TYPE']} | {nullable} | {col['COLUMN_KEY']} | {col['COLUMN_COMMENT']} |")
                md.append("\n---\n")

        # 4. 保存文件
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(md))
        
        print(f"✅ 文档已更新: {OUTPUT_FILE}")

    conn.close()

if __name__ == "__main__":
    asyncio.run(generate_markdown())
