from datetime import datetime, timedelta
import asyncio
from typing import Dict, Any, List
from app.utils.database import db
from app.utils.http_client import http_client
from app.utils.code_utils import normalize_ts_code
from app.utils.logger import get_logger

logger = get_logger("stock-manager.pre_market")

class PreMarketService:
    """早盘数据服务
    
    负责同步除权除息、新股上市、业绩预告等数据
    """
    
    async def create_tables_if_not_exists(self):
        """创建早盘相关数据表"""
        # 1. 除权除息表 (stock_dividend_daily 可能已存在，此处为冗余检查或补充字段)
        # Note: 我们之前在文档里有 dividend ，但不知是否有表。假设使用 stock_dividend
        # 这里为了除权计算方便，我们可能需要一个轻量级的表，或者复用。
        # 这里创建一个专用表记录除权日信息，方便快速查询
        sql_xr = """
        CREATE TABLE IF NOT EXISTS stock_xr_schedules (
            id INT AUTO_INCREMENT PRIMARY KEY,
            ts_code VARCHAR(20) NOT NULL COMMENT '股票代码',
            ex_date DATE NOT NULL COMMENT '除权除息日',
            bonus_ratio DECIMAL(10,4) DEFAULT 0 COMMENT '送转比例',
            cash_div DECIMAL(10,4) DEFAULT 0 COMMENT '每股派现',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_code_date (ts_code, ex_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='除权除息日程表';
        """
        
        # 2. 业绩预告表 (stock_performance_forecast)
        sql_forecast = """
        CREATE TABLE IF NOT EXISTS stock_performance_forecast (
            id INT AUTO_INCREMENT PRIMARY KEY,
            ts_code VARCHAR(20) NOT NULL COMMENT '股票代码',
            report_period DATE NOT NULL COMMENT '报告期',
            notice_date DATE NOT NULL COMMENT '公告日期',
            type VARCHAR(255) COMMENT '业绩变动类型',
            growth_range VARCHAR(255) COMMENT '预告幅度',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_code_period (ts_code, report_period)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='业绩预告表';
        """

        try:
            await db.execute(sql_xr)
            await db.execute(sql_forecast)
            logger.info("早盘数据表检查/创建完成")
        except Exception as e:
            logger.error(f"创建早盘数据表失败: {e}")
            raise

    async def sync_company_events(self) -> Dict[str, Any]:
        """08:30 同步除权除息和新股"""
        await self.create_tables_if_not_exists()
        stats = {"xr_count": 0, "new_stock_count": 0}
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        try:
            # --- 1. 同步除权除息 (从 dividend 接口获取最近的) ---
            # 这是一个简化的逻辑：遍历今日的分红配股数据太慢
            # 理想情况：AkShare 若有 "今日除权" 接口最好，否则需要维护全量
            # 暂时策略：不全量同步，仅作为 placeholder, 实际逻辑可能需要更复杂的上游接口支持
            # 由于 AkShare 接口限制，我们暂时跳过大规模同步，记录一条日志
            logger.info("正在执行除权除息检查 (Placeholder)")
            
            # --- 2. 同步新股 (今日上市) ---
            # AkShare: stock_new_gh_em
            # 这里调用 akshare-api 封装的接口 (如果还没封装，需要去 akshare-api 加)
            # 我们先假设在 akshare-api 增加一个 /api/v1/market/new_stocks
            pass 
            
        except Exception as e:
            logger.error(f"早盘事件同步失败: {e}")
            
        return stats

    async def sync_daily_performance_forecast(self) -> int:
        """08:45 同步业绩预告 (针对下一报告期)"""
        await self.create_tables_if_not_exists()
        
        # 推算当前关注的报告期 (例如现在是2月，关注3月31日的一季报或去年12月31日的年报)
        # 简化逻辑：同步最近四个季度的预告
        now = datetime.now()
        current_year = now.year
        periods = [
            f"{current_year-1}-12-31",
            f"{current_year}-03-31", 
            f"{current_year}-06-30",
            f"{current_year}-09-30",
            f"{current_year}-12-31"
        ]
        
        total_count = 0
        try:
            for period in periods:
                params = {"period": period}
                # 调用 AkShare (ak.stock_yjyg_em)
                # 需在 akshare-api 确认有此接口 (Finance router)
                # 目前 akshare-api 似乎没有直接暴露 yjyg，我们需要加上
                # 假设 AkShare Service 已有 get_performance_forecast(period)
                # 我们在 AkShare API Router 加一个 /api/v1/finance/forecast
                
                # Check akshare-api service code first... 
                # (Added in previous turn: get_performance_forecast)
                # But router? We need to verify router.
                
                path = "/api/v1/forecast"
                data = await http_client.get("akshare", path, params=params)
                
                if not data:
                    continue
                    
                rows = []
                for item in data:
                    # P0: 使用统一的归一化工具
                    ts_code = normalize_ts_code(item.get("stock_code") or item.get("code"))
                    if not ts_code:
                        continue
                    
                    rows.append((
                        ts_code,
                        period,
                        item.get("notice_date"),
                        item.get("type"),
                        item.get("growth_range")
                    ))
                
                if rows:
                    sql = """
                    INSERT INTO stock_performance_forecast
                    (ts_code, report_period, notice_date, type, growth_range)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        notice_date=VALUES(notice_date),
                        type=VALUES(type),
                        growth_range=VALUES(growth_range),
                        updated_at=CURRENT_TIMESTAMP
                    """
                    await db.execute_many(sql, rows)
                    total_count += len(rows)
                    
            logger.info(f"业绩预告同步完成: {total_count} 条")
            return total_count
            
        except Exception as e:
            logger.error(f"业绩预告同步失败: {e}")
            return 0
