"""指数与行业数据端点"""
import logging

from fastapi import APIRouter, HTTPException, Request

import baostock as bs

router = APIRouter()
logger = logging.getLogger("baostock-api")


@router.get("/index/cons/{index}")
async def get_index_constituents(request: Request, index: str):
    """
    获取指数成分股
    
    - **index**: 指数代码,如 sz.399300 (沪深300), sh.000016 (上证50)
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    try:
        # 补全指数代码前缀
        if not index.startswith(("sh.", "sz.")):
            if index.startswith("0"):
                index = f"sh.{index}"
            else:
                index = f"sz.{index}"
        
        # 查询成分股
        rs = bs.query_hs300_stocks() if "399300" in index else bs.query_sz50_stocks()
        
        # 通用查询
        if "000016" in index:
            rs = bs.query_sz50_stocks()
        elif "399300" in index:
            rs = bs.query_hs300_stocks()
        elif "000905" in index:
            rs = bs.query_zz500_stocks()
        else:
            # 尝试沪深300
            rs = bs.query_hs300_stocks()
        
        if rs.error_code != "0":
            logger.error(f"查询指数成分失败: {rs.error_msg}", extra={"request_id": request_id})
            raise HTTPException(status_code=500, detail=f"查询失败: {rs.error_msg}")
        
        result = []
        while rs.next():
            row = rs.get_row_data()
            result.append({
                "code": row[1] if len(row) > 1 else row[0],
                "name": row[2] if len(row) > 2 else "",
            })
        
        logger.info(f"获取指数成分成功: index={index}, count={len(result)}", extra={"request_id": request_id})
        return {"index": index, "constituents": result}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取指数成分失败: index={index}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取指数成分失败: {str(e)}")


@router.get("/industry/classify")
async def get_industry_classify(request: Request):
    """获取行业分类"""
    request_id = getattr(request.state, "request_id", "unknown")
    
    try:
        rs = bs.query_stock_industry()
        
        if rs.error_code != "0":
            logger.error(f"查询行业分类失败: {rs.error_msg}", extra={"request_id": request_id})
            raise HTTPException(status_code=500, detail=f"查询失败: {rs.error_msg}")
        
        result = []
        industries = {}
        
        while rs.next():
            row = rs.get_row_data()
            code = row[1] if len(row) > 1 else ""
            industry = row[3] if len(row) > 3 else ""
            
            if industry:
                if industry not in industries:
                    industries[industry] = []
                industries[industry].append(code)
        
        # 转换为列表格式
        for industry, stocks in industries.items():
            result.append({
                "industry": industry,
                "stock_count": len(stocks),
            })
        
        logger.info(f"获取行业分类成功: count={len(result)}", extra={"request_id": request_id})
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取行业分类失败: error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取行业分类失败: {str(e)}")


@router.get("/finance/profit/{code}")
async def get_profit_data(request: Request, code: str):
    """
    获取盈利能力数据
    
    - **code**: 股票代码,如 sh.600519
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    try:
        # 补全股票代码前缀
        if not code.startswith(("sh.", "sz.")):
            if code.startswith("6"):
                code = f"sh.{code}"
            else:
                code = f"sz.{code}"
        
        # 查询盈利能力
        rs = bs.query_profit_data(code=code, year=2024, quarter=3)
        
        if rs.error_code != "0":
            # 尝试上一季度
            rs = bs.query_profit_data(code=code, year=2024, quarter=2)
        
        if rs.error_code != "0":
            logger.error(f"查询盈利能力失败: {rs.error_msg}", extra={"request_id": request_id})
            raise HTTPException(status_code=500, detail=f"查询失败: {rs.error_msg}")
        
        result = []
        while rs.next():
            row = rs.get_row_data()
            result.append({
                "code": row[0] if len(row) > 0 else code,
                "pub_date": row[1] if len(row) > 1 else "",
                "stat_date": row[2] if len(row) > 2 else "",
                "roe_avg": float(row[3]) if len(row) > 3 and row[3] else None,
                "np_margin": float(row[4]) if len(row) > 4 and row[4] else None,
                "gp_margin": float(row[5]) if len(row) > 5 and row[5] else None,
                "net_profit": float(row[6]) if len(row) > 6 and row[6] else None,
                "eps_ttm": float(row[7]) if len(row) > 7 and row[7] else None,
            })
        
        if not result:
            raise HTTPException(status_code=404, detail="未找到盈利数据")
        
        logger.info(f"获取盈利能力成功: code={code}", extra={"request_id": request_id})
        return result[0] if len(result) == 1 else result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取盈利能力失败: code={code}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取盈利能力失败: {str(e)}")
