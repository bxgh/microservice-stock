import httpx
import time
from typing import Dict, Any, Optional, List
from app.utils.logger import get_logger

logger = get_logger("gateway.quote_service")

# 腾讯行情接口支持批量获取，此处封装单股逻辑
_TENCENT_URL = "http://qt.gtimg.cn/q={symbol}"

class QuoteService:
    """行情服务 - 使用 Tencent (Tencent) API 获取实时数据"""

    def _normalize_code(self, code: str) -> str:
        """
        标准化代码为 Tencent 格式 (shxxxxxx, szxxxxxx)
        支持格式: 600519.SH / sh.600519 / 600519 / sz000001
        """
        code = code.strip().lower()
        
        # 处理 sh.600519 格式
        if "." in code and len(code.split(".")[0]) == 2:
            parts = code.split(".")
            market, symbol = parts[0], parts[1]
            return f"{market}{symbol}"
            
        # 处理 600519.sh 格式
        if "." in code:
            parts = code.split(".")
            symbol, market = parts[0], parts[1]
            if market in ["ss", "sh"]:
                return f"sh{symbol}"
            return f"sz{symbol}"
            
        # 纯数字判断
        if code.startswith(('6', '9')):
            return f"sh{code}"
        else:
            return f"sz{code}"

    def _safe_float(self, val: str, default: float = 0.0) -> float:
        """安全转换字符串为浮点数"""
        try:
            if not val or val == "" or val == "-":
                return default
            return float(val)
        except (ValueError, TypeError):
            return default

    async def _fetch_tencent(self, code: str) -> Optional[List[str]]:
        """从腾讯接口获取原始数据字符串"""
        symbol = self._normalize_code(code)
        url = _TENCENT_URL.format(symbol=symbol)
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    logger.error(f"Failed to fetch Tencent data for {code}: HTTP {resp.status_code}")
                    return None
                
                # 腾讯接口使用 GBK 编码
                content = resp.content.decode("gbk", errors="ignore")
                if "v_pv_none_match" in content or "=" not in content:
                    logger.warning(f"No match for {code}")
                    return None
                
                # 提取引号内的内容
                data_str = content.split('"')[1]
                return data_str.split("~")
        except Exception as e:
            logger.error(f"Error fetching Tencent data for {code}: {e}")
            return None

    async def get_spot(self, code: str) -> Optional[Dict[str, Any]]:
        """获取个股实时行情 (轻量版)"""
        items = await self._fetch_tencent(code)
        if not items or len(items) < 40:
            return None
        
        try:
            # 字段参考：0:类型, 1:名称, 2:代码, 3:当前价, 4:昨收, 5:今开, 6:成交量(手), 31:涨跌, 32:涨跌幅, 33:最高, 34:最低, 37:成交额(万)
            return {
                "code": items[2],
                "name": items[1],
                "last": self._safe_float(items[3]),
                "open": self._safe_float(items[5]),
                "high": self._safe_float(items[33]),
                "low": self._safe_float(items[34]),
                "prev_close": self._safe_float(items[4]),
                "chg": self._safe_float(items[31]),
                "chg_pct": self._safe_float(items[32]),
                "volume": self._safe_float(items[36]),
                "amount": self._safe_float(items[37]) * 10000,
                "timestamp": int(time.time())
            }
        except Exception as e:
            logger.error(f"Error parsing Tencent spot data for {code}: {e}")
            return None

    async def get_snapshot(self, code: str) -> Optional[Dict[str, Any]]:
        """获取个股快照行情 (含五档盘口)"""
        items = await self._fetch_tencent(code)
        if not items or len(items) < 50:
            return None
        
        try:
            # 买1-5: 9,11,13,15,17(价), 10,12,14,16,18(量)
            # 卖1-5: 19,21,23,25,27(价), 20,22,24,26,28(量)
            bid_ask = {
                "buy": [
                    {"price": self._safe_float(items[9+i*2]), "volume": self._safe_float(items[10+i*2])}
                    for i in range(5)
                ],
                "sell": [
                    {"price": self._safe_float(items[19+i*2]), "volume": self._safe_float(items[20+i*2])}
                    for i in range(5)
                ]
            }
            
            pe = self._safe_float(items[39], None)
            pb = self._safe_float(items[46], None)
            mkt_cap = self._safe_float(items[45], None)
            float_mkt_cap = self._safe_float(items[44], None)

            return {
                "code": items[2],
                "name": items[1],
                "last": self._safe_float(items[3]),
                "open": self._safe_float(items[5]),
                "high": self._safe_float(items[33]),
                "low": self._safe_float(items[34]),
                "prev_close": self._safe_float(items[4]),
                "chg": self._safe_float(items[31]),
                "chg_pct": self._safe_float(items[32]),
                "volume": self._safe_float(items[36]),
                "amount": self._safe_float(items[37]) * 10000,
                "timestamp": int(time.time()),
                "bid_ask": bid_ask,
                "pe_dynamic": pe,
                "pb": pb,
                "market_cap": mkt_cap * 100000000 if mkt_cap else None,
                "float_market_cap": float_mkt_cap * 100000000 if float_mkt_cap else None
            }
        except Exception as e:
            logger.error(f"Error parsing Tencent snapshot for {code}: {e}")
            return None

quote_service = QuoteService()
