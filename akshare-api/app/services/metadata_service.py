
import asyncio
import time
import gc
import pandas as pd
import akshare as ak
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
from app.utils.logger import get_logger
from app.utils.database import db

logger = get_logger("akshare-api.metadata")

def fetch_ipo_info_worker(symbol: str) -> Dict[str, Any]:
    """Worker function to fetch IPO info from 10jqka (Direct HTML Scraping)"""
    try:
        code = symbol.split(".")[0] if "." in symbol else symbol
        
        url = f"http://basic.10jqka.com.cn/{code}/company.html"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        
        # We need a synchronous request because this runs in a thread pool executor
        import requests
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            html = resp.content.decode('gbk', errors='ignore')
            
            if "发行价格" in html:
                import re
                idx = html.find("发行价格")
                # Look at sufficient context
                context = html[idx:idx+300]
                
                # Pattern 1: 31.39元
                match = re.search(r'([\d\.]+)(?=元)', context)
                if match:
                    val = float(match.group(1))
                    return {"symbol": symbol, "price": val}
                
                # Pattern 2: <td>31.39</td>
                match2 = re.search(r'>\s*([\d\.]+)\s*<', context)
                if match2:
                    val = float(match2.group(1))
                    return {"symbol": symbol, "price": val}
            
        return {"symbol": symbol, "price": None}
    except Exception as e:
        return {"symbol": symbol, "price": None, "error": str(e)}

def fetch_sw_cons_worker(l3_code: str) -> Dict[str, Any]:
    """Worker to fetch constituents for an L3 industry (Running in Thread)"""
    try:
        df = ak.sw_index_third_cons(symbol=l3_code)
        if df is None or df.empty:
             return {"l3_code": l3_code, "stocks": []}
        
        stocks = []
        for _, row in df.iterrows():
            stocks.append(row['股票代码'])
        return {"l3_code": l3_code, "stocks": stocks}
    except Exception as e:
        return {"l3_code": l3_code, "stocks": [], "error": str(e)}

class MetadataService:
    def __init__(self):
        # Use ThreadPoolExecutor instead of ProcessPool to save memory
        # 128MB is tight for multiple Python processes
        self.pool = ThreadPoolExecutor(max_workers=2)

    async def sync_stock_list(self):
        """Sync full A-share stock list to stock_basic_info"""
        logger.info("Starting Stock List Sync...")
        try:
            # 1. Fetch from AkShare (Try multiple methods)
            df = None
            # Method A: spot_em (Comprehensive but heavy)
            try:
                # We need some stock list, even if incomplete.
                # Try simple info first as it's more stable
                df = await asyncio.to_thread(ak.stock_info_a_code_name)
            except Exception as e:
                logger.warning(f"Failed to fetch stock_info_a_code_name: {e}")
                
            if df is None or df.empty:
                # Fallback to spot_em
                try:
                    df = await asyncio.to_thread(ak.stock_zh_a_spot_em)
                except Exception as e:
                    logger.error(f"Failed to fetch stock_zh_a_spot_em: {e}")
            
            if df is None or df.empty:
                return {"status": "error", "message": "Could not fetch stock list from AkShare"}

            logger.info(f"Fetched {len(df)} stocks from AkShare.")
            
            # 2. Prepare for DB
            db_rows = []
            for _, row in df.iterrows():
                # stock_info_a_code_name returns: code, name
                # stock_zh_a_spot_em returns: 代码, 名称
                code = row.get('code', row.get('代码'))
                name = row.get('name', row.get('名称'))
                
                if not code or not name: continue
                
                # Format to TS_CODE
                ts_code = code
                if len(code) == 6:
                    if code.startswith(('6', '9', '688')): ts_code = f"{code}.SH"
                    elif code.startswith(('0', '3')): ts_code = f"{code}.SZ"
                    elif code.startswith(('4', '8')): ts_code = f"{code}.BJ"
                
                # Basic info
                market = "主板"
                if code.startswith('688'): market = "科创板"
                elif code.startswith('30'): market = "创业板"
                elif code.startswith(('4', '8')): market = "北交所"
                
                db_rows.append((ts_code, code, name, market, "L")) # L for Listed
            
            # 3. Upsert
            sql = """
            INSERT INTO stock_basic_info (ts_code, symbol, name, market, list_status)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                name=VALUES(name), 
                market=VALUES(market),
                list_status=VALUES(list_status)
            """
            
            batch_size = 500
            for i in range(0, len(db_rows), batch_size):
                await db.execute_many(sql, db_rows[i:i+batch_size])
                
            logger.info(f"Stock List Sync completed. Synced {len(db_rows)} stocks.")
            return {"status": "success", "synced": len(db_rows)}
            
        except Exception as e:
            logger.error(f"Stock List Sync Failed: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    async def sync_issue_prices(self):
        """Sync Issue Price for all stocks missing it"""
        logger.info("Starting Issue Price Sync (ThreadPool Mode)...")
        
        # 1. Get stocks with missing issue_price
        try:
            rows = await db.execute("SELECT ts_code FROM stock_basic_info WHERE issue_price IS NULL")
            if not rows:
                logger.info("No stocks missing issue_price.")
                return {"status": "success", "message": "No updates needed"}
                
            symbols = [r[0] for r in rows]
            logger.info(f"Found {len(symbols)} stocks missing issue_price")
            
            # 2. Process in chunks
            chunk_size = 20  # Smaller chunk size
            updated_count = 0
            
            loop = asyncio.get_running_loop()
            
            for i in range(0, len(symbols), chunk_size):
                chunk = symbols[i:i+chunk_size]
                tasks = []
                for sym in chunk:
                    tasks.append(loop.run_in_executor(self.pool, fetch_ipo_info_worker, sym))
                
                results = await asyncio.gather(*tasks)
                
                # Prepare updates
                updates = []
                for res in results:
                    if res.get("price") is not None:
                        updates.append((res["price"], res["symbol"]))
                
                if updates:
                    await db.execute_many("UPDATE stock_basic_info SET issue_price=%s WHERE ts_code=%s", updates)
                    updated_count += len(updates)
                
                # Report progress
                if (i + len(chunk)) % 100 == 0:
                    logger.info(f"Progress: {i + len(chunk)}/{len(symbols)}. Updated so far: {updated_count}")
                    gc.collect() # Force GC to release memory from DataFrames
                
                # Rate limiting and yield to event loop
                await asyncio.sleep(0.5)

            logger.info(f"Issue Price Sync Completed. Updated {updated_count} records.")
            return {"status": "success", "updated": updated_count}
        except Exception as e:
            logger.error(f"Issue Price Sync Failed: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    async def sync_shenwan_industries(self):
        """Sync Shenwan Level 1/2/3 Industries"""
        logger.info("Starting Shenwan Industry Sync (ThreadPool Mode)...")
        loop = asyncio.get_running_loop()

        # 1. Fetch Industry Metadata (L1, L2, L3)
        try:
            # L1
            df_l1 = await asyncio.to_thread(ak.sw_index_first_info)
            l1_map = {row['行业名称']: row['行业代码'] for _, row in df_l1.iterrows()}
            
            # L2
            df_l2 = await asyncio.to_thread(ak.sw_index_second_info)
            l2_map = {}
            for _, row in df_l2.iterrows():
                l2_map[row['行业名称']] = {
                    "code": row['行业代码'],
                    "parent_name": row['上级行业']
                }

            # L3
            df_l3 = await asyncio.to_thread(ak.sw_index_third_info)
            l3_info = {}
            for _, row in df_l3.iterrows():
                l3_code = row['行业代码']
                l3_name = row['行业名称']
                l2_name = row['上级行业']
                
                l2_node = l2_map.get(l2_name)
                if not l2_node:
                    continue
                    
                l2_code = l2_node["code"]
                l1_name = l2_node["parent_name"]
                l1_code = l1_map.get(l1_name)
                
                l3_info[l3_code] = {
                    "l3_name": l3_name,
                    "l2_code": l2_code,
                    "l2_name": l2_name,
                    "l1_code": l1_code,
                    "l1_name": l1_name
                }
            
            logger.info(f"Prepared Metadata: {len(l1_map)} L1, {len(l2_map)} L2, {len(l3_info)} L3 industries")
            
            # release memory
            del df_l1, df_l2, df_l3, l1_map, l2_map
            gc.collect()

            # 2. Fetch Constituents for each L3
            l3_codes = list(l3_info.keys())
            stock_mapping = {} 
            
            chunk_size = 10 
            for i in range(0, len(l3_codes), chunk_size):
                chunk = l3_codes[i:i+chunk_size]
                tasks = []
                for code in chunk:
                    tasks.append(loop.run_in_executor(self.pool, fetch_sw_cons_worker, code))
                
                results = await asyncio.gather(*tasks)
                
                for res in results:
                    l3_c = res["l3_code"]
                    stocks = res["stocks"]
                    meta = l3_info[l3_c]
                    
                    for stock in stocks:
                        fmt_code = stock
                        if len(stock) == 6:
                            if stock.startswith(("6", "9", "11")): fmt_code = f"{stock}.SH"
                            elif stock.startswith(("0", "3")): fmt_code = f"{stock}.SZ"
                            elif stock.startswith(("4", "8")): fmt_code = f"{stock}.BJ"
                        
                        stock_mapping[fmt_code] = {
                            "code": fmt_code,
                            "l1_code": meta["l1_code"],
                            "l1_name": meta["l1_name"],
                            "l2_code": meta["l2_code"],
                            "l2_name": meta["l2_name"],
                            "l3_code": l3_c,
                            "l3_name": meta["l3_name"]
                        }
                
                if (i + len(chunk)) % 50 == 0:
                    logger.info(f"Processed {i + len(chunk)}/{len(l3_codes)} L3 industries")
                    gc.collect()
                await asyncio.sleep(0.5)

            # 3. Batch Insert
            logger.info(f"Upserting {len(stock_mapping)} stock industry records...")
            
            db_rows = []
            for s in stock_mapping.values():
                db_rows.append((
                    s["code"],
                    s["l1_code"], s["l1_name"],
                    s["l2_code"], s["l2_name"],
                    s["l3_code"], s["l3_name"]
                ))
            
            sql = """
            INSERT INTO stock_industry_sw 
            (code, l1_code, l1_name, l2_code, l2_name, l3_code, l3_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            l1_code=VALUES(l1_code), l1_name=VALUES(l1_name),
            l2_code=VALUES(l2_code), l2_name=VALUES(l2_name),
            l3_code=VALUES(l3_code), l3_name=VALUES(l3_name)
            """
            
            for i in range(0, len(db_rows), 500):
                await db.execute_many(sql, db_rows[i:i+500])
                
            return {"status": "success", "count": len(stock_mapping)}

        except Exception as e:
            logger.error(f"Shenwan Sync Failed: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    async def sync_em_industries(self):
        """Sync EastMoney Industries (Board Name + Constituents)"""
        logger.info("Starting EastMoney Industry Sync...")
        try:
            # 1. Fetch Board List
            df_boards = await asyncio.to_thread(ak.stock_board_industry_name_em)
            if df_boards is None or df_boards.empty:
                logger.error("Failed to fetch EastMoney industry list.")
                return {"status": "error", "message": "Empty board list"}

            total_boards = len(df_boards)
            logger.info(f"Found {total_boards} EastMoney industries. Fetching constituents...")
            
            loop = asyncio.get_running_loop()
            
            # Prepare SQL for batch insert
            sql = """
            INSERT INTO stock_industry_em (ts_code, industry_code, industry_name)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                industry_name=VALUES(industry_name)
            """
            
            batch_records = []
            total_synced = 0
            
            # 2. Iterate each board to get constituents
            for idx, row in df_boards.iterrows():
                board_name = row['板块名称']
                board_code = row['板块代码'] 
                
                try:
                    # Fetch constituents
                    df_cons = await loop.run_in_executor(
                        self.pool, 
                        lambda: ak.stock_board_industry_cons_em(symbol=board_name)
                    )
                    
                    if df_cons is not None and not df_cons.empty:
                        # columns: 代码, 名称 ...
                        for _, c_row in df_cons.iterrows():
                            raw_code = str(c_row['代码']).zfill(6)
                            ts_code = raw_code
                            if raw_code.startswith(('6', '9', '688')): ts_code = f"{raw_code}.SH"
                            elif raw_code.startswith(('0', '3')): ts_code = f"{raw_code}.SZ"
                            elif raw_code.startswith(('4', '8')): ts_code = f"{raw_code}.BJ"
                            
                            batch_records.append((ts_code, board_code, board_name))
                    
                    if (idx + 1) % 5 == 0:
                        logger.info(f"Fetched {idx+1}/{total_boards} industries")
                    
                except Exception as e:
                    logger.warning(f"Failed to fetch constituents for {board_name}: {e}")
                
                # Check batch size and insert
                if len(batch_records) >= 200:
                    await db.execute_many(sql, batch_records)
                    total_synced += len(batch_records)
                    batch_records = []
                    logger.info(f"Synced {total_synced} records so far...")

                # Polite delay (increased to reduce connection drops)
                await asyncio.sleep(2.0)
                
            # Insert remaining
            if batch_records:
                await db.execute_many(sql, batch_records)
                total_synced += len(batch_records)
            
            logger.info(f"EastMoney Industry Sync Completed. Total records: {total_synced}")
            return {"status": "success", "count": total_synced}
            
        except Exception as e:
            logger.error(f"EM Industry Sync Failed: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    async def _query_wencai(self, query: str, perpage: int = 100, loop: bool = True):
        """Helper to query pywencai-api"""
        import httpx
        url = "http://pywencai-api:8000/api/v1/query"
        payload = {"q": query, "perpage": perpage, "loop": loop}
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                logger.error(f"PyWencai API error: {resp.status_code} - {resp.text}")
                return None
            return resp.json()

    def _format_ths_code(self, raw_code: str) -> str:
        """Format raw code to TS_CODE"""
        if not raw_code: return ""
        if "." in raw_code: return raw_code
        if raw_code.startswith(('6', '9', '688')): return f"{raw_code}.SH"
        if raw_code.startswith(('0', '3')): return f"{raw_code}.SZ"
        if raw_code.startswith(('4', '8')): return f"{raw_code}.BJ"
        return raw_code

    async def sync_ths_sectors(self):
        """Standard THS Sector Sync (Two-Phase Strategy)"""
        logger.info("Starting THS Sector Sync (Two-Phase)...")
        try:
            # 1. Sync Hierarchy Industries
            await self._sync_ths_hierarchy_industry()
            # 2. Sync Concepts
            await self._sync_ths_concepts()
            
            logger.info("THS Sector Sync (Two-Phase) Completed.")
            return {"status": "success", "message": "Standard sync completed"}
        except Exception as e:
            logger.error(f"THS Sector Sync Failed: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    async def _sync_ths_hierarchy_industry(self):
        """Phase 1: Discover Industries & Concepts, Phase 2: Iterate Constituents"""
        logger.info("Discovering THS Sectors (Industries & Concepts)...")
        # Step 1: Discovery via general query
        discovery_q = "所有股票;所属同花顺行业;所属概念"
        res = await self._query_wencai(discovery_q, perpage=200, loop=True)
        if not res or not res.get("data"):
            logger.error("Failed to discover sectors")
            return
            
        cols = res.get("columns", [])
        code_idx = next((i for i, c in enumerate(cols) if "代码" in c), 0)
        ind_idx = next((i for i, c in enumerate(cols) if "所属同花顺行业" in c), -1)
        conc_idx = next((i for i, c in enumerate(cols) if "所属概念" in c), -1)
        
        # Discover unique L1, L2, L3 and Concepts
        l1_set, l2_set, l3_set = set(), set(), set()
        conc_set = set()
        
        industry_batch = []
        logger.info(f"Processing {len(res['data'])} stock records for discovery...")
        for row in res["data"]:
            ts_code = self._format_ths_code(str(row[code_idx]))
            
            # Industries
            if ind_idx != -1:
                raw_ind = str(row[ind_idx])
                if raw_ind and raw_ind != "None":
                    parts = [p.strip() for p in raw_ind.split("-")]
                    l1 = parts[0] if len(parts) >= 1 else None
                    l2 = parts[1] if len(parts) >= 2 else None
                    l3 = parts[2] if len(parts) >= 3 else None
                    if l1: l1_set.add(l1)
                    if l2: l2_set.add(l2)
                    if l3: l3_set.add(l3)
                    industry_batch.append((ts_code, l1, l2, l3))
            
            # Concepts (Just collect names here)
            if conc_idx != -1:
                raw_conc = str(row[conc_idx])
                if raw_conc and raw_conc != "None":
                    concs = [c.strip() for c in raw_conc.split(";")]
                    for c in concs:
                        if c: conc_set.add(c)
            
        # Bulk Seed Industry Info
        if industry_batch:
            logger.info(f"Bulk seeding {len(industry_batch)} industry records...")
            sql_ind = """
                INSERT INTO stock_industry_ths (ts_code, l1_name, l2_name, l3_name) 
                VALUES (%s, %s, %s, %s) 
                ON DUPLICATE KEY UPDATE l1_name=VALUES(l1_name), l2_name=VALUES(l2_name), l3_name=VALUES(l3_name)
            """
            for i in range(0, len(industry_batch), 1000):
                await db.execute_many(sql_ind, industry_batch[i:i+1000])
                
        logger.info(f"Discovered: L1={len(l1_set)}, L2={len(l2_set)}, L3={len(l3_set)}, Concepts={len(conc_set)}")
        
        # Bulk Seed Sector Dictionary (Concepts)
        if conc_set:
            logger.info(f"Seeding {len(conc_set)} concept names to dictionary...")
            for name in conc_set:
                await db.execute(
                    "INSERT IGNORE INTO stock_sector_ths (sector_name, sector_type) VALUES (%s, %s)",
                    (name, 'concept')
                )
        
        # Optimized Concept Seeding (Bulk Mapping)
        logger.info("Bulk seeding concept mapping from discovery...")
        # Get name -> id map
        rows = await db.execute("SELECT sector_name, id FROM stock_sector_ths WHERE sector_type='concept'")
        name_to_id = {r[0]: r[1] for r in rows}
        
        batch_cons = []
        for row in res["data"]:
            ts_code = self._format_ths_code(str(row[code_idx]))
            raw_conc = str(row[conc_idx]) if conc_idx != -1 else None
            if raw_conc and raw_conc != "None":
                concs = [c.strip() for c in raw_conc.split(";")]
                for c in concs:
                    if c in name_to_id:
                        batch_cons.append((ts_code, name_to_id[c]))
                        
        if batch_cons:
            logger.info(f"Bulk inserting {len(batch_cons)} concept mappings...")
            for i in range(0, len(batch_cons), 1000):
                await db.execute_many(
                    "INSERT IGNORE INTO stock_sector_cons_ths (ts_code, sector_id) VALUES (%s, %s)",
                    batch_cons[i:i+1000]
                )
            logger.info("Concept mapping seed completed.")
        
        # Save discovered sets for concept sync
        self._last_discovered_concepts = list(conc_set)
        
        # Step 2: Iterate each industry sector and sync (Deep Dive)
        levels = [("一级", l1_set, "l1_name"), ("二级", l2_set, "l2_name"), ("三级", l3_set, "l3_name")]
        for label, names, db_col in levels:
            logger.info(f"Refining constituents for {len(names)} {label} industries...")
            for name in names:
                # 记录板块字典
                await db.execute(
                    "INSERT IGNORE INTO stock_sector_ths (sector_name, sector_type, sector_level) VALUES (%s, %s, %s)",
                    (name, 'industry', label)
                )
                
                # 查询成分股 (深挖)
                q_cons = f"{name}行业成分股"
                res_cons = await self._query_wencai(q_cons, perpage=200, loop=True)
                if not res_cons or not res_cons.get("data"): continue
                
                cons_cols = res_cons.get("columns", [])
                c_idx = next((i for i, c in enumerate(cons_cols) if "代码" in c), -1)
                if c_idx == -1: continue
                
                batch_data = []
                for r in res_cons["data"]:
                    t_code = self._format_ths_code(str(r[c_idx]))
                    batch_data.append((t_code, name))
                
                if batch_data:
                    sql = f"INSERT INTO stock_industry_ths (ts_code, {db_col}) VALUES (%s, %s) ON DUPLICATE KEY UPDATE {db_col}=VALUES({db_col})"
                    await db.execute_many(sql, batch_data)
                    
                await asyncio.sleep(1)

    async def _sync_ths_concepts(self):
        """Phase 2 for Concept Sectors"""
        concepts = getattr(self, "_last_discovered_concepts", [])
        if not concepts:
            logger.warning("No discovered concepts to sync. Run industry discovery first?")
            return
            
        logger.info(f"Syncing constituents for {len(concepts)} concepts...")
        
        for name in concepts:
            # 记录板块字典并获取 ID
            await db.execute(
                "INSERT IGNORE INTO stock_sector_ths (sector_name, sector_type) VALUES (%s, %s)",
                (name, 'concept')
            )
            # 获取 ID
            rows = await db.execute("SELECT id FROM stock_sector_ths WHERE sector_name=%s AND sector_type='concept'", (name,))
            if not rows: continue
            sector_id = rows[0][0]
            
            # 查询成分股 (深挖)
            q_cons = f"{name}成分股"
            res_cons = await self._query_wencai(q_cons, perpage=200, loop=True)
            if not res_cons or not res_cons.get("data"): continue
            
            cons_cols = res_cons.get("columns", [])
            code_idx = next((i for i, c in enumerate(cons_cols) if "代码" in c), -1)
            if code_idx == -1: continue
            
            batch_data = []
            for r in res_cons["data"]:
                ts_code = self._format_ths_code(str(r[code_idx]))
                batch_data.append((ts_code, sector_id))
            
            if batch_data:
                sql = "INSERT IGNORE INTO stock_sector_cons_ths (ts_code, sector_id) VALUES (%s, %s)"
                await db.execute_many(sql, batch_data)
                
            await asyncio.sleep(1)

    async def sync_ths_industries(self, mode: str = "standard"):
        """Sync THS Industries (Wrapper)
        
        Args:
            mode: "standard" for two-phase sync, "fast" for single query backup
        """
        if mode == "fast":
            return await self.sync_ths_industries_fast()
        return await self.sync_ths_sectors()

    async def sync_ths_industries_fast(self):
        """Sync THS Industries via Single Query (Backup Method)"""
        logger.info("Starting THS Industry Sync (Fast Method)...")
        
        try:
            # 1. Call PyWencai API
            import httpx
            query_text = "所有股票;同花顺一级行业;同花顺二级行业;同花顺三级行业"
            url = "http://pywencai-api:8000/api/v1/query"
            payload = {
                "q": query_text,
                "perpage": 100,
                "loop": True
            }
            
            logger.info(f"Querying PyWencai: {query_text} (Target: {url})")
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, json=payload)
                
                if resp.status_code != 200:
                    logger.error(f"PyWencai API error: {resp.status_code} - {resp.text}")
                    return {"status": "error", "message": f"PyWencai API Error: {resp.status_code}"}
                
                res_json = resp.json()
            
            # 2. Parse Data
            # Result structure from wencai_service: {"columns": [...], "data": [[...], ...]}
            # Note: The data might be a list of lists.
            
            columns = res_json.get("columns", [])
            data = res_json.get("data", [])
            
            if not data:
                logger.warning(f"No data returned from PyWencai for query: {query_text}")
                return {"status": "warning", "message": "No data found"}
                
            logger.info(f"Got {len(data)} rows from PyWencai. Processing...")
            
            # Map column names to indices
            # Expected columns like: '股票代码', '同花顺一级行业', '同花顺二级行业', '同花顺三级行业'
            # Or variations like '所属同花顺行业(一级)' etc.
            
            # Helper to find column index fuzzy
            def find_col_idx(cols, keywords):
                for idx, col_name in enumerate(cols):
                    if all(k in col_name for k in keywords):
                        return idx
                return None
            
            code_idx = find_col_idx(columns, ["代码"])
            l1_idx = find_col_idx(columns, ["一级"])
            l2_idx = find_col_idx(columns, ["二级"])
            l3_idx = find_col_idx(columns, ["三级"])
            
            if code_idx is None:
                logger.error(f"Missing stock code column. Available: {columns}")
                return {"status": "error", "message": "Missing code column"}

            db_rows = []
            valid_count = 0
            
            for row in data:
                # Get values
                # data is list of lists
                if len(row) <= code_idx: continue
                
                raw_code = str(row[code_idx])
                if not raw_code: continue
                
                # Format Code to TS_CODE (e.g. 600519.SH)
                ts_code = raw_code
                if "." not in raw_code:
                    if raw_code.startswith(('6', '9', '688')): ts_code = f"{raw_code}.SH"
                    elif raw_code.startswith(('0', '3')): ts_code = f"{raw_code}.SZ"
                    elif raw_code.startswith(('4', '8')): ts_code = f"{raw_code}.BJ"
                
                l1 = row[l1_idx] if l1_idx is not None and len(row) > l1_idx else None
                l2 = row[l2_idx] if l2_idx is not None and len(row) > l2_idx else None
                l3 = row[l3_idx] if l3_idx is not None and len(row) > l3_idx else None
                
                # Clean up None or "nan" or empty strings
                if l1 in ["None", "nan", ""]: l1 = None
                if l2 in ["None", "nan", ""]: l2 = None
                if l3 in ["None", "nan", ""]: l3 = None
                
                # We need at least one industry level to be useful, but let's store whatever we have
                db_rows.append((ts_code, l1, l2, l3))
                valid_count += 1
            
            logger.info(f"Prepared {len(db_rows)} records for insertion.")
            
            # 3. Batch Insert
            # Schema: ts_code, l1_name, l2_name, l3_name
            
            sql = """
            INSERT INTO stock_industry_ths (ts_code, l1_name, l2_name, l3_name)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                l1_name=VALUES(l1_name),
                l2_name=VALUES(l2_name),
                l3_name=VALUES(l3_name)
            """
            
            # Execute in batches of 500
            for i in range(0, len(db_rows), 500):
                batch = db_rows[i:i+500]
                await db.execute_many(sql, batch)
                
            logger.info(f"THS Industry Sync Completed. Updated {valid_count} records.")
            return {"status": "success", "count": valid_count}

        except Exception as e:
            logger.error(f"THS Sync Failed: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

