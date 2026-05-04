import json
from typing import List, Dict, Any
from app.utils.database import db
from app.utils.logger import get_logger

logger = get_logger("stock-manager.business_rule")

class BusinessRuleValidator:
    async def validate_price_limit(self, trade_date: str):
        """校验当日 K 线的涨跌幅是否符合规则 (Story E5-S2)"""
        logger.info(f"开始涨跌幅业务规则校验: {trade_date}")
        
        # 1. 获取当日 K 线及其对应的理论涨跌幅限制
        # 需要前一日收盘价计算涨跌幅
        sql = """
            SELECT k.ts_code, k.open, k.high, k.low, k.close, k.pre_close,
                   l.up_limit_pct, l.down_limit_pct, l.rule_desc,
                   s.is_new, s.status
            FROM stock_kline_daily k
            JOIN dim_price_limit l ON k.ts_code = l.ts_code AND k.trade_date = l.trade_date
            LEFT JOIN dim_stock_status s ON k.ts_code = s.ts_code AND k.trade_date = s.trade_date
            WHERE k.trade_date = %s
        """
        records = await db.execute(sql, (trade_date,))
        if not records:
            logger.warning(f"当日 {trade_date} 无可校验记录")
            return
            
        issues = []
        for row in records:
            ts_code, o, h, l, c, pre_c, up_pct, down_pct, rule_desc, is_new, status = row
            
            # 如果没有前收盘价，无法校验
            if not pre_c: continue
            
            # 计算理论涨跌停价格 (四舍五入到分，A 股规则)
            # 注意：实际规则是 round(pre_c * (1+pct), 2)
            theo_up = round(float(pre_c) * (1 + float(up_pct)) + 0.000001, 2)
            theo_down = round(float(pre_c) * (1 + float(down_pct)) + 0.000001, 2)
            
            # 校验逻辑
            # 1. high 不能超过 theo_up (容差 0.01 元以防浮点误差)
            # 2. low 不能低于 theo_down
            if h > theo_up + 0.0101 or l < theo_down - 0.0101:
                # 标记为可疑
                issues.append({
                    "ts_code": ts_code,
                    "trade_date": trade_date,
                    "check_type": "BUSINESS_RULE",
                    "severity": "WARN",
                    "finding_msg": f"涨跌幅超限: H={h}, L={l}, 理论区间=[{theo_down}, {theo_up}], 规则={rule_desc}",
                    "diff_data": {
                        "ohlc": {"o": float(o), "h": float(h), "l": float(l), "c": float(c)},
                        "pre_close": float(pre_c),
                        "limits": {"up": theo_up, "down": theo_down, "up_pct": float(up_pct), "down_pct": float(down_pct)}
                    }
                })
                
        # 批量写入 DQ findings
        if issues:
            await self._log_findings(issues)
            logger.info(f"发现 {len(issues)} 条涨跌幅异常记录")
        else:
            logger.info("涨跌幅规则校验通过")

    async def reconcile_adjustment_factors(self, ts_code: str = None):
        """复权因子对账 (Story E5-S3)
        比对逻辑: 理论因子变动 vs 实际因子变动
        理论变动 R = (1 + S + T) / (1 - D/P_pre)
        """
        logger.info(f"开始复权因子对账: {ts_code if ts_code else '全市场'}")
        
        # 1. 获取所有除权除息事件
        sql_actions = """
            SELECT ts_code, ex_date, div_cash, stk_div, stk_add 
            FROM dim_corporate_action 
            WHERE ex_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        """
        if ts_code:
            sql_actions += f" AND ts_code = '{ts_code}'"
        
        actions = await db.execute(sql_actions)
        if not actions:
            logger.info("近期无除权除息事件，无需对账")
            return
            
        issues = []
        for ts_code, ex_date, d, s, t in actions:
            # 获取前一日收盘价
            sql_pre = "SELECT close FROM stock_kline_daily WHERE ts_code=%s AND trade_date < %s ORDER BY trade_date DESC LIMIT 1"
            res_pre = await db.execute(sql_pre, (ts_code, ex_date))
            if not res_pre: continue
            pre_c = float(res_pre[0][0])
            
            # 获取因子变动
            sql_factor = "SELECT adjust_factor, adjust_date FROM stock_adjust_factor WHERE ts_code=%s AND adjust_date <= %s ORDER BY adjust_date DESC LIMIT 2"
            res_factor = await db.execute(sql_factor, (ts_code, ex_date))
            if len(res_factor) < 2: continue
            
            f_curr = float(res_factor[0][0])
            f_prev = float(res_factor[1][0])
            actual_ratio = f_curr / f_prev
            
            # 计算理论比率
            # D 是每股分红，S 是送股，T 是转增
            # 理论比率 = (1 + S + T) / (1 - D/P_pre)
            theo_ratio = (1 + float(s) + float(t)) / (1 - float(d)/pre_c)
            
            # 比对，容差 0.01%
            diff = abs(actual_ratio - theo_ratio) / theo_ratio
            if diff > 0.0001:
                issues.append({
                    "ts_code": ts_code,
                    "trade_date": ex_date,
                    "check_type": "FACTOR_RECONCILE",
                    "severity": "ERROR",
                    "finding_msg": f"复权因子对账差异超限: 实际变动={actual_ratio:.6f}, 理论变动={theo_ratio:.6f}, 差异={diff:.4%}",
                    "diff_data": {
                        "ex_date": str(ex_date),
                        "pre_close": pre_c,
                        "corporate_action": {"div": float(d), "stk_div": float(s), "stk_add": float(t)},
                        "factors": {"prev": f_prev, "curr": f_curr},
                        "diff": diff
                    }
                })
                
        if issues:
            await self._log_findings(issues)
            logger.warning(f"复权因子对账发现 {len(issues)} 处异常")
        else:
            logger.info("复权因子对账全部通过")

    async def _log_findings(self, issues: List[Dict[str, Any]]):
        """批量落库 dq_findings"""
        query = """
            INSERT INTO dq_findings (ts_code, trade_date, rule_id, severity, description, diff_data)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        args = []
        for i in issues:
            args.append((
                i["ts_code"], i["trade_date"], i["check_type"], 
                i["severity"], i["finding_msg"], json.dumps(i["diff_data"])
            ))
        await db.execute_many(query, args)

business_rule_validator = BusinessRuleValidator()
