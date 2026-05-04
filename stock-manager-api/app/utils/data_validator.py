import json
from typing import List, Dict, Any, Tuple

class DataValidator:
    """数据校验核心类"""

    @staticmethod
    def validate_kline_batch(data: List[Dict[str, Any]], source_table: str = "stock_kline_daily") -> Tuple[List[Dict], List[Dict]]:
        """
        批量校验 K 线数据
        
        Returns:
            (passed_records, rejected_records)
            rejected_records 包含: {'raw': original_dict, 'reason': str}
        """
        passed = []
        rejected = []

        for item in data:
            reason = DataValidator._check_kline_item(item)
            if reason:
                rejected.append({
                    "ts_code": item.get("ts_code"),
                    "trade_date": item.get("trade_date"),
                    "source_table": source_table,
                    "raw_data": json.dumps(item, ensure_ascii=False),
                    "reject_reason": reason
                })
            else:
                passed.append(item)
        
        return passed, rejected

    @staticmethod
    def _check_kline_item(item: Dict[str, Any]) -> str:
        """单条 K 线校验逻辑"""
        try:
            # 1. 必填字段校验
            required = ["ts_code", "trade_date", "open", "high", "low", "close"]
            for field in required:
                if item.get(field) is None:
                    return f"Missing required field: {field}"

            # 2. 值域校验 (Range)
            o, h, l, c = float(item["open"]), float(item["high"]), float(item["low"]), float(item["close"])
            if any(v <= 0 for v in [o, h, l, c]):
                return f"Price must be positive: O={o}, H={h}, L={l}, C={c}"
            
            vol = float(item.get("vol") or item.get("volume") or 0)
            amount = float(item.get("amount") or 0)
            if vol < 0 or amount < 0:
                return f"Volume/Amount cannot be negative: V={vol}, A={amount}"

            # 3. 行内一致性校验 (Consistency)
            # high 必须是最高，low 必须是最低
            if h < o or h < c or h < l:
                return f"High price inconsistency: H={h} is not the maximum of (O={o}, C={c}, L={l})"
            if l > o or l > c or l > h:
                return f"Low price inconsistency: L={l} is not the minimum of (O={o}, C={c}, H={h})"

            # 4. 业务合理性校验 (Rationality)
            # 成交额 / 成交量 应该在 [low, high] 附近
            # 注意：Tushare 的 vol 单位是手(100股)，amount 单位是千元。
            # 我们在入库前通常会统一单位。如果这里是原始数据，需要小心单位。
            # 假设传入的是统一后的数据（元，股）
            if vol > 0 and amount > 0:
                avg_price = amount / vol
                # 考虑到权重的细微差异，放宽到 10% 冗余
                if avg_price < l * 0.8 or avg_price > h * 1.2:
                    return f"Business irrationality: amount/vol={avg_price:.2f} is far from range [{l}, {h}]"

            return "" # Passed
        except (ValueError, TypeError) as e:
            return f"Data type error: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"
