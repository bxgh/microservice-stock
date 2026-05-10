import logging
import time
import pandas as pd
from mootdx.quotes import Quotes

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MagicVerifier")

class MagicStrategy:
    def __init__(self):
        # The "Proven" Matrix from the user's script
        self.proven_search_matrix = [
            (3500, 800, "万科A前区域"),
            (4000, 500, "万科A原成功"),
            (4500, 800, "万科A后区域"),
            (3000, 1000, "深度区域1"),
            (5000, 1000, "深度区域2"),
            (6000, 1200, "深度区域3"),
            (2000, 1500, "广域区域1"),
            (7000, 1500, "广域区域2"),
            (8000, 2000, "广域区域3"),
            (1000, 2000, "极限区域1"),
            (10000, 3000, "极限区域2"),
        ]
        self.target_time = "09:25"

    def execute_search(self, symbol, date, server=None):
        logger.info(f"🚀 Verifying {symbol} on {date} [Server: {server or 'Auto'}]")
        
        try:
            # Replicate the client factory call exactly
            kwargs = {
                'market': 'std',
                'multithread': True,
                'heartbeat': True,
                'block': False
            }
            if server:
                kwargs['server'] = server
                kwargs['bestip'] = False
            else:
                kwargs['bestip'] = True # Default behavior if not specified

            client = Quotes.factory(**kwargs)
        except Exception as e:
            logger.error(f"❌ Client init failed: {e}")
            return False

        all_data = []
        found_target = False

        for i, (start, offset, desc) in enumerate(self.proven_search_matrix):
            logger.info(f"Step {i+1}: {desc} (start={start}, offset={offset})")
            try:
                data = client.transactions(symbol=symbol, date=date, start=start, offset=offset)
                
                if data is not None and not data.empty:
                    earliest = data['time'].min()
                    latest = data['time'].max()
                    count = len(data)
                    logger.info(f"  -> Got {count} rows. Time: {earliest} - {latest}")

                    if earliest <= self.target_time:
                        found_target = True
                        logger.info(f"  🎯 FOUND TARGET {self.target_time}!")
                        return True
                else:
                    logger.info("  -> No Data")
                
                time.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"  -> Error: {e}")

        logger.info("❌ Search finished. Target NOT found.")
        return False

if __name__ == "__main__":
    verifier = MagicStrategy()
    stock = "600010" # Baosteel (The problem stock)
    date = "20260106"
    
    # 1. Try with Auto Discovery (Default)
    print("\n--- TEST 1: Auto Discovery (Original Script Logic) ---")
    verifier.execute_search(stock, date)
    
    # 2. Try with Known Working Huawei Server (Limited)
    print("\n--- TEST 2: Fixed IP 175.6.5.153 (Huawei) ---")
    verifier.execute_search(stock, date, server=('175.6.5.153', 7709))
    
    # 3. Try with Known Deep Server (If accessible)
    print("\n--- TEST 3: Fixed IP 119.147.212.81 (Deep History) ---")
    verifier.execute_search(stock, date, server=('119.147.212.81', 7709))
