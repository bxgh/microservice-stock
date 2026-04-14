import asyncio
import sys
import logging
from datetime import datetime, timedelta

# 适配 Docker 路径
sys.path.append("/app")
from app.utils.database import db
from app.utils.http_client import http_client

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("backfill_lhb")

async def backfill_lhb(start_date: str, end_date: str):
    """
    回溯龙虎榜数据
    按月步进，因为单次请求范围不宜过大
    """
    await db.connect()
    try:
        current = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        while current <= end:
            # 每次请求一个月
            next_month = current + timedelta(days=30)
            if next_month > end:
                next_month = end
            
            s_str = current.strftime("%Y-%m-%d")
            e_str = next_month.strftime("%Y-%m-%d")
            
            logger.info(f"正在抓取区间: {s_str} 至 {e_str}")
            
            # 使用现有 Service 逻辑 (akshare-api)
            # GET /api/v1/game/lhb/detail?start_date=X&end_date=Y
            # 注意：我们需要确保 akshare-api 有暴露按日期范围的接口
            # 目前文档看，/api/v1/game/lhb/detail 是我们自己定义的 path 吗？
            # 检查一下 akshare-api/app/api/market.py 或其他
            
            # 由于之前未明确暴露范围接口，可能需要直接调用 akshare_service
            # 或者使用 http_client 调用 akshare-api 假设它有
            # 我们直接在 akshare-api 增加一个范围接口最稳妥，或者利用现有的 get_lhb_detail(start, end)
            
            # 检查 akshare_service.get_lhb_detail 确实支持 start/end
            # 检查 akshare-api router:
            # 暂时假设 akshare-api 有 /api/v1/game/lhb?start_date=...&end_date=...
            # 如果没有，我们稍后补上。先写脚本骨架。
            
            # 模拟调用 (实际需替换为真实 URL)
            params = {"start_date": s_str, "end_date": e_str}
            # Path correct: /api/v1/dragon_tiger/daily
            data = await http_client.get("akshare", "/api/v1/dragon_tiger/daily", params=params)
            
            if data:
                rows = []
                for item in data:
                     raw_code = item.get("code")
                     # Format Code
                     if not raw_code: continue
                     
                     if raw_code.startswith("6"): ts_code = f"{raw_code}.SH"
                     elif raw_code.startswith("8") or raw_code.startswith("4") or raw_code.startswith("9"): ts_code = f"{raw_code}.BJ"
                     else: ts_code = f"{raw_code}.SZ"

                     rows.append((
                        ts_code,
                        # name is not in DB
                        item.get("date"),
                        item.get("close"),
                        item.get("change_pct"),
                        item.get("turnover_rate"),
                        item.get("net_buy"), # map to net_buy_amt
                        item.get("reason")
                    ))
                
                if rows:
                    sql = """
                    INSERT IGNORE INTO stock_lhb_daily 
                    (ts_code, trade_date, close_price, change_pct, turnover_rate, net_buy_amt, reason)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """
                    await db.execute_many(sql, rows)
                    logger.info(f"已入库 {len(rows)} 条")
                    logger.info(f"已入库 {len(rows)} 条")
            
            current = next_month + timedelta(days=1)
            await asyncio.sleep(2) # 限流
            
    except Exception as e:
        logger.error(f"回溯失败: {e}")
    finally:
        await db.disconnect()
        await http_client.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 backfill_lhb.py 2023-01-01 2023-12-31")
    else:
        asyncio.run(backfill_lhb(sys.argv[1], sys.argv[2]))
