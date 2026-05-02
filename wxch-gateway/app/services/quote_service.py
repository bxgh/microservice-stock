import time
import asyncio
import httpx
import easyquotation
from typing import Dict, Any, Optional, List
from app.utils.logger import get_logger

logger = get_logger("gateway.quote_service")

class QuoteService:
    """行情服务 - 获取实时行情与分时数据"""

    def __init__(self):
        # 使用 httpx 异步请求，不再依赖同步的 easyquotation
        self.client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)

    def _normalize_code(self, code: str) -> str:
        """
        转换为腾讯格式: sh600519 / sz000001 / bj831039
        """
        code = code.strip().lower()
        if "." in code:
            parts = code.split(".")
            if parts[0] in ["sh", "sz", "bj"]:
                return f"{parts[0]}{parts[1]}"
            else:
                m = parts[1]
                if m in ["ss", "sh"]: m = "sh"
                return f"{m}{parts[0]}"
        
        if code.startswith(('6', '9')):
            return f"sh{code}"
        elif code.startswith(('4', '8')):
            return f"bj{code}"
        else:
            return f"sz{code}"

    def _fix_encoding(self, text: Any) -> str:
        """修复编码问题"""
        if not text: return ""
        try:
            return text.encode('latin1').decode('gbk')
        except:
            return str(text)

    async def _fetch_raw_qt(self, code: str) -> Optional[List[str]]:
        """从腾讯 qt 接口获取原始点阵数据"""
        norm_code = self._normalize_code(code)
        url = f"http://qt.gtimg.cn/q={norm_code}"
        try:
            resp = await self.client.get(url)
            if resp.status_code != 200: return None
            
            # 响应格式: v_sh600519="1~贵州茅台~600519~...";
            text = resp.text
            if "~" not in text: return None
            
            parts = text.split('"')
            if len(parts) < 2: return None
            data_str = parts[1]
            return data_str.split("~")
        except Exception as e:
            logger.error(f"Error fetching raw qt: {e}")
            return None

    async def get_spot(self, code: str) -> Optional[Dict[str, Any]]:
        """获取个股实时行情"""
        qt = await self._fetch_raw_qt(code)
        if not qt or len(qt) < 40: return None
        
        try:
            last = float(qt[3])
            prev_close = float(qt[4])
            return {
                "code": qt[2],
                "name": qt[1],
                "last": last,
                "open": float(qt[5]),
                "high": float(qt[33]),
                "low": float(qt[34]),
                "prev_close": prev_close,
                "chg": round(last - prev_close, 3),
                "chg_pct": round((last / prev_close - 1) * 100, 2) if prev_close > 0 else 0,
                "volume": float(qt[6]),
                "amount": float(qt[37]) * 10000,
                "timestamp": int(time.time())
            }
        except (ValueError, IndexError):
            return None

    async def get_snapshot(self, code: str) -> Optional[Dict[str, Any]]:
        """获取个股快照行情 (含五档盘口、量比、实换手)"""
        qt = await self._fetch_raw_qt(code)
        if not qt or len(qt) < 71: return None
        
        try:
            last = float(qt[3])
            prev_close = float(qt[4])
            
            # 解析五档 (买 9-18, 卖 19-28)
            bid_ask = {
                "buy": [
                    {"price": float(qt[9 + i*2]), "volume": float(qt[10 + i*2]) * 100}
                    for i in range(5)
                ],
                "sell": [
                    {"price": float(qt[19 + i*2]), "volume": float(qt[20 + i*2]) * 100}
                    for i in range(5)
                ]
            }

            return {
                "code": qt[2],
                "name": qt[1],
                "last": last,
                "open": float(qt[5]),
                "high": float(qt[33]),
                "low": float(qt[34]),
                "prev_close": prev_close,
                "chg": round(last - prev_close, 3),
                "chg_pct": round((last / prev_close - 1) * 100, 2) if prev_close > 0 else 0,
                "volume": float(qt[6]),
                "amount": float(qt[37]) * 10000,
                "timestamp": int(time.time()),
                "bid_ask": bid_ask,
                "pe_dynamic": float(qt[52]) if qt[52] else None,
                "pb": float(qt[46]) if qt[46] else None,
                "market_cap": float(qt[45]) if qt[45] else None,
                "float_market_cap": float(qt[44]) if qt[44] else None,
                "turnover_rate": float(qt[38]) if qt[38] else None,
                "turnover_real": float(qt[70]) if len(qt) > 70 and qt[70] else None,
                "quantity_ratio": float(qt[49]) if qt[49] else None
            }
        except (ValueError, IndexError):
            return None

    async def get_time_share(self, code: str) -> Dict[str, Any]:
        """获取个股分时行情 (Tencent 源)"""
        norm_code = self._normalize_code(code)
        url = f"https://web.ifzq.gtimg.cn/appstock/app/minute/query?code={norm_code}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://new.qq.com/"
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    logger.error(f"Failed to fetch time-share data: {resp.status_code}")
                    return {}
                
                data_json = resp.json()
                if 'data' not in data_json or norm_code not in data_json['data']:
                    logger.warning(f"No time-share data found for {norm_code}")
                    return {}
                
                stock_data = data_json['data'][norm_code]
                # 提取当日统计 (量比、换手、实换手)
                qt = stock_data.get('qt', {}).get(norm_code, [])
                turnover_rate = float(qt[38]) if len(qt) > 38 else None
                turnover_real = float(qt[70]) if len(qt) > 70 else None
                quantity_ratio = float(qt[49]) if len(qt) > 49 else None

                # 提取分时点位
                inner_data = stock_data.get('data', {})
                if isinstance(inner_data, dict):
                    minute_list = inner_data.get('data', [])
                else:
                    minute_list = inner_data if isinstance(inner_data, list) else []

                result = []
                prev_vol = 0.0
                prev_amount = 0.0
                for item in minute_list:
                    if not isinstance(item, str):
                        continue
                    # 格式: "时间 价格 累积成交量 累积成交额"
                    parts = item.split()
                    if len(parts) < 3:
                        continue
                    try:
                        curr_price = float(parts[1])
                        cum_vol = float(parts[2])
                        cum_amount = float(parts[3]) if len(parts) > 3 else 0.0
                        
                        # 计算当前分钟增量
                        minute_vol = cum_vol - prev_vol
                        minute_amount = cum_amount - prev_amount
                        
                        # 计算均价 (累积成交额 / 累积成交量)
                        # 腾讯分时接口返回的 cum_vol 已经是股数，无需再乘以 100
                        avg_price = round(cum_amount / cum_vol, 3) if cum_vol > 0 else curr_price

                        result.append({
                            "time": parts[0],
                            "price": curr_price,
                            "avg_price": avg_price,
                            "volume": minute_vol,
                            "amount": minute_amount
                        })
                        
                        prev_vol = cum_vol
                        prev_amount = cum_amount
                    except (ValueError, IndexError, ZeroDivisionError) as parse_err:
                        continue

                return {
                    "code": code,
                    "turnover_rate": turnover_rate,
                    "turnover_real": turnover_real,
                    "quantity_ratio": quantity_ratio,
                    "data": result
                }
        except Exception as e:
            logger.error(f"Error fetching time-share data: {e}")
            return {}

quote_service = QuoteService()
