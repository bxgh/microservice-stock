"""市场数据相关端点"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

import akshare as ak

router = APIRouter()
logger = logging.getLogger("akshare-api")


@router.get("/dragon_tiger/daily")
async def get_dragon_tiger_daily(
    request: Request,
    date: Optional[str] = Query(None, description="日期 YYYY-MM-DD,默认最近交易日"),
):
    """
    获取龙虎榜数据
    
    - **date**: 交易日期,如 2024-01-15
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    try:
        # 获取龙虎榜数据
        if date:
            # 转换日期格式: YYYY-MM-DD -> YYYYMMDD
            date_str = date.replace("-", "")
            df = ak.stock_lhb_detail_em(start_date=date_str, end_date=date_str)
        else:
            df = ak.stock_lhb_detail_em()
        
        if df.empty:
            return []
        
        # 限制返回数量
        df = df.head(50)
        
        result = []
        for _, row in df.iterrows():
            result.append({
                "code": row.get("代码", ""),
                "name": row.get("名称", ""),
                "close": float(row.get("收盘价", 0)) if row.get("收盘价") else None,
                "change_pct": float(row.get("涨跌幅", 0)) if row.get("涨跌幅") else None,
                "turnover_rate": float(row.get("换手率", 0)) if row.get("换手率") else None,
                "net_buy": float(row.get("龙虎榜净买额", 0)) if row.get("龙虎榜净买额") else None,
                "reason": row.get("上榜原因", ""),
                "date": str(row.get("上榜日", "")),
            })
        
        logger.info(f"获取龙虎榜成功: date={date}, count={len(result)}", extra={"request_id": request_id})
        return result
        
    except Exception as e:
        logger.error(f"获取龙虎榜失败: date={date}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取龙虎榜失败: {str(e)}")


@router.get("/industry/stock/{code}")
async def get_stock_industry(request: Request, code: str):
    """
    获取个股所属行业
    
    - **code**: 股票代码,如 600519
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    try:
        # 获取股票行业信息
        df = ak.stock_individual_info_em(symbol=code)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"未找到股票: {code}")
        
        # 提取行业信息
        industry = None
        for _, row in df.iterrows():
            if row.get("item") == "行业":
                industry = row.get("value")
                break
        
        result = {
            "code": code,
            "industry": industry,
        }
        
        # 补充其他基本信息
        for _, row in df.iterrows():
            item = row.get("item", "")
            value = row.get("value", "")
            if item == "股票简称":
                result["name"] = value
            elif item == "上市时间":
                result["list_date"] = value
            elif item == "总股本":
                result["total_share"] = value
        
        logger.info(f"获取行业信息成功: code={code}", extra={"request_id": request_id})
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取行业信息失败: code={code}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取行业信息失败: {str(e)}")


@router.get("/rank/hot")
async def get_hot_rank(
    request: Request,
    limit: int = Query(50, ge=1, le=100, description="返回数量,默认50"),
):
    """
    获取热门股票排行
    
    - **limit**: 返回数量,最大100
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    try:
        # 获取热门股票(按成交额排序)
        df = ak.stock_zh_a_spot_em()
        
        if df.empty:
            return []
        
        # 按成交额排序
        df = df.sort_values("成交额", ascending=False).head(limit)
        
        result = []
        for idx, row in df.iterrows():
            result.append({
                "rank": len(result) + 1,
                "code": row.get("代码", ""),
                "name": row.get("名称", ""),
                "price": float(row.get("最新价", 0)) if row.get("最新价") else None,
                "change_pct": float(row.get("涨跌幅", 0)) if row.get("涨跌幅") else None,
                "volume": float(row.get("成交量", 0)) if row.get("成交量") else None,
                "amount": float(row.get("成交额", 0)) if row.get("成交额") else None,
                "turnover_rate": float(row.get("换手率", 0)) if row.get("换手率") else None,
            })
        
        logger.info(f"获取热门排行成功: limit={limit}, count={len(result)}", extra={"request_id": request_id})
        return result
        
    except Exception as e:
        logger.error(f"获取热门排行失败: error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取热门排行失败: {str(e)}")
