import pywencai
import pandas as pd

def test_wencai():
    print("Testing pywencai directly...")
    try:
        df = pywencai.get(query="今日涨停", perpage=10)
        print("Result type:", type(df))
        if df is not None:
            print("Columns:", df.columns.tolist())
            print("Data shape:", df.shape)
        else:
            print("Result is None")
    except Exception as e:
        print(f"Error caught: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_wencai()
