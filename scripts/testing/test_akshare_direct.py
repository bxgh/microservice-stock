#!/usr/bin/env python3
"""
直接测试 AkShare Service 层是否返回真实数据
"""
import asyncio
import sys
sys.path.insert(0, '/home/ubuntu/microservice-stock/akshare-api')

from app.services.akshare_service import AkShareService

async def test_all_apis():
    """测试所有 AkShare 接口"""
    service = AkShareService()
    
    print("=" * 60)
    print("AkShare 真实数据测试")
    print("=" * 60)
    
    # 1. 财务摘要
    print("\n【1. 财务摘要】测试股票: 600519 (贵州茅台)")
    finance = await service.get_financial_abstract("600519")
    if finance:
        print(f"✓ 成功获取财务数据")
        print(f"  营业总收入: {finance.get('total_revenue')}")
        print(f"  净利润: {finance.get('net_profit')}")
        print(f"  ROE: {finance.get('roe')}")
        print(f"  报告期: {finance.get('report_date')}")
    else:
        print("✗ 获取失败")
    
    # 2. 实时估值
    print("\n【2. 实时估值】")
    valuation = await service.get_valuation_spot("600519")
    if valuation:
        print(f"✓ 成功获取估值数据")
        print(f"  名称: {valuation.get('name')}")
        print(f"  PE: {valuation.get('pe')}")
        print(f"  价格: {valuation.get('price')}")
        print(f"  总市值: {valuation.get('market_cap')}")
    else:
        print("✗ 获取失败")
    
    # 3. 龙虎榜
    print("\n【3. 龙虎榜】")
    lhb = await service.get_lhb_detail()
    if lhb and len(lhb) > 0:
        print(f"✓ 成功获取龙虎榜数据，共 {len(lhb)} 条")
        print(f"  示例: {lhb[0].get('name')} ({lhb[0].get('code')})")
        print(f"       涨跌幅: {lhb[0].get('change_pct')}%")
    else:
        print("✗ 获取失败或无数据")
    
    # 4. 个股信息
    print("\n【4. 个股信息】")
    info = await service.get_individual_info("600519")
    if info:
        print(f"✓ 成功获取个股信息")
        print(f"  行业: {info.get('industry')}")
        print(f"  名称: {info.get('name')}")
        print(f"  上市时间: {info.get('list_date')}")
    else:
        print("✗ 获取失败")
    
    # 5. 热门排行
    print("\n【5. 热门排行（成交额前3）】")
    hot = await service.get_hot_rank(limit=3)
    if hot and len(hot) > 0:
        print(f"✓ 成功获取热门排行，共 {len(hot)} 条")
        for i, stock in enumerate(hot[:3], 1):
            print(f"  {i}. {stock.get('name')} ({stock.get('code')})")
            print(f"     成交额: {stock.get('amount')}, 涨跌幅: {stock.get('change_pct')}%")
    else:
        print("✗ 获取失败")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_all_apis())
