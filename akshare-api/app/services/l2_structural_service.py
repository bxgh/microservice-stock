import asyncio
import logging
import datetime
from typing import Dict, Any, List, Optional
from app.utils.database import db
from app.services.akshare_service import AkShareService

logger = logging.getLogger("akshare-api.structural")

class L2StructuralService:
    def __init__(self):
        self.ak_service = AkShareService()

    async def sync_sw_index_daily(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """同步申万行业指数日线及估值 (一级+二级)"""
        if not start_date:
            start_date = datetime.date.today().strftime("%Y%m%d")
        if not end_date:
            end_date = start_date
            
        logger.info(f"开始同步申万指数分析: {start_date} ~ {end_date}")
        
        counts = {"l1": 0, "l2": 0}
        
        try:
            # 1. 同步一级行业
            l1_data = await self.ak_service.get_sw_index_analysis("一级行业", start_date, end_date)
            if l1_data:
                await self._save_sw_to_db(l1_data, "l1")
                counts["l1"] = len(l1_data)
            
            await asyncio.sleep(1) # 避开频率限制
            
            # 2. 同步二级行业
            l2_data = await self.ak_service.get_sw_index_analysis("二级行业", start_date, end_date)
            if l2_data:
                await self._save_sw_to_db(l2_data, "l2")
                counts["l2"] = len(l2_data)

            await asyncio.sleep(1)
            
            # 3. 同步风格指数 (Chapter 2 新增)
            style_data = await self.ak_service.get_sw_index_analysis("风格指数", start_date, end_date)
            if style_data:
                await self._save_sw_to_db(style_data, "style")
                counts["style"] = len(style_data)
                
            return {"status": "success", "counts": counts}
        except Exception as e:
            logger.error(f"同步申万指数失败: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    async def sync_concept_kline_daily(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """同步同花顺概念板块行情"""
        if not start_date:
            start_date = datetime.date.today().strftime("%Y%m%d")
        if not end_date:
            end_date = start_date
            
        logger.info(f"开始同步概念板块行情: {start_date} ~ {end_date}")
        
        try:
            # 1. 获取最新概念名单
            concepts = await self.ak_service.get_concept_name_ths()
            if not concepts:
                return {"status": "error", "message": "无法获取概念名单"}
            
            success_count = 0
            # 2. 逐个同步板块行情
            # 注意: 为防止封禁，采用严格的串行模式和休眠
            for i, concept in enumerate(concepts):
                name = concept["name"]
                code = concept["code"]
                
                try:
                    data = await self.ak_service.get_concept_index_ths(name, start_date, end_date)
                    if data:
                        await self._save_concept_to_db(code, name, data)
                        success_count += 1
                    
                    if (i + 1) % 10 == 0:
                        logger.info(f"概念同步进度: {i+1}/{len(concepts)}")
                    
                    # 严格频率控制: 2秒
                    await asyncio.sleep(2.0)
                    
                    # 强制垃圾回收，释放 DataFrame 占用的内存
                    import gc
                    gc.collect()
                    
                except Exception as e:
                    logger.warning(f"同步概念 {name} 失败: {e}")
                    
            return {"status": "success", "total": len(concepts), "success": success_count}
        except Exception as e:
            logger.error(f"同步概念行情任务异常: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    async def _save_sw_to_db(self, data: List[Dict[str, Any]], level: str):
        """保存申万数据到 ODS"""
        cols = [
            "trade_date", "ts_code", "name", "level", "close", "pct_chg", 
            "vol", "amount", "pe_ttm", "pb", "dv_ratio"
        ]
        db_rows = []
        for item in data:
            db_rows.append((
                item.get("date"), item.get("code"), item.get("name"), level,
                item.get("close"), item.get("pct_chg"), item.get("vol"), 
                item.get("amount"), item.get("pe"), item.get("pb"), item.get("dv_ratio")
            ))
            
        sql = f"""
        INSERT INTO ods_sw_index_daily ({", ".join(cols)})
        VALUES ({", ".join(["%s"]*len(cols))})
        ON DUPLICATE KEY UPDATE 
        """ + ", ".join([f"{c}=VALUES({c})" for c in cols[2:]])
        await db.execute_many(sql, db_rows)

    async def _save_concept_to_db(self, code: str, name: str, data: List[Dict[str, Any]]):
        """保存概念数据到 ODS"""
        cols = [
            "trade_date", "concept_code", "concept_name", "open", "high", 
            "low", "close", "pct_chg", "amount"
        ]
        db_rows = []
        for item in data:
            db_rows.append((
                item.get("date"), code, name, item.get("open"), item.get("high"),
                item.get("low"), item.get("close"), item.get("pct_chg"), item.get("amount")
            ))
            
        sql = f"""
        INSERT INTO ods_concept_kline_daily ({", ".join(cols)})
        VALUES ({", ".join(["%s"]*len(cols))})
        ON DUPLICATE KEY UPDATE 
        """ + ", ".join([f"{c}=VALUES({c})" for c in cols[3:]])
        await db.execute_many(sql, db_rows)
