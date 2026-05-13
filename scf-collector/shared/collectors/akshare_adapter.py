import logging
from typing import List, Dict, Any
from shared.utils.models import KLineModel

logger = logging.getLogger(__name__)

class AkShareAdapter:
    """
    AkShare 数据适配器：负责将 AkShare 原始 DataFrame/Dict 转换为 KLineModel
    处理量纲：股 -> 手，百分数 -> 小数
    处理代码：前缀 (sh600519) -> 后缀 (600519.SH)
    """

    @staticmethod
    def _convert_code(raw_code: str) -> str:
        """
        统一转换至 Tushare 格式 (600519.SH)
        支持格式: sh600519, sz000001, 600519, 000001
        """
        if not raw_code: return ""
        raw_code = str(raw_code).lower()
        
        # 处理带前缀的情况 (sh600519)
        if raw_code[:2] in ['sh', 'sz', 'bj']:
            prefix = raw_code[:2].upper()
            num_code = raw_code[2:]
            return f"{num_code}.{prefix}"
            
        # 处理纯数字的情况 (600519)
        num_code = raw_code
        if num_code.startswith('6'): suffix = 'SH'
        elif num_code.startswith('0') or num_code.startswith('3'): suffix = 'SZ'
        elif num_code.startswith('8') or num_code.startswith('4') or num_code.startswith('9'): suffix = 'BJ'
        else: suffix = 'SH'
        
        return f"{num_code}.{suffix}"

    @classmethod
    def from_spot_records(cls, records: List[Dict[str, Any]], biz_date: str) -> List[KLineModel]:
        """
        从 AkShare 实时快照 (Sina/Legacy 源) 记录转换
        字段参考: symbol, code, name, trade (最新价), settlement (昨收), open, high, low, volume (股), amount (元), tickhum (涨跌幅%)
        """
        models = []
        for r in records:
            try:
                # 停牌过滤：成交量为 0 且开盘价为 0
                vol_raw = float(r.get('volume', 0))
                open_price = float(r.get('open', 0))
                if vol_raw == 0 and open_price == 0:
                    continue

                ts_code = cls._convert_code(r.get('symbol', ''))
                close_price = float(r.get('trade', 0))
                pre_close = float(r.get('settlement', 0))
                
                # 健壮性：处理昨收价为 0 的极端情况
                if pre_close == 0: pre_close = close_price

                m = KLineModel(
                    ts_code=ts_code,
                    trade_date=biz_date,
                    open=open_price,
                    high=float(r.get('high', 0)),
                    low=float(r.get('low', 0)),
                    close=close_price,
                    pre_close=pre_close,
                    change=close_price - pre_close,
                    # Sina 源涨跌幅可能是 tickhum 或 changepercent
                    pct_chg=float(r.get('tickhum', r.get('changepercent', 0))) / 100.0,
                    volume=vol_raw / 100.0, # 股 -> 手
                    amount=float(r.get('amount', 0))
                )
                models.append(m)
            except Exception as e:
                continue
        return models

    @classmethod
    def from_em_spot_records(cls, records: List[Dict[str, Any]], biz_date: str) -> List[KLineModel]:
        """
        从 AkShare 实时快照 (EM 源) 记录转换
        字段参考: 代码, 名称, 最新价, 昨收, 今开, 最高, 最低, 成交量 (股，接口实际单位), 成交额 (元), 涨跌幅 (%)
        """
        models = []
        for r in records:
            try:
                raw_code = r.get('代码', '')
                if not raw_code: continue
                
                ts_code = cls._convert_code(raw_code)
                vol_raw = float(r.get('成交量', 0))
                
                # 停牌过滤
                if vol_raw == 0: continue

                m = KLineModel(
                    ts_code=ts_code,
                    trade_date=biz_date,
                    open=float(r.get('今开', 0)),
                    high=float(r.get('最高', 0)),
                    low=float(r.get('最低', 0)),
                    close=float(r.get('最新价', 0)),
                    pre_close=float(r.get('昨收', 0)),
                    change=float(r.get('涨跌额', 0)),
                    pct_chg=float(r.get('涨跌幅', 0)) / 100.0,
                    volume=vol_raw / 100.0, # 经实测 AkShare EM 源也是股，需转换为手
                    amount=float(r.get('成交额', 0))
                )
                models.append(m)
            except Exception as e:
                continue
        return models
