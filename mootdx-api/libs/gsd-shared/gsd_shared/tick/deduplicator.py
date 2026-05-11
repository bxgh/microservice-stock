from collections import deque
from typing import Dict, Any, Set, Optional

class TickDeduplicator:
    """
    Unified Tick Deduplicator (V2 - Occurrence Based)
    
    Strategy:
    1. If 'num'/'no'/'index' exists and > 0, use it as unique ID.
    2. Otherwise, use (time, price, volume, direction) + (occurrence count in batch).
    3. Re-assigns 'num' to item if missing to ensure ClickHouse stability.
    """
    
    def __init__(self, cache_size: int = 60000):
        self.cache_size = cache_size
        self.cache_deques: Dict[str, deque] = {}      # code -> deque[key]
        self.cache_sets: Dict[str, Set[str]] = {}      # code -> set[key]
        self._local_occ_counters: Dict[str, int] = {} # temp key -> count
        
    def reset_batch_counters(self):
        """Must be called before processing a new batch/poll round for a stock."""
        self._local_occ_counters.clear()

    def is_duplicate(self, code: str, item: Dict[str, Any]) -> bool:
        """
        Check if a tick item is a duplicate.
        
        Args:
            code: Stock code
            item: Tick item dict (Will be mutated to assign 'num' if missing)
        """
        key = self._make_key(item)
        return self.is_duplicate_by_key(code, key)

    def is_duplicate_by_key(self, code: str, key: str) -> bool:
        """
        Check if a pre-generated key is a duplicate and add to cache if not.
        """
        if code not in self.cache_sets:
            self.cache_sets[code] = set()
            self.cache_deques[code] = deque(maxlen=self.cache_size)

        if key in self.cache_sets[code]:
            return True
            
        # Add to cache
        if len(self.cache_deques[code]) >= self.cache_size:
            oldest = self.cache_deques[code].popleft()
            self.cache_sets[code].discard(oldest)
            
        self.cache_deques[code].append(key)
        self.cache_sets[code].add(key)
        
        return False
    
    def _make_key(self, item: Dict[str, Any], increment: bool = True) -> str:
        """
        Generate deduplication key.
        """
        # 1. 提取时间/价/量基础指纹
        t = item.get('time', '')
        p = item.get('price', 0)
        v = item.get('vol', item.get('volume', 0))
        d = item.get('type', item.get('buyorsell', 'NEUTRAL'))
        base_key = f"{t}|{p}|{v}|{d}"

        # 2. Check for API-provided unique ID.
        api_num = item.get('num', item.get('no', item.get('index')))
        
        # 3. 区分原始 ID 与我们分配的内部序号
        is_internal_num = False
        if api_num is not None:
            try:
                num_val = int(api_num)
                # 经验值：API 提供的成交序号通常很大，或者是连续的全局序号。
                # 我们分配的 'num' 在单批次内通常从 1 开始。
                # 如果 num 刚好等于当前 batch 的内部计数器，很有可能是同一对象被重复调用 is_duplicate。
                occ_now = self._local_occ_counters.get(base_key, 0)
                if num_val == occ_now and num_val > 0:
                    is_internal_num = True
            except (ValueError, TypeError):
                pass

        # 4. 如果是确凿的外部 ID，直接返回
        if api_num and not is_internal_num:
            # 只有当 ID 足够大或者明确不是我们刚分配的序号时才使用
            if int(api_num) > 50000:
                return f"ID|{api_num}"
        
        # 5. 内部出现次数逻辑 (Occurrence-based)
        occ = self._local_occ_counters.get(base_key, 0)
        
        if increment:
            # 幂等保护：如果这个 item 字典对象已经在此批次分配过同一个序号，不要再次自增
            if is_internal_num:
                return f"VAL|{base_key}|{occ-1}"
                
            self._local_occ_counters[base_key] = occ + 1
            # 分配 num 并持久化到字典中
            item['num'] = occ + 1
            
        return f"VAL|{base_key}|{occ}"
    
    def clear(self, code: str = None):
        """Clear cache for a specific code or all codes"""
        if code:
            self.cache_sets.pop(code, None)
            self.cache_deques.pop(code, None)
        else:
            self.cache_sets.clear()
            self.cache_deques.clear()
        self._local_occ_counters.clear()
