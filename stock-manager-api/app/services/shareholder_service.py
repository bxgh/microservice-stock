from typing import Dict, Any, List, Optional
from datetime import datetime
from app.utils.database import db
from app.utils.http_client import http_client
from app.utils.logger import get_logger

logger = get_logger("stock-manager.shareholder")


class ShareholderService:
    """股东数据同步服务"""
    
    async def fetch_from_akshare(self, code: str, all_history: bool = False) -> Dict[str, Any]:
        """从 akshare-api 获取股东数据
        
        :param code: 股票代码
        :param all_history: 是否获取全量历史数据
        :return: 股东数据字典
        """
        try:
            path = f"/api/v1/shareholder/{code}"
            params = {"all": "true" if all_history else "false"}
            
            data = await http_client.get("akshare", path, params=params)
            logger.info(f"从 akshare-api 获取股东数据成功: code={code}, all={all_history}")
            return data
        except Exception as e:
            logger.error(f"从 akshare-api 获取股东数据失败: code={code}, error={e}")
            raise
    
    async def sync_holder_count(self, code: str, data: List[Dict[str, Any]]) -> int:
        """同步股东户数至数据库
        
        :param code: 股票代码
        :param data: 股东户数历史列表
        :return: 受影响的行数
        """
        if not data:
            logger.info(f"股东户数数据为空: code={code}")
            return 0
        
        sql = """
            INSERT INTO stock_shareholder_count 
            (ts_code, end_date, holder_count, holder_change_pct, avg_market_cap)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                holder_count = VALUES(holder_count),
                holder_change_pct = VALUES(holder_change_pct),
                avg_market_cap = VALUES(avg_market_cap),
                updated_at = CURRENT_TIMESTAMP
        """
        
        rows = []
        for item in data:
            rows.append((
                code,
                item.get("date"),
                item.get("count"),
                item.get("change"),
                item.get("avg_market_cap")
            ))
        
        try:
            await db.execute_many(sql, rows)
            logger.info(f"股东户数同步成功: code={code}, count={len(rows)}")
            return len(rows)
        except Exception as e:
            logger.error(f"股东户数同步失败: code={code}, error={e}")
            raise
    
    async def sync_top10_holders(self, code: str, data: List[Dict[str, Any]]) -> int:
        """同步前十大股东至数据库
        
        :param code: 股票代码
        :param data: 前十大股东列表
        :return: 受影响的行数
        """
        if not data:
            logger.info(f"前十大股东数据为空: code={code}")
            return 0
        
        sql = """
            INSERT INTO stock_top10_shareholders
            (ts_code, end_date, rank, holder_name, share_type, hold_count, hold_pct, change_stat)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                holder_name = VALUES(holder_name),
                share_type = VALUES(share_type),
                hold_count = VALUES(hold_count),
                hold_pct = VALUES(hold_pct),
                change_stat = VALUES(change_stat),
                updated_at = CURRENT_TIMESTAMP
        """
        
        rows = []
        for item in data:
            rows.append((
                code,
                item.get("time"),
                item.get("rank"),
                item.get("holder_name"),
                item.get("share_type"),
                item.get("hold_count"),
                item.get("hold_pct"),
                item.get("change")
            ))
        
        try:
            await db.execute_many(sql, rows)
            logger.info(f"前十大股东同步成功: code={code}, count={len(rows)}")
            return len(rows)
        except Exception as e:
            logger.error(f"前十大股东同步失败: code={code}, error={e}")
            raise
    
    async def sync_single_stock(self, code: str, all_history: bool = False) -> Dict[str, Any]:
        """同步单只股票的股东数据
        
        :param code: 股票代码
        :param all_history: 是否获取全量历史数据
        :return: 同步结果统计
        """
        try:
            # 获取数据
            data = await self.fetch_from_akshare(code, all_history)
            
            # 同步股东户数
            holder_count_data = data.get("holder_count_history", [])
            holder_count_synced = await self.sync_holder_count(code, holder_count_data)
            
            # 同步前十大股东
            top10_data = data.get("top10_holders", [])
            top10_synced = await self.sync_top10_holders(code, top10_data)
            
            result = {
                "code": code,
                "all_history": all_history,
                "holder_count_synced": holder_count_synced,
                "top10_synced": top10_synced,
                "synced_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            logger.info(f"股东数据同步完成: {result}")
            return result
        except Exception as e:
            logger.error(f"股东数据同步失败: code={code}, error={e}")
            raise
    
    async def sync_batch(self, codes: List[str], all_history: bool = False) -> Dict[str, Any]:
        """批量同步股东数据
        
        :param codes: 股票代码列表
        :param all_history: 是否获取全量历史数据
        :return: 批量同步结果
        """
        results = []
        failed = []
        
        for code in codes:
            try:
                result = await self.sync_single_stock(code, all_history)
                results.append(result)
            except Exception as e:
                logger.error(f"批量同步失败: code={code}, error={e}")
                failed.append({"code": code, "error": str(e)})
        
        return {
            "total": len(codes),
            "success": len(results),
            "failed": len(failed),
            "results": results,
            "failures": failed,
            "synced_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    async def get_holder_count_history(self, code: str, limit: int = 100) -> List[Dict[str, Any]]:
        """查询股东户数历史
        
        :param code: 股票代码
        :param limit: 返回记录数
        :return: 股东户数历史列表
        """
        sql = """
            SELECT end_date, holder_count, holder_change_pct, avg_market_cap, updated_at
            FROM stock_shareholder_count
            WHERE ts_code = %s
            ORDER BY end_date DESC
            LIMIT %s
        """
        
        try:
            rows = await db.execute(sql, (code, limit))
            results = []
            for row in rows:
                results.append({
                    "date": row[0].strftime("%Y-%m-%d") if row[0] else None,
                    "count": row[1],
                    "change_pct": float(row[2]) if row[2] else None,
                    "avg_market_cap": float(row[3]) if row[3] else None,
                    "updated_at": row[4].strftime("%Y-%m-%d %H:%M:%S") if row[4] else None
                })
            return results
        except Exception as e:
            logger.error(f"查询股东户数失败: code={code}, error={e}")
            raise
    
    async def get_top10_holders(self, code: str, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """查询前十大股东
        
        :param code: 股票代码
        :param end_date: 截止日期，如果不指定则返回最新一期
        :return: 前十大股东列表
        """
        if end_date:
            sql = """
                SELECT end_date, rank, holder_name, share_type, hold_count, hold_pct, change_stat, updated_at
                FROM stock_top10_shareholders
                WHERE ts_code = %s AND end_date = %s
                ORDER BY rank ASC
            """
            params = (code, end_date)
        else:
            sql = """
                SELECT end_date, rank, holder_name, share_type, hold_count, hold_pct, change_stat, updated_at
                FROM stock_top10_shareholders
                WHERE ts_code = %s AND end_date = (
                    SELECT MAX(end_date) FROM stock_top10_shareholders WHERE ts_code = %s
                )
                ORDER BY rank ASC
            """
            params = (code, code)
        
        try:
            rows = await db.execute(sql, params)
            results = []
            for row in rows:
                results.append({
                    "date": row[0].strftime("%Y-%m-%d") if row[0] else None,
                    "rank": row[1],
                    "holder_name": row[2],
                    "share_type": row[3],
                    "hold_count": row[4],
                    "hold_pct": float(row[5]) if row[5] else None,
                    "change_stat": row[6],
                    "updated_at": row[7].strftime("%Y-%m-%d %H:%M:%S") if row[7] else None
                })
            return results
        except Exception as e:
            logger.error(f"查询前十大股东失败: code={code}, error={e}")
            raise
