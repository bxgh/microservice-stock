"""市场数据相关端点"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger("akshare-api.api.market")


@router.get("/dragon_tiger/daily")
async def get_dragon_tiger_daily(
    request: Request,
    date: Optional[str] = Query(None, description="日期 YYYY-MM-DD,默认最近交易日"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
):
    """
    获取龙虎榜数据
    
    - **date**: 单日查询
    - **start_date/end_date**: 范围查询 (优先)
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    
    try:
        logger.info(f"DEBUG MARKET: start={start_date}, end={end_date}, date={date}", extra={"request_id": request_id})
        if start_date and end_date:
            result = await service.get_lhb_detail(start_date, end_date)
            logger.info(f"获取龙虎榜(范围)成功: {start_date}~{end_date}, count={len(result)}", extra={"request_id": request_id})
        else:
            result = await service.get_lhb_detail(date, date)
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
    service = request.app.state.akshare_service
    
    try:
        info = await service.get_individual_info(code)
        
        if not info:
            raise HTTPException(status_code=404, detail=f"未找到股票: {code}")
        
        info["code"] = code
        logger.info(f"获取行业信息成功: code={code}", extra={"request_id": request_id})
        return info
        
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
    service = request.app.state.akshare_service
    
    try:
        result = await service.get_hot_rank(limit)
        
        # 补全 rank
        for i, item in enumerate(result):
            item["rank"] = i + 1
            
        logger.info(f"获取热门排行成功: limit={limit}, count={len(result)}", extra={"request_id": request_id})
        return result
        
    except Exception as e:
        logger.error(f"获取热门排行失败: error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取热门排行失败: {str(e)}")


@router.get("/capital_flow/{code}")
async def get_capital_flow(request: Request, code: str):
    """
    获取个股资金流向 (最近30日)
    
    - **code**: 股票代码,如 600519
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    
    try:
        result = await service.get_capital_flow(code)
        logger.info(f"获取资金流向成功: code={code}, count={len(result)}", extra={"request_id": request_id})
        return result
    except Exception as e:
        logger.error(f"获取资金流向失败: code={code}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取资金流向失败: {str(e)}")


@router.get("/block_trade/daily")
async def get_block_trade(
    request: Request,
    date: Optional[str] = Query(None, description="日期 YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
):
    """
    获取大宗交易数据 (支持单日或范围)
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    
    if start_date and end_date:
        s_date, e_date = start_date, end_date
    else:
        if not date:
            from datetime import datetime
            date = datetime.now().strftime("%Y-%m-%d")
        s_date, e_date = date, date
        
    try:
        result = await service.get_block_trade(s_date, e_date)
        logger.info(f"获取大宗交易成功: start={s_date}, end={e_date}, count={len(result)}", extra={"request_id": request_id})
        return result
    except Exception as e:
        logger.error(f"获取大宗交易失败: start={s_date}, end={e_date}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取大宗交易失败: {str(e)}")


@router.get("/margin/summary")
async def get_margin_summary(request: Request):
    """获取全市场两融汇总历史"""
    service = request.app.state.akshare_service
    result = await service.get_margin_summary()
    return result

@router.get("/margin/{code}")
async def get_margin_data(request: Request, code: str):
    """
    获取融资融券数据 (最近30日)
    
    - **code**: 股票代码,如 600519
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    
    try:
        result = await service.get_margin_data(code)
        logger.info(f"获取融资融券成功: code={code}, count={len(result)}", extra={"request_id": request_id})
        return result
    except Exception as e:
        logger.error(f"获取融资融券失败: code={code}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取融资融券失败: {str(e)}")
@router.get("/restricted/release")
async def get_restricted_release(
    request: Request,
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
):
    """
    获取限售股解禁数据
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    
    from datetime import datetime, timedelta
    if not start_date:
        start_date = datetime.now().strftime("%Y-%m-%d")
    if not end_date:
        # 默认看未来30天
        end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
    try:
        result = await service.get_restricted_release(start_date, end_date)
        logger.info(f"获取限售股解禁成功: start={start_date}, end={end_date}, count={len(result)}", extra={"request_id": request_id})
        return result
    except Exception as e:
        logger.error(f"获取限售股解禁失败: start={start_date}, end={end_date}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取限售股解禁失败: {str(e)}")
@router.get("/north/daily")
async def get_north_funds_daily(
    request: Request,
    date: str = Query(..., description="日期 YYYY-MM-DD"),
):
    """
    获取北向资金每日个股统计
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    
    try:
        result = await service.get_north_funds_daily(date)
        logger.info(f"获取北向资金成功: date={date}, count={len(result)}", extra={"request_id": request_id})
        return result
    except Exception as e:
        logger.error(f"获取北向资金失败: date={date}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取北向资金失败: {str(e)}")
@router.get("/dragon_tiger/institution")
async def get_dragon_tiger_inst(
    request: Request,
    date: str = Query(..., description="日期 YYYY-MM-DD"),
):
    """
    获取龙虎榜机构统计
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    
    try:
        result = await service.get_lhb_inst_stats(date)
        logger.info(f"获取龙虎榜机构统计成功: date={date}, count={len(result)}", extra={"request_id": request_id})
        return result
    except Exception as e:
        logger.error(f"获取龙虎榜机构统计失败: date={date}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取龙虎榜机构统计失败: {str(e)}")
@router.get("/north/history/{code}")
async def get_north_funds_history(
    request: Request,
    code: str,
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
):
    """
    获取个股北向持股历史
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    
    try:
        result = await service.get_north_funds_history(code, start_date, end_date)
        logger.info(f"获取个股北向历史成功: code={code}, start={start_date}, end={end_date}, count={len(result)}", extra={"request_id": request_id})
        return result
    except Exception as e:
        logger.error(f"获取个股北向历史失败: code={code}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取个股北向历史失败: {str(e)}")


@router.get("/suspension/daily")
async def get_suspension_daily(
    request: Request,
    date: str = Query(..., description="日期 YYYY-MM-DD"),
):
    """
    获取每日停复牌信息
    
    注意: 某些数据源可能只返回当前最新的停牌列表，而忽略日期参数。
    """
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    
    try:
        result = await service.get_suspension_daily(date)
        logger.info(f"获取停复牌信息成功: date={date}, count={len(result)}", extra={"request_id": request_id})
        return result
    except Exception as e:
        logger.error(f"获取停复牌信息失败: date={date}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"获取停复牌信息失败: {str(e)}")


@router.get("/market/breadth")
async def get_market_breadth(request: Request):
    """获取大盘涨跌分布与总市值 (实时)"""
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    try:
        result = await service.get_market_breadth()
        return result
    except Exception as e:
        logger.error(f"获取大盘分化数据失败: {e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/north/flow_summary")
async def get_north_flow_summary(request: Request):
    """获取北向资金汇总流向历史"""
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    try:
        result = await service.get_north_fund_flow_summary()
        return result
    except Exception as e:
        logger.error(f"获取北向汇总失败: {e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/index/daily")
async def get_index_daily(
    request: Request,
    symbol: str = Query(..., description="指数代码"),
    start_date: str = Query("19700101"),
    end_date: str = Query("20500101")
):
    """获取指数日线行情 (A股)"""
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    try:
        result = await service.get_index_daily(symbol, start_date, end_date)
        return result
    except Exception as e:
        logger.error(f"获取指数行情失败: {e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/index/sw_daily")
async def get_sw_index_daily(
    request: Request,
    symbol: str = Query(..., description="申万指数代码")
):
    """获取申万行业指数历史日线"""
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    try:
        result = await service.get_sw_index_daily(symbol)
        return result
    except Exception as e:
        logger.error(f"获取申万指数失败: {e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/index/us_daily")
async def get_us_index_daily(
    request: Request,
    symbol: str = Query(".NDX", description="美股指数代码")
):
    """获取美股指数历史行情"""
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    try:
        result = await service.get_us_index_daily(symbol)
        return result
    except Exception as e:
        logger.error(f"获取美股指数失败: {e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fund/etf_daily")
async def get_etf_daily(
    request: Request,
    symbol: str = Query(..., description="ETF代码"),
    start_date: str = Query("19700101"),
    end_date: str = Query("20500101")
):
    """获取 ETF 日线行情"""
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    try:
        result = await service.get_etf_daily(symbol, start_date, end_date)
        return result
    except Exception as e:
        logger.error(f"获取 ETF 行情失败: {e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/limit_pool")
async def get_limit_pool(
    request: Request,
    date: str = Query(..., description="日期 YYYY-MM-DD"),
    pool_type: str = Query("zt", description="池类型: zt(涨停), dt(跌停), zb(炸板), lian(连板)")
):
    """获取涨跌停池数据"""
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    try:
        result = await service.get_limit_pool(date, pool_type)
        logger.info(f"获取涨跌停池成功: date={date}, type={pool_type}, count={len(result)}", extra={"request_id": request_id})
        return result
    except Exception as e:
        logger.error(f"获取涨跌停池失败: date={date}, type={pool_type}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/index/sw_indicator")
async def get_sw_index_indicator(
    request: Request,
    symbol: str = Query("一级行业", description="申万指数类型: 市场表征, 一级行业, 二级行业, 风格指数"),
    start_date: str = Query("20000101", description="开始日期 YYYYMMDD"),
    end_date: str = Query("20500101", description="结束日期 YYYYMMDD")
):
    """获取申万行业指数分析数据 (含 PE/PB)"""
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    try:
        result = await service.get_sw_index_analysis(symbol, start_date, end_date)
        logger.info(f"获取申万指标成功: symbol={symbol}, count={len(result)}", extra={"request_id": request_id})
        return result
    except Exception as e:
        logger.error(f"获取申万指标失败: symbol={symbol}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/index/concept_ths")
async def get_concept_ths(
    request: Request,
    symbol: str = Query(..., description="概念名称 (如 人造肉)"),
    start_date: str = Query("20000101", description="开始日期 YYYYMMDD"),
    end_date: str = Query("20500101", description="结束日期 YYYYMMDD")
):
    """获取同花顺概念板块历史日线"""
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    try:
        result = await service.get_concept_index_ths(symbol, start_date, end_date)
        logger.info(f"获取概念板块行情成功: symbol={symbol}, count={len(result)}", extra={"request_id": request_id})
        return result
    except Exception as e:
        logger.error(f"获取概念板块行情失败: symbol={symbol}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/index/concept_names")
async def get_concept_names(request: Request):
    """获取同花顺概念板块名单"""
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    try:
        result = await service.get_concept_name_ths()
        logger.info(f"获取概念名单成功: count={len(result)}", extra={"request_id": request_id})
        return result
    except Exception as e:
        logger.error(f"获取概念名单失败: error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index/sw_sync")
async def sync_sw_index(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """手动同步申万行业数据到 ODS"""
    from app.services.l2_structural_service import L2StructuralService
    service = L2StructuralService()
    result = await service.sync_sw_index_daily(start_date, end_date)
    return result


@router.post("/index/concept_sync")
async def sync_concept_index(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """手动同步同花顺概念板块数据到 ODS"""
    from app.services.l2_structural_service import L2StructuralService
    service = L2StructuralService()
    result = await service.sync_concept_kline_daily(start_date, end_date)
    return result


@router.get("/stock/daily")
async def get_stock_daily(
    request: Request,
    symbol: str = Query(..., description="股票代码"),
    start_date: str = Query("19700101"),
    end_date: str = Query("20500101"),
    adjust: str = Query("", description="复权类型: hfq, qfq, ''")
):
    """获取个股日线行情 (A股)"""
    request_id = getattr(request.state, "request_id", "unknown")
    service = request.app.state.akshare_service
    try:
        result = await service.get_stock_daily(symbol, start_date, end_date, adjust)
        logger.info(f"获取个股行情成功: symbol={symbol}, count={len(result)}", extra={"request_id": request_id})
        return result
    except Exception as e:
        logger.error(f"获取个股行情失败: symbol={symbol}, error={e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))
