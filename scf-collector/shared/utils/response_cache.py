# -*- coding: utf-8 -*-
"""
[E15-M6-T2] 应用层 LLM 响应缓存管理器 response_cache.py
实现基于 MD5 签名的 MySQL 缓存读取、安全入库和异步热度统计。
"""

import json
import re
import hashlib
import logging
import asyncio
from typing import Optional, Dict, Any
from shared.db.connection import execute_query

logger = logging.getLogger(__name__)

class ResponseCache:
    @classmethod
    def generate_key(cls, prompt_name: str, prompt_version: str, model_name: str, user_prompt: str) -> str:
        """
        根据 prompt 特征和 user_prompt 生成高精度的 32 位 MD5 签名作为唯一缓存 Key。
        在哈希前自动对 user_prompt 的空白与换行进行一致性规范化，防范无关微小格式偏移导致缓存失配。
        """
        # 1. 替换连续空白为单空格并去除首尾空白
        normalized_prompt = re.sub(r'\s+', ' ', user_prompt).strip()
        
        # 2. 拼接特征签名原字符串
        key_src = f"{prompt_name}:{prompt_version}:{model_name}:{normalized_prompt}"
        
        # 3. 计算并返回 MD5 哈希
        return hashlib.md5(key_src.encode('utf-8')).hexdigest()

    @classmethod
    async def get(cls, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        根据 cache_key 查询 MySQL 响应缓存。
        若命中则异步增加命中热度并返回还原的字典响应。
        """
        sql = "SELECT response_content FROM meta_response_cache WHERE cache_key = %s"
        try:
            rows = await execute_query(sql, (cache_key,), is_select=True)
            if rows:
                content_str = rows[0]['response_content']
                # 异步自增命中次数，不阻断主链路返回
                asyncio.create_task(cls.increment_hit(cache_key))
                
                logger.info(f"[ResponseCache] Cache HIT for key: {cache_key}")
                return json.loads(content_str)
            return None
        except Exception as e:
            logger.error(f"[ResponseCache] Read cache database failed for key {cache_key}: {e}")
            return None

    @classmethod
    async def set(cls, cache_key: str, prompt_name: str, prompt_version: str, model_name: str, response_dict: Dict[str, Any]):
        """
        静默将 LLM 生成的字典响应序列化后存入物理缓存表中，支持主键幂等更新。
        """
        sql = """
        INSERT INTO meta_response_cache (
            cache_key, prompt_name, prompt_version, model_name, response_content, hit_count
        ) VALUES (%s, %s, %s, %s, %s, 0)
        ON DUPLICATE KEY UPDATE 
            response_content = VALUES(response_content)
        """
        try:
            content_str = json.dumps(response_dict, ensure_ascii=False)
            await execute_query(
                sql, 
                (cache_key, prompt_name, prompt_version, model_name, content_str), 
                is_select=False
            )
            logger.info(f"[ResponseCache] Cache SET successfully for key: {cache_key}")
        except Exception as e:
            logger.error(f"[ResponseCache] Save cache database failed for key {cache_key}: {e}")

    @classmethod
    async def increment_hit(cls, cache_key: str):
        """
        异步自增物理表的命中计数值与最后命中时间
        """
        sql = """
        UPDATE meta_response_cache 
        SET hit_count = hit_count + 1, last_hit_at = CURRENT_TIMESTAMP 
        WHERE cache_key = %s
        """
        try:
            await execute_query(sql, (cache_key,), is_select=False)
        except Exception as e:
            logger.error(f"[ResponseCache] Async increment hit count failed for key {cache_key}: {e}")

    @classmethod
    async def evict_cold_data(cls, days: int = 30):
        """
        物理淘汰超过 30 天未被任何业务命中的冷数据，保障数据库轻量整洁。
        """
        sql = "DELETE FROM meta_response_cache WHERE last_hit_at < DATE_SUB(NOW(), INTERVAL %s DAY)"
        try:
            await execute_query(sql, (days,), is_select=False)
            logger.info(f"[ResponseCache] Successfully evicted cold cache data older than {days} days.")
        except Exception as e:
            logger.error(f"[ResponseCache] Cold cache data eviction failed: {e}")
