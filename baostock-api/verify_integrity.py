import asyncio
import datetime
import random
from app.utils.database import db

async def verify_integrity():
    print("Connecting to database...")
    await db.connect()
    
    try:
        # 1. Check total count
        count_res = await db.execute("SELECT COUNT(*) FROM stock_kline_daily")
        total_rows = count_res[0][0]
        print(f"Total K-line records: {total_rows}")
        
        # 2. Get all stock codes
        codes_res = await db.execute("SELECT DISTINCT code FROM stock_kline_daily")
        all_codes = [r[0] for r in codes_res]
        print(f"Total distinct stocks scanned: {len(all_codes)}")
        
        # 3. Sample check
        sample_size = 20
        sample_codes = random.sample(all_codes, min(sample_size, len(all_codes)))
        print(f"Sampling {len(sample_codes)} stocks for detailed analysis...")
        
        issues_found = []
        
        for code in sample_codes:
            # Fetch all data for this stock
            rows = await db.execute(
                "SELECT trade_date, open, high, low, close, volume FROM stock_kline_daily WHERE code=%s ORDER BY trade_date ASC",
                (code,)
            )
            
            if not rows:
                print(f"  [WARN] {code}: No data found")
                continue
                
            dates = []
            abnormal_price_count = 0
            abnormal_vol_count = 0
            
            for r in rows:
                t_date, open_p, high_p, low_p, close_p, vol = r
                dates.append(t_date)
                
                # Check price logic: High must be >= Low
                # Need to handle potential None or 0 values if any
                try:
                    if high_p is not None and low_p is not None:
                        if float(high_p) < float(low_p):
                            abnormal_price_count += 1
                except ValueError:
                    pass
                    
                # Check volume logic: Volume must be >= 0
                try:
                    if vol is not None and float(vol) < 0:
                        abnormal_vol_count += 1
                except ValueError:
                    pass

            # Check gaps
            gaps = 0
            max_gap_days = 0
            if len(dates) > 1:
                for i in range(1, len(dates)):
                    delta = (dates[i] - dates[i-1]).days
                    if delta > 10: # Gap larger than generic holiday (~10 days)
                        gaps += 1
                        if delta > max_gap_days:
                            max_gap_days = delta
                            
            print(f"  {code}: {len(rows)} records, Range: {dates[0]} to {dates[-1]}")
            
            if abnormal_price_count > 0:
                issues_found.append(f"{code}: {abnormal_price_count} records with High < Low")
            if abnormal_vol_count > 0:
                issues_found.append(f"{code}: {abnormal_vol_count} records with Volume < 0")
            if gaps > 0:
                print(f"    - Found {gaps} large gaps (>10 days). Max gap: {max_gap_days} days. (Could be suspension)")

        # 4. Check for duplicates in sample
        # (Assuming Primary Key prevents this, but verifying logical duplicates code+date)
        for code in sample_codes:
            dup_check = await db.execute(
                "SELECT trade_date, COUNT(*) as cnt FROM stock_kline_daily WHERE code=%s GROUP BY trade_date HAVING cnt > 1",
                (code,)
            )
            if dup_check:
                issues_found.append(f"{code}: Found {len(dup_check)} days with duplicate records")

        print("\n=== Verification Summary ===")
        if issues_found:
            print("Issues Found:")
            for issue in issues_found:
                print(f"  - {issue}")
        else:
            print("No logical data anomalies (High<Low, Vol<0, Duplicates) found in sample.")
            print("Note: Large date gaps may exist due to trading suspensions.")
            
    except Exception as e:
        print(f"Error during verification: {e}")
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(verify_integrity())
