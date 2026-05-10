
try:
    from mootdx.utils import get_stock_market
    print(f"600519 -> {get_stock_market('600519')}")
    print(f"sh600519 -> {get_stock_market('sh600519')}")
    print(f"000001 -> {get_stock_market('000001')}")
    print(f"sz000001 -> {get_stock_market('sz000001')}")
except ImportError:
    print("Could not import get_stock_market")
