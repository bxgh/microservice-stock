from typing import List, Dict, Any
from app.core.rule_engine import rule_engine
from app.services.rules.handlers import price_limit_handler, factor_reconcile_handler
from app.utils.logger import get_logger

logger = get_logger("stock-manager.business_rule")


class BusinessRuleValidator:
    def __init__(self):
        # 注册处理器
        rule_engine.register_handler(
            "price_limit_handler", price_limit_handler)
        rule_engine.register_handler(
            "factor_reconcile_handler",
            factor_reconcile_handler)

    async def validate_price_limit(self, trade_date: str) -> Dict[str, Any]:
        """校验当日 K 线的涨跌幅 (重构后调用规则引擎)"""
        logger.info(f"触发涨跌幅校验: {trade_date}")
        results = await rule_engine.execute_all({"trade_date": trade_date})
        
        # 汇总统计
        passed_count = 0
        rejected_count = 0
        for r in results:
            if r.get("rule_id") == "PRICE_LIMIT_CHECK":  # 对应 rules.yaml 中的 ID
                res = r.get("result", {})
                passed_count += (res.get("checked_count", 0) - res.get("rejected_count", 0))
                rejected_count += res.get("rejected_count", 0)
        
        return {"passed_count": passed_count, "rejected_count": rejected_count}

    async def reconcile_adjustment_factors(self, ts_code: str = None) -> Dict[str, Any]:
        """复权因子对账 (重构后调用规则引擎)"""
        logger.info(f"触发因子对账: {ts_code if ts_code else '全市场'}")
        results = await rule_engine.execute_all({"ts_code": ts_code})
        return {"results": results}


business_rule_validator = BusinessRuleValidator()
