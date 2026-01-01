import datetime
from typing import Dict, Any
from app.utils.database import db
from app.utils.logger import get_logger

logger = get_logger("stock-manager.audit")

class AuditService:
    """审计服务"""
    
    async def get_audit_weekly(self, week: str = "current") -> Dict[str, Any]:
        """获取周度审计报告"""
        try:
            if week == "current":
                today = datetime.date.today()
                start_date = today - datetime.timedelta(days=today.weekday())
                week_label = today.strftime("%Y-W%V")
            else:
                try:
                    year_part, week_part = week.split("-W")
                    start_date = datetime.datetime.strptime(f"{year_part}-W{week_part}-1", "%G-W%V-%u").date()
                    week_label = week
                except:
                    raise ValueError("Invalid week format")
            
            end_date = start_date + datetime.timedelta(days=6)
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            
            # 获取交易日历
            sql_cal = "SELECT cal_date, is_open FROM trade_cal WHERE cal_date BETWEEN %s AND %s"
            cal_rows = await db.execute(sql_cal, (start_str, end_str))
            
            # 获取基线：使用最近一个交易日的实际股票数作为基准
            # 这样可以避免代码格式不一致的问题
            sql_baseline = """
                SELECT COUNT(DISTINCT code) 
                FROM stock_kline_daily 
                WHERE trade_date = (
                    SELECT MAX(trade_date) 
                    FROM stock_kline_daily 
                    WHERE trade_date < %s
                )
            """
            baseline_res = await db.execute(sql_baseline, (start_str,))
            total_baseline = baseline_res[0][0] if baseline_res else 5422
            
            # 如果查不到，使用静态基线
            if not total_baseline:
                total_baseline = 5422
                logger.warning(f"无法从K线表获取基线，使用静态值: {total_baseline}")
            
            # 获取 MySQL K线计数
            sql_mysql = "SELECT trade_date, COUNT(DISTINCT code) as count FROM stock_kline_daily WHERE trade_date BETWEEN %s AND %s GROUP BY trade_date"
            mysql_res = await db.execute(sql_mysql, (start_str, end_str))
            mysql_counts = {
                row[0].strftime("%Y-%m-%d") if isinstance(row[0], (datetime.date, datetime.datetime)) else str(row[0]): row[1]
                for row in mysql_res
            }
            

            # 获取 ClickHouse 同步记录（从内网同步日志表）
            sql_ch = """
                SELECT execution_time, records_processed, details 
                FROM sync_execution_logs 
                WHERE task_name = 'kline_daily_sync' 
                  AND status = 'SUCCESS'
                  AND execution_time >= %s
                  AND details LIKE '%%增量同步完成%%'
                ORDER BY execution_time DESC
            """
            # 扩大查询范围以包含 T+1 执行的日志
            ch_res = await db.execute(sql_ch, (start_str,))
            
            # 处理ClickHouse数据：从 details 中解析业务日期
            import re
            ch_counts = {}
            for row in ch_res:
                records = row[1]
                details = row[2]
                # 匹配 (YYYY-MM-DD ~ YYYY-MM-DD)
                match = re.search(r'\((\d{4}-\d{2}-\d{2})\s*~\s*(\d{4}-\d{2}-\d{2})\)', details)
                if match:
                    # 如果是单日同步，直接记录
                    if match.group(1) == match.group(2):
                        biz_date = match.group(1)
                        if biz_date not in ch_counts:
                            ch_counts[biz_date] = records
                    else:
                        # 如果是多日同步，暂取平均值或记录为多日（目前业务多为单日或补全）
                        # 此处简化处理，只记录在范围内出现的日期
                        pass
            
            # 组装数据
            days = []
            for cal_row in cal_rows:
                d_date = cal_row[0].strftime("%Y-%m-%d") if isinstance(cal_row[0], (datetime.date, datetime.datetime)) else str(cal_row[0])
                is_open = int(cal_row[1])
                
                if not is_open:
                    days.append({"date": d_date, "overallStatus": "holiday"})
                    continue
                
                l2_mysql = mysql_counts.get(d_date, 0)
                l3_ch = ch_counts.get(d_date, 0)
                
                # 完整性计算：以最终环节 (ClickHouse) 为准，对比基线
                # 如果 L3 还没做，则反映为不完整
                pct = round((l3_ch / total_baseline * 100), 2) if total_baseline > 0 else 0
                
                # 状态判定
                if pct >= 99:
                    status = "complete"
                elif pct >= 95:
                    status = "partial"
                else:
                    status = "critical"
                
                days.append({
                    "date": d_date,
                    "kline": {
                        "l1_baseline": total_baseline,
                        "l2_mysql": l2_mysql,
                        "l3_clickhouse": l3_ch,
                        "completeness_pct": pct
                    },
                    "overallStatus": status
                })
            
            return {
                "weekLabel": week_label,
                "lastUpdated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "days": days
            }
        except Exception as e:
            logger.error(f"Audit weekly 异常: {e}")
            return {"error": str(e)}
