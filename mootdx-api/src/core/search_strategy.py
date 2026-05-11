"""
Mootdx Matrix Search Strategy
Ported from 'GuaranteedSuccessStrategy' 100% success reference implementation.
"""
import logging
import asyncio
import pandas as pd
from typing import List, Dict, Optional, Tuple, Any
from mootdx.quotes import Quotes

logger = logging.getLogger("search-strategy")

class MatrixSearchStrategy:
    """
    智能矩阵搜索策略
    
    核心逻辑：
    1. 遍历预设的 "Proven Search Matrix" (已验证成功的参数组合)。
    2. 严格校验是否获取到了 09:25 的集合竞价数据。
    3. 在内存中进行去重和排序。
    """
    
    def __init__(self):
        # 完整复刻参考脚本中的搜索矩阵
        self.proven_search_matrix = [
            # 零优先级：针对小盘股/低频股的快速覆盖
            (0, 800, "quick_catch_latest"),
            (1500, 800, "quick_catch_mid"),
            
            # 第一优先级：万科A成功区域 (已验证有效)
            (3500, 800, "priority_vanke_pre"),
            (4000, 500, "priority_vanke_mid"),
            (4500, 800, "priority_vanke_post"),

            # 第二优先级：深度搜索区域
            (3000, 1000, "deep_search_1"),
            (5000, 1000, "deep_search_2"),
            (6000, 1200, "deep_search_3"),

            # 第三优先级：广域搜索
            (2000, 1500, "wide_search_1"),
            (7000, 1500, "wide_search_2"),
            (8000, 2000, "wide_search_3"),

            # 第四优先级：极限搜索
            (1000, 2000, "limit_search_1"),
            (10000, 3000, "limit_search_2"),
        ]
        
        self.target_time = "09:25"

    async def execute_post_market(self, client: Quotes, symbol: str, date: str) -> Tuple[Optional[List[Dict]], bool]:
        """
        执行盘后全量采集
        
        Args:
            client: Mootdx Quotes 客户端
            symbol: 股票代码
            date: 日期 YYYYMMDD
            
        Returns:
            (List[Dict], bool): (数据列表, 是否包含09:25数据)
        """
        # 标准化 symbol (移除 sh., sz. 等前缀)
        clean_symbol = symbol
        for prefix in ['sh.', 'sz.', 'sh', 'sz']:
            if symbol.lower().startswith(prefix):
                clean_symbol = symbol[len(prefix):]
                break
        
        logger.info(f"Executing matrix search for {clean_symbol} (original: {symbol}) on {date}")
        
        all_data = []
        found_0925 = False
        loop = asyncio.get_event_loop()
        
        for start_pos, offset, desc in self.proven_search_matrix:
            try:
                # 异步执行同步的 mootdx 调用
                batch_df = await loop.run_in_executor(
                    None,
                    lambda: client.transactions(
                        symbol=clean_symbol,
                        date=date,
                        start=start_pos,
                        offset=offset
                    )
                )
                
                if batch_df is not None and not batch_df.empty:
                    # Mootdx returns: time, price, vol, buyorsell
                    current_earliest = str(batch_df['time'].iloc[0])
                    
                    # Log snippet
                    # logger.debug(f"  {desc}: Got {len(batch_df)} rows, earliest={current_earliest}")
                    
                    if current_earliest <= self.target_time:
                        found_0925 = True
                        all_data.append(batch_df)
                        
                        # 智能停止：找到目标后，且有足够数据覆盖，就不再继续深搜，节省资源
                        # 参考脚本逻辑：if found_0925 and len(all_data) >= 2: break
                        # 但为了稳妥，我们至少拿到两批数据再停，或者只要涵盖09:25就认为核心目标达盛
                        # [FIX] user requires full data completeness. The matrix is sparse, so we MUST NOT break early.
                        # We need to collect all chunks defined in the matrix to fill the gaps.
                        # if len(all_data) >= 2:
                        #    break
                    else:
                        all_data.append(batch_df)
                
                await asyncio.sleep(0.1)  # 避免过快请求
                
            except Exception as e:
                logger.warning(f"  Search step {desc} failed for {symbol}: {e}")
                continue
                
        if not all_data:
            return None, False
            
        # 合并处理
        try:
            final_df = pd.concat(all_data, ignore_index=True)
            
            # 1. 去重
            final_df = final_df.drop_duplicates(subset=['time', 'price', 'vol'])
            
            # 2. 排序 (时间升序)
            final_df = final_df.sort_values('time', ascending=True).reset_index(drop=True)
            
            # 3. 最终校验
            earliest_time = str(final_df['time'].iloc[0])
            is_perfect = earliest_time <= self.target_time
            
            # 4. 转换格式
            # Mootdx returns columns: time, price, vol, buyorsell
            # We need standard format.
            # Convert to list of dicts
            records = final_df.to_dict('records')
            
            return records, is_perfect
            
        except Exception as e:
            logger.error(f"Error processing data frames for {symbol}: {e}")
            return None, False
