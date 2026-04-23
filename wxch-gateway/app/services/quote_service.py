import httpx
import time
from typing import Dict, Any, Optional
from app.utils.logger import get_logger

logger = get_logger("gateway.quote_service")

# Tencent 请求头
_TENCENT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://gu.qq.com/"
}

class QuoteService:
    """行情服务 - 使用 Tencent (QQ) API 获取实时数据"""

    def _normalize_code_tencent(self, code: str) -> str:
        """
        标准化代码为 Tencent 格式 (sh600519, bj920002)
        """
        code = code.strip().lower()
        if "." in code:
            parts = code.split(".")
            # sh.600519 or 600519.sh
            if len(parts[0]) == 2 and not parts[0].isdigit():
                return f"{parts[0]}{parts[1]}"
            if len(parts[1]) == 2 and not parts[1].isdigit():
                return f"{parts[1]}{parts[0]}"
            # Default to SH if unknown suffix but has dot
            return f"sh{parts[0]}"
        
        # 纯数字判断
        if code.startswith(('6', '9', '5')):
            return f"sh{code}"
        elif code.startswith(('8', '4', '0', '3')):
            return f"sz{code}"
        # 默认
        return f"sh{code}"

    async def _fetch_tencent_raw(self, tencent_code: str) -> Optional[str]:
        """从腾讯接口获取原始文本数据"""
        url = f"https://qt.gtimg.cn/q={tencent_code}"
        try:
            async with httpx.AsyncClient(timeout=5.0, verify=False) as client:
                resp = await client.get(url, headers=_TENCENT_HEADERS)
                if resp.status_code != 200:
                    return None
                # 腾讯接口通常返回 GBK 编码
                return resp.content.decode("gbk")
        except Exception as e:
            logger.error(f"Tencent fetch error: {e}")
            return None

    def _parse_tencent_data(self, raw: str) -> Optional[Dict[str, Any]]:
        """解析腾讯接口返回的波浪号分隔数据"""
        try:
            if "=" not in raw:
                return None
            data_str = raw.split("=")[1].strip().strip('"').strip(";")
            items = data_str.split("~")
            if len(items) < 35:
                return None
            
            def to_float(idx, default=0.0):
                try:
                    return float(items[idx]) if items[idx] else default
                except:
                    return default

            # 处理时间戳 20260423113120 (idx 30)
            ts_str = items[30]
            try:
                struct_time = time.strptime(ts_str, "%Y%m%d%H%M%S")
                timestamp = int(time.mktime(struct_time))
            except:
                timestamp = int(time.time())

            res = {
                "code": items[2],
                "name": items[1],
                "last": to_float(3),
                "open": to_float(5),
                "high": to_float(33),
                "low": to_float(34),
                "prev_close": to_float(4),
                "chg": to_float(31),
                "chg_pct": to_float(32),
                "volume": to_float(6),
                "amount": to_float(37) * 10000, # 腾讯成交额单位是万元
                "timestamp": timestamp
            }
            
            # 添加盘口数据
            # 买1-5: 9,11,13,15,17(价), 10,12,14,16,18(量)
            # 卖1-5: 19,21,23,25,27(价), 20,22,24,26,28(量)
            bid_ask = {
                "buy": [
                    {"price": to_float(9 + i*2), "volume": to_float(10 + i*2)}
                    for i in range(5)
                ],
                "sell": [
                    {"price": to_float(19 + i*2), "volume": to_float(20 + i*2)}
                    for i in range(5)
                ]
            }
            res["bid_ask"] = bid_ask
            
            # 市值等信息
            if len(items) > 46:
                res["pe_dynamic"] = to_float(39)
                res["pb"] = to_float(46)
                res["market_cap"] = to_float(45) * 100000000 # 亿 -> 元
                res["float_market_cap"] = to_float(44) * 100000000 # 亿 -> 元
            
            return res
        except Exception as e:
            logger.error(f"Parse Tencent error: {e}")
            return None

    async def get_spot(self, code: str) -> Optional[Dict[str, Any]]:
        """获取个股实时行情"""
        tencent_code = self._normalize_code_tencent(code)
        raw = await self._fetch_tencent_raw(tencent_code)
        if not raw:
            return None
        
        data = self._parse_tencent_data(raw)
        if not data:
            return None
        
        # 返回 SpotResponse 所需的子集
        return {
            "code": data["code"],
            "name": data["name"],
            "last": data["last"],
            "open": data["open"],
            "high": data["high"],
            "low": data["low"],
            "prev_close": data["prev_close"],
            "chg": data["chg"],
            "chg_pct": data["chg_pct"],
            "volume": data["volume"],
            "amount": data["amount"],
            "timestamp": data["timestamp"]
        }

    async def get_snapshot(self, code: str) -> Optional[Dict[str, Any]]:
        """获取个股快照行情 (含五档盘口)"""
        tencent_code = self._normalize_code_tencent(code)
        raw = await self._fetch_tencent_raw(tencent_code)
        if not raw:
            return None
        
        return self._parse_tencent_data(raw)

quote_service = QuoteService()
