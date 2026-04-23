import time
import asyncio
import easyquotation
from typing import Dict, Any, Optional
from app.utils.logger import get_logger

logger = get_logger("gateway.quote_service")

class QuoteService:
    """行情服务 - 使用 easyquotation (Tencent 数据源) 获取数据"""

    def __init__(self):
        # 使用 tencent 数据源，包含 PE/PB 和市值数据
        self.quotation = easyquotation.use('tencent')

    def _normalize_code(self, code: str) -> str:
        """
        转换为 easyquotation 格式: sh600519 / sz000001
        支持 sh.600519 / 600519.SH / 600519
        """
        code = code.strip().lower()
        if "." in code:
            parts = code.split(".")
            if parts[0] in ["sh", "sz"]:
                return f"{parts[0]}{parts[1]}"
            else:
                # 600519.sh
                m = parts[1]
                if m in ["ss", "sh"]: m = "sh"
                return f"{m}{parts[0]}"
        
        # 纯数字判断
        if code.startswith(('6', '9')):
            return f"sh{code}"
        else:
            return f"sz{code}"

    def _fix_encoding(self, text: Any) -> str:
        """修复可能存在的编码问题"""
        if not text:
            return ""
        if isinstance(text, bytes):
            return text.decode('gbk', errors='ignore')
        # 常见情况：GBK 被错误识别为 latin1
        try:
            return text.encode('latin1').decode('gbk')
        except (UnicodeEncodeError, UnicodeDecodeError):
            return str(text)

    async def _fetch_data(self, code: str) -> Optional[Dict[str, Any]]:
        """在线程池中运行同步的 easyquotation 调用"""
        norm_code = self._normalize_code(code)
        try:
            # run_in_executor 需要 running loop (Python 3.10+ 推荐写法)
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(None, self.quotation.stocks, [norm_code])
            
            # easyquotation tencent 源返回的 key 是 600519 (不带前缀)
            symbol = norm_code[2:]
            if not data:
                return None
            
            if symbol in data:
                return data[symbol]
            if norm_code in data:
                return data[norm_code]
                
            return None
        except Exception as e:
            logger.error(f"Error fetching data from Tencent: {e}")
            return None

    async def get_spot(self, code: str) -> Optional[Dict[str, Any]]:
        """获取个股实时行情"""
        data = await self._fetch_data(code)
        if not data:
            return None
        
        now = data.get("now", 0.0)
        close = data.get("close", 0.0)
        chg = round(now - close, 3) if now and close else 0.0
        chg_pct = round((now / close - 1) * 100, 2) if now and close else 0.0

        # 腾讯源的成交额通常在一些乱码键中，尝试通过数值大小和单位推断
        amount = 0.0
        volume = float(data.get("volume") or 0)
        denom_1 = now * volume
        denom_100 = denom_1 * 100

        # 寻找可能的成交额字段（通过比值判断，避免除零）
        if denom_1 > 0:
            for k, v in data.items():
                if isinstance(v, (int, float)) and v > 0:
                    ratio1 = v / denom_1
                    ratio100 = v / denom_100
                    if 0.9 < ratio1 < 1.1 or 0.9 < ratio100 < 1.1:
                        amount = float(v)
                        break

        if amount == 0 and denom_100 > 0:
            # 保底方案：按手数估算（每手100股）
            amount = denom_100

        return {
            "code": data.get("code", code),
            "name": self._fix_encoding(data.get("name", "")),
            "last": now,
            "open": data.get("open", 0.0),
            "high": data.get("high", 0.0),
            "low": data.get("low", 0.0),
            "prev_close": close,
            "chg": chg,
            "chg_pct": chg_pct,
            "volume": volume,
            "amount": amount,
            "timestamp": int(time.time())
        }

    async def get_snapshot(self, code: str) -> Optional[Dict[str, Any]]:
        """获取个股快照行情 (含五档盘口)"""
        # 只调用一次 _fetch_data，避免重复网络请求
        data = await self._fetch_data(code)
        if not data:
            return None

        # 计算涨跌额和涨跌幅
        now = data.get("now", 0.0)
        close = data.get("close", 0.0)
        chg = round(now - close, 3) if now and close else 0.0
        chg_pct = round((now / close - 1) * 100, 2) if now and close else 0.0

        # 成交额匹配
        volume = float(data.get("volume") or 0)
        denom_1 = now * volume
        denom_100 = denom_1 * 100
        amount = 0.0
        if denom_1 > 0:
            for k, v in data.items():
                if isinstance(v, (int, float)) and v > 0:
                    ratio1 = v / denom_1
                    ratio100 = v / denom_100
                    if 0.9 < ratio1 < 1.1 or 0.9 < ratio100 < 1.1:
                        amount = float(v)
                        break
        if amount == 0 and denom_100 > 0:
            amount = denom_100

        # Tencent 源五档字段名为 bid1, bid1_volume ... ask1, ask1_volume
        bid_ask = {
            "buy": [
                {"price": data.get(f"bid{i}", 0.0), "volume": data.get(f"bid{i}_volume", 0.0)}
                for i in range(1, 6)
            ],
            "sell": [
                {"price": data.get(f"ask{i}", 0.0), "volume": data.get(f"ask{i}_volume", 0.0)}
                for i in range(1, 6)
            ]
        }

        # 市值字段（腾讯源键名可能是乱码，先尝试已知键，再遍历兜底）
        market_cap = data.get("ֵ") or data.get("market_cap")
        float_market_cap = data.get("ֵͨ") or data.get("float_market_cap")
        if not market_cap:
            for k, v in data.items():
                if isinstance(v, (int, float)) and v > 100:
                    decoded = self._fix_encoding(k)
                    if '值' in decoded:
                        if '流通' in decoded:
                            float_market_cap = v
                        else:
                            market_cap = v

        return {
            "code": data.get("code", code),
            "name": self._fix_encoding(data.get("name", "")),
            "last": now,
            "open": data.get("open", 0.0),
            "high": data.get("high", 0.0),
            "low": data.get("low", 0.0),
            "prev_close": close,
            "chg": chg,
            "chg_pct": chg_pct,
            "volume": volume,
            "amount": amount,
            "timestamp": int(time.time()),
            "bid_ask": bid_ask,
            "pe_dynamic": data.get("PE"),
            "pb": data.get("PB"),
            "market_cap": market_cap,
            "float_market_cap": float_market_cap
        }

quote_service = QuoteService()
