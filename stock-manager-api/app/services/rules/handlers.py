import json
import logging
from typing import Dict, Any, List
from app.utils.database import db

logger = logging.getLogger("stock-manager.rule_handlers")


async def _log_findings(issues: List[Dict[str, Any]]):
    """批量落库 dq_findings"""
    if not issues:
        return
    query = """
        INSERT INTO dq_findings (ts_code, trade_date, rule_id, severity, description, diff_data)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    args = []
    for i in issues:
        args.append((
            i["ts_code"], i["trade_date"], i["rule_id"],
            i["severity"], i["finding_msg"], json.dumps(i["diff_data"])
        ))
    await db.execute_many(query, args)


async def price_limit_handler(rule: Any, context: Dict[str, Any]):
    """涨跌幅超限校验逻辑"""
    trade_date = context.get("trade_date")
    if not trade_date:
        return {"checked_count": 0, "rejected_count": 0}

    sql = """
        SELECT k.ts_code, k.open, k.high, k.low, k.close, k.pre_close,
               l.up_limit_pct, l.down_limit_pct, l.rule_desc
        FROM stock_kline_daily k
        JOIN dim_price_limit l ON k.ts_code = l.ts_code AND k.trade_date = l.trade_date
        WHERE k.trade_date = %s
    """
    records = await db.execute(sql, (trade_date,))
    if not records:
        return {"checked_count": 0, "rejected_count": 0}

    issues = []
    for row in records:
        ts_code, o, h, l, c, pre_c, up_pct, down_pct, rule_desc = row
        if not pre_c:
            continue

        theo_up = round(float(pre_c) * (1 + float(up_pct)) + 0.000001, 2)
        theo_down = round(float(pre_c) * (1 + float(down_pct)) + 0.000001, 2)

        if h > theo_up + 0.0101 or l < theo_down - 0.0101:
            issues.append({
                "ts_code": ts_code,
                "trade_date": trade_date,
                "rule_id": rule.id,
                "severity": rule.severity,
                "finding_msg": f"涨跌幅超限: H={h}, L={l}, 理论区间=[{theo_down}, {theo_up}]",
                "diff_data": {"h": float(h), "l": float(l), "up": theo_up, "down": theo_down}
            })
            # 如果异常过多，分批写入，防止 issues 列表过大
            if len(issues) >= 100:
                await _log_findings(issues)
                issues = []

    if issues:
        await _log_findings(issues)
    return {"checked_count": len(records), "rejected_count": len(issues)}


async def factor_reconcile_handler(rule: Any, context: Dict[str, Any]):
    """复权因子对账校验逻辑"""
    ts_code = context.get("ts_code")

    sql_actions = """
        SELECT ts_code, ex_date, div_cash, stk_div, stk_add
        FROM dim_corporate_action
        WHERE ex_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
    """
    if ts_code:
        sql_actions += f" AND ts_code = '{ts_code}'"

    actions = await db.execute(sql_actions)
    if not actions:
        return

    issues = []
    for ts_code, ex_date, d, s, t in actions:
        sql_pre = "SELECT close FROM stock_kline_daily WHERE ts_code=%s AND trade_date < %s ORDER BY trade_date DESC LIMIT 1"
        res_pre = await db.execute(sql_pre, (ts_code, ex_date))
        if not res_pre:
            continue
        pre_c = float(res_pre[0][0])

        sql_factor = "SELECT adjust_factor, adjust_date FROM stock_adjust_factor WHERE ts_code=%s AND adjust_date <= %s ORDER BY adjust_date DESC LIMIT 2"
        res_factor = await db.execute(sql_factor, (ts_code, ex_date))
        if len(res_factor) < 2:
            continue

        f_curr = float(res_factor[0][0])
        f_prev = float(res_factor[1][0])
        actual_ratio = f_curr / f_prev
        theo_ratio = (1 + float(s) + float(t)) / (1 - float(d) / pre_c)

        diff = abs(actual_ratio - theo_ratio) / theo_ratio
        if diff > 0.0001:
            issues.append(
                {
                    "ts_code": ts_code,
                    "trade_date": ex_date,
                    "rule_id": rule.id,
                    "severity": rule.severity,
                    "finding_msg": f"复权因子对账差异超限: 实际={
                        actual_ratio:.6f}, 理论={
                        theo_ratio:.6f}, 差异={
                        diff:.4%}",
                    "diff_data": {
                        "ex_date": str(ex_date),
                        "factors": {
                            "prev": f_prev,
                            "curr": f_curr},
                        "diff": diff}})

    await _log_findings(issues)
