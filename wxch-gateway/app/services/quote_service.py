import httpx
import time
from typing import Dict, Any, Optional
from app.utils.logger import get_logger

logger = get_logger("gateway.quote_service")

# EastMoney 请求头，模拟浏览器请求
_EM_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/"
}


class QuoteService:
    """行情服务 - 使用 EastMoney API 获取实时数据"""

    def _normalize_code(self, code: str) -> str:
        """
        标准化代码为 EastMoney secid 格式
        SH市场: 1.xxxxxx, SZ/BJ市场: 0.xxxxxx
        支持格式: 600519.SH / sh.600519 / 600519
        """
        code = code.strip()

        # 处理 sh.600519 / sz.000001 格式 (BaoStock 格式)
        if "." in code and len(code.split(".")[0]) == 2:
            parts = code.split(".")
            market, symbol = parts[0].upper(), parts[1]
            if market in ("SH", "SS"):
                return f"1.{symbol}"
            else:
                return f"0.{symbol}"

        # 处理 600519.SH / 000001.SZ 格式
        if "." in code:
            parts = code.split(".")
            symbol, market = parts[0], parts[1].upper()
            if market in ("SH", "SS"):
                return f"1.{symbol}"
            else:
                return f"0.{symbol}"

        # 纯数字：按代码前缀判断市场
        if code.startswith(("6", "9")):
            return f"1.{code}"
        else:
            return f"0.{code}"

    def _safe_float(self, data: dict, key: str, div: float = 100.0) -> Optional[float]:
        """安全读取并转换 EastMoney 数值字段 (原始值通常放大100倍)"""
        val = data.get(key)
        if val is None or val == "-":
            return None
        try:
            result = float(val) / div
            return result if result != 0.0 else None
        except (TypeError, ValueError):
            return None

    def _safe_price(self, data: dict, key: str) -> float:
        """读取价格字段，不可用时返回 0.0"""
        val = self._safe_float(data, key, div=100.0)
        return val if val is not None else 0.0

    async def get_spot(self, code: str) -> Optional[Dict[str, Any]]:
        """获取个股实时行情 (轻量版)"""
        secid = self._normalize_code(code)
        # f57: 代码, f58: 名称, f43: 最新价, f44: 最高, f45: 最低
        # f46: 开盘, f60: 昨收, f169: 涨跌幅, f170: 涨跌额
        # f47: 成交量(手), f48: 成交额(元)
        fields = "f57,f58,f43,f44,f45,f46,f60,f169,f170,f47,f48"
        url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields={fields}"

        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=_EM_HEADERS)
                if resp.status_code != 200:
                    logger.error(f"获取实时行情失败: code={code}, HTTP={resp.status_code}")
                    return None

                res_json = resp.json()
                data = res_json.get("data")
                if not data:
                    logger.warning(f"实时行情无数据: code={code}")
                    return None

                return {
                    "code": data.get("f57", ""),
                    "name": data.get("f58", ""),
                    "last": self._safe_price(data, "f43"),
                    "open": self._safe_price(data, "f46"),
                    "high": self._safe_price(data, "f44"),
                    "low": self._safe_price(data, "f45"),
                    "prev_close": self._safe_price(data, "f60"),
                    "chg": self._safe_price(data, "f170"),
                    "chg_pct": self._safe_price(data, "f169"),
                    "volume": float(data.get("f47") or 0),
                    "amount": float(data.get("f48") or 0),
                    "timestamp": int(time.time())
                }
        except Exception as e:
            logger.error(f"获取实时行情异常: code={code}, error={e}", exc_info=True)
            return None

    async def get_snapshot(self, code: str) -> Optional[Dict[str, Any]]:
        """获取个股快照行情 (含五档盘口与估值)"""
        secid = self._normalize_code(code)
        # 基础行情 + 五档卖盘(f11卖1价,f12卖1量 ... f19卖5价,f20卖5量)
        # 五档买盘(f31买1价,f32买1量 ... f39买5价,f40买5量)
        # f162: PE(动), f167: PB, f116: 总市值, f117: 流通市值
        fields = (
            "f57,f58,f43,f44,f45,f46,f60,f169,f170,f47,f48,"
            "f11,f12,f13,f14,f15,f16,f17,f18,f19,f20,"
            "f31,f32,f33,f34,f35,f36,f37,f38,f39,f40,"
            "f162,f167,f116,f117"
        )
        url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields={fields}"

        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=_EM_HEADERS)
                if resp.status_code != 200:
                    logger.error(f"获取快照行情失败: code={code}, HTTP={resp.status_code}")
                    return None

                res_json = resp.json()
                data = res_json.get("data")
                if not data:
                    logger.warning(f"快照行情无数据: code={code}")
                    return None

                # 提取五档买卖盘口
                bid_ask = {
                    "buy": [
                        {
                            "price": self._safe_price(data, f"f{31 + i * 2}"),
                            "volume": float(data.get(f"f{32 + i * 2}") or 0)
                        }
                        for i in range(5)
                    ],
                    "sell": [
                        {
                            "price": self._safe_price(data, f"f{11 + i * 2}"),
                            "volume": float(data.get(f"f{12 + i * 2}") or 0)
                        }
                        for i in range(5)
                    ]
                }

                return {
                    "code": data.get("f57", ""),
                    "name": data.get("f58", ""),
                    "last": self._safe_price(data, "f43"),
                    "open": self._safe_price(data, "f46"),
                    "high": self._safe_price(data, "f44"),
                    "low": self._safe_price(data, "f45"),
                    "prev_close": self._safe_price(data, "f60"),
                    "chg": self._safe_price(data, "f170"),
                    "chg_pct": self._safe_price(data, "f169"),
                    "volume": float(data.get("f47") or 0),
                    "amount": float(data.get("f48") or 0),
                    "timestamp": int(time.time()),
                    "bid_ask": bid_ask,
                    "pe_dynamic": self._safe_float(data, "f162"),
                    "pb": self._safe_float(data, "f167"),
                    "market_cap": data.get("f116"),
                    "float_market_cap": data.get("f117")
                }
        except Exception as e:
            logger.error(f"获取快照行情异常: code={code}, error={e}", exc_info=True)
            return None


quote_service = QuoteService()
