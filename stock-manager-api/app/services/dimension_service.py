import httpx
import datetime
from app.utils.database import db
from app.utils.logger import get_logger
from app.config import settings

logger = get_logger("stock-manager.dimension")

class DimensionService:
    def __init__(self):
        self.tushare_url = settings.TUSHARE_API_URL

    async def sync_stock_status(self, trade_date: str = ''):
        """同步股票状态 (Story E5-S1)
        逻辑:
        1. 获取当日所有股票代码
        2. 获取当日停牌信息 -> is_suspended
        3. 获取当日 ST 信息 (通过 name 中的 'ST' 标记或专门接口)
        4. 获取上市日期判断是否为新股 -> is_new
        """
        if not trade_date:
            trade_date = datetime.date.today().strftime("%Y-%m-%d")
        
        logger.info(f"开始同步股票状态: {trade_date}")
        
        # 1. 获取基础信息 (ts_code, name, list_date)
        sql_basic = "SELECT ts_code, name, list_date, market FROM stock_basic_info"
        basic_info = await db.execute(sql_basic)
        if not basic_info:
            logger.warning("未获取到基础证券信息")
            return
            
        # 2. 获取停牌信息
        sql_suspend = "SELECT ts_code FROM dim_stock_suspend WHERE suspend_date = %s"
        suspend_res = await db.execute(sql_suspend, (trade_date,))
        suspended_codes = {r[0] for r in suspend_res}
        
        # 3. 准备写入数据
        trade_date_obj = datetime.datetime.strptime(trade_date, "%Y-%m-%d").date()
        insert_args = []
        for ts_code, name, list_date, market in basic_info:
            is_st = 1 if 'ST' in name.upper() else 0
            is_suspended = 1 if ts_code in suspended_codes else 0
            
            # 判断新股 (上市 N 日内，此处定义为 5 个交易日，简化为 7 个自然日)
            is_new = 1 if list_date and (trade_date_obj - list_date).days <= 7 else 0
            
            # 状态枚举
            status = 'NORMAL'
            if is_suspended: status = 'SUSPEND'
            elif is_st: status = 'ST'
            elif is_new: status = 'NEW'
            
            insert_args.append((
                ts_code, trade_date, status, is_st, is_suspended, is_new
            ))
            
        query = """
            INSERT INTO dim_stock_status (
                ts_code, trade_date, status, is_st, is_suspended, is_new
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            status=VALUES(status), is_st=VALUES(is_st), 
            is_suspended=VALUES(is_suspended), is_new=VALUES(is_new)
        """
        await db.execute_many(query, insert_args)
        logger.info(f"股票状态同步完成: {len(insert_args)} 条")

    async def sync_corporate_actions(self, ts_code: str = ''):
        """同步除权除息流水 (Story E5-S1)"""
        try:
            logger.info(f"正在同步除权除息数据: {ts_code if ts_code else '全市场'}")
            url = f"{self.tushare_url}/api/v1/dividend"
            params = {"ts_code": ts_code}
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json().get("data", [])
            
            if not data:
                return 0
                
            query = """
                INSERT INTO dim_corporate_action (
                    ts_code, ann_date, record_date, ex_date, pay_date,
                    div_cash, stk_div, stk_add, event_type
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                ann_date=VALUES(ann_date), record_date=VALUES(record_date),
                pay_date=VALUES(pay_date), div_cash=VALUES(div_cash),
                stk_div=VALUES(stk_div), stk_add=VALUES(stk_add)
            """
            args = []
            for i in data:
                # 过滤掉没有除权除息日的数据
                ex_date = i.get("ex_date")
                if not ex_date: continue
                
                ex_date_str = f"{ex_date[:4]}-{ex_date[4:6]}-{ex_date[6:8]}"
                
                def fmt_date(d):
                    return f"{d[:4]}-{d[4:6]}-{d[6:8]}" if d else None

                args.append((
                    i.get("ts_code"), fmt_date(i.get("ann_date")), fmt_date(i.get("record_date")),
                    ex_date_str, fmt_date(i.get("pay_date")),
                    i.get("cash_div_tax"), i.get("stk_div"), i.get("stk_booster"),
                    'DIVIDEND' if i.get("cash_div_tax") else 'SPLIT'
                ))
            
            await db.execute_many(query, args)
            logger.info(f"除权除息同步完成: {len(args)} 条")
            return len(args)
        except Exception as e:
            logger.error(f"同步除权除息失败: {e}")
            raise

    async def generate_daily_price_limits(self, trade_date: str):
        """动态生成当日涨跌幅限制规则 (Story E5-S4)"""
        logger.info(f"开始生成涨跌幅限制: {trade_date}")
        
        # 1. 获取当日股票状态
        sql = """
            SELECT s.ts_code, s.status, s.is_st, s.is_new, b.market
            FROM dim_stock_status s
            JOIN stock_basic_info b ON s.ts_code = b.ts_code
            WHERE s.trade_date = %s
        """
        status_res = await db.execute(sql, (trade_date,))
        if not status_res:
            logger.warning(f"当日 {trade_date} 无股票状态数据，无法生成涨跌幅限制")
            return
            
        insert_args = []
        for ts_code, status, is_st, is_new, market in status_res:
            up_limit, down_limit = 0.10, -0.10
            rule_desc = "主板 10%"
            
            # 规则逻辑
            if market == '科创板' or market == '创业板':
                # 2020-08-24 之后创业板为 20%
                # 简单起见，此处假设系统只处理近期数据或已知日期
                up_limit, down_limit = 0.20, -0.20
                rule_desc = f"{market} 20%"
            elif market == '北交所':
                up_limit, down_limit = 0.30, -0.30
                rule_desc = "北交所 30%"
            else:
                # 主板
                if is_st:
                    up_limit, down_limit = 0.05, -0.05
                    rule_desc = "主板 ST 5%"
            
            # 特殊情况：新股
            if is_new:
                # 注册制新股前 5 日无涨跌幅限制，核准制第一天 44%
                # 此处简化为 1.0 (100% 容差)
                up_limit, down_limit = 1.0, -1.0
                rule_desc = "新股无限制"
                
            insert_args.append((
                ts_code, trade_date, up_limit, down_limit, rule_desc
            ))
            
        query = """
            INSERT INTO dim_price_limit (
                ts_code, trade_date, up_limit_pct, down_limit_pct, rule_desc
            ) VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            up_limit_pct=VALUES(up_limit_pct), down_limit_pct=VALUES(down_limit_pct),
            rule_desc=VALUES(rule_desc)
        """
        await db.execute_many(query, insert_args)
        logger.info(f"涨跌幅限制生成完成: {len(insert_args)} 条")

dimension_service = DimensionService()
