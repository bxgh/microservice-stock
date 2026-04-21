
import asyncio
import os
import httpx
import aiomysql
from dotenv import load_dotenv
import logging

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("sync_financials")

load_dotenv()

# 配置
AKSHARE_URL = "http://localhost:8003/api/v1/finance/historical"
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "db": os.getenv("DB_NAME"),
    "autocommit": True,
    "charset": 'utf8mb4'
}

async def get_stock_codes(pool):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT ts_code FROM stock_basic_info WHERE list_status = 'L'")
            rows = await cur.fetchall()
            return [row[0] for row in rows]

async def sync_stock_financials(pool, client, ts_code):
    try:
        # AkShare API 通常接受 600519 这种格式
        symbol = ts_code.split(".")[0]
        # 但 akshare-api service 会自动转换，所以发 600519 即可
        
        logger.info(f"Fetching financials for {ts_code}...")
        resp = await client.get(f"{AKSHARE_URL}/{symbol}", timeout=60.0)
        if resp.status_code != 200:
            logger.error(f"Failed to fetch {ts_code}: {resp.status_code}")
            return
            
        data = resp.json()
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                # 1. 保存资产负债表
                bs_list = data.get("balance_sheets", [])
                for bs in bs_list:
                    cols = [
                        "ts_code", "report_date", "notice_date", "total_assets", "total_liabilities",
                        "total_equity", "total_equity_ato_parent", "monetary_funds", "accounts_receivable",
                        "notes_receivable", "inventory", "goodwill", "short_term_borrowings", "long_term_borrowings",
                        "total_current_assets", "total_non_current_assets", "total_current_liabilities", "total_non_current_liabilities"
                    ]
                    keys = ", ".join(cols)
                    placeholders = ", ".join(["%s"] * len(cols))
                    values = [ts_code, bs.get("report_date"), bs.get("notice_date")] + [bs.get(c) for c in cols[3:]]
                    
                    # 使用 ON DUPLICATE KEY UPDATE 保持幂等
                    update_stmt = ", ".join([f"{c}=VALUES({c})" for c in cols[2:]])
                    sql = f"INSERT INTO stock_balance_sheet ({keys}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_stmt}"
                    await cur.execute(sql, values)

                # 2. 保存利润表
                is_list = data.get("income_statements", [])
                for is_row in is_list:
                    cols = [
                        "ts_code", "report_date", "notice_date", "total_revenue", "operating_revenue",
                        "total_operating_cost", "operating_cost", "selling_expenses", "administrative_expenses",
                        "financial_expenses", "research_expenses", "operating_profit", "total_profit",
                        "net_profit", "parent_net_profit", "deducted_net_profit", "ebit"
                    ]
                    keys = ", ".join(cols)
                    placeholders = ", ".join(["%s"] * len(cols))
                    values = [ts_code, is_row.get("report_date"), is_row.get("notice_date")] + [is_row.get(c) for c in cols[3:]]
                    
                    update_stmt = ", ".join([f"{c}=VALUES({c})" for c in cols[2:]])
                    sql = f"INSERT INTO stock_income_statement ({keys}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_stmt}"
                    await cur.execute(sql, values)

                # 3. 保存现金流量表
                cf_list = data.get("cash_flows", [])
                for cf in cf_list:
                    cols = [
                        "ts_code", "report_date", "notice_date", "net_operating_cash_flow",
                        "net_investing_cash_flow", "net_financing_cash_flow", "capex",
                        "free_cash_flow", "cash_and_equivalents_at_end"
                    ]
                    keys = ", ".join(cols)
                    placeholders = ", ".join(["%s"] * len(cols))
                    values = [ts_code, cf.get("report_date"), cf.get("notice_date")] + [cf.get(c) for c in cols[3:]]
                    
                    update_stmt = ", ".join([f"{c}=VALUES({c})" for c in cols[2:]])
                    sql = f"INSERT INTO stock_cash_flow_statement ({keys}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_stmt}"
                    await cur.execute(sql, values)
                    
        logger.info(f"Successfully synced {ts_code}: {len(bs_list)} BS, {len(is_list)} IS, {len(cf_list)} CF rows.")

    except Exception as e:
        logger.error(f"Error syncing {ts_code}: {e}")

async def main():
    pool = await aiomysql.create_pool(**DB_CONFIG)
    codes = await get_stock_codes(pool)
    
    # 为了演示，先只同步前 5 个
    test_codes = codes[:5]
    logger.info(f"Starting sync for {len(test_codes)} stocks...")
    
    async with httpx.AsyncClient() as client:
        for code in test_codes:
            await sync_stock_financials(pool, client, code)
            # 适当延时防止限流
            await asyncio.sleep(1)
            
    pool.close()
    await pool.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
