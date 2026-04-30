import logging
from typing import List, Optional, Tuple, Dict, Any
from fastapi import HTTPException
from app.utils.database import db
from app.models.diary import DiaryEntryCreate, DiaryEntryUpdate

logger = logging.getLogger("gateway.service.diary")

class DiaryService:
    async def get_stats(self, user_id: int) -> Dict[str, Any]:
        # 1. 本月记录天数 (DISTINCT entry_date in current month)
        days_query = """
            SELECT COUNT(DISTINCT entry_date) as c 
            FROM diary_entry 
            WHERE user_id = %s AND deleted_at IS NULL 
            AND entry_date >= DATE_FORMAT(NOW(), '%%Y-%%m-01')
        """
        days_res = await db.execute(days_query, (user_id,))
        monthly_days = days_res[0]["c"] if days_res else 0

        # 2. 错题本总数 (Linked to tag category=2)
        error_query = """
            SELECT COUNT(DISTINCT d.id) as c
            FROM diary_entry d
            JOIN diary_tag dt ON d.id = dt.diary_id
            JOIN diary_tag_dict t ON dt.tag_id = t.id
            WHERE d.user_id = %s AND d.deleted_at IS NULL AND t.category = 2
        """
        error_res = await db.execute(error_query, (user_id,))
        error_book_count = error_res[0]["c"] if error_res else 0

        # 3. 最近心情
        mood_query = """
            SELECT mood FROM diary_entry 
            WHERE user_id = %s AND deleted_at IS NULL AND mood IS NOT NULL
            ORDER BY entry_date DESC, created_at DESC LIMIT 1
        """
        mood_res = await db.execute(mood_query, (user_id,))
        latest_mood = mood_res[0]["mood"] if mood_res else None

        # 4. 心情分布
        dist_query = """
            SELECT mood, COUNT(*) as count
            FROM diary_entry
            WHERE user_id = %s AND deleted_at IS NULL AND mood IS NOT NULL
            GROUP BY mood
        """
        mood_distribution = await db.execute(dist_query, (user_id,))

        return {
            "monthly_days": monthly_days,
            "error_book_count": error_book_count,
            "latest_mood": latest_mood,
            "mood_distribution": mood_distribution
        }

    async def get_list(self, user_id: int, page: int = 1, size: int = 20, 
                       tag: Optional[str] = None, entry_type: Optional[int] = None, 
                       search: Optional[str] = None) -> Tuple[List[Dict[str, Any]], int]:
        offset = (page - 1) * size
        
        base_query = """
            FROM diary_entry d
            WHERE d.user_id = %s AND d.deleted_at IS NULL
        """
        params = [user_id]
        
        if entry_type is not None:
            base_query += " AND d.entry_type = %s"
            params.append(entry_type)
            
        if tag:
            base_query += """
                AND EXISTS (
                    SELECT 1 FROM diary_tag dt
                    JOIN diary_tag_dict t ON dt.tag_id = t.id
                    WHERE dt.diary_id = d.id AND t.name = %s
                )
            """
            params.append(tag)
            
        if search:
            # Simple LIKE search or FULLTEXT match
            base_query += " AND MATCH(d.title, d.content) AGAINST(%s IN NATURAL LANGUAGE MODE)"
            params.append(search)

        count_query = f"SELECT COUNT(*) as total {base_query}"
        count_res = await db.execute(count_query, tuple(params))
        total = count_res[0]["total"] if count_res else 0
        
        if total == 0:
            return [], 0
            
        select_query = f"""
            SELECT d.id, d.entry_date, d.entry_type, d.mood, d.title, d.excerpt, 
                   d.word_count, d.is_pinned, d.mp_published_count, d.created_at, d.updated_at
            {base_query}
            ORDER BY d.is_pinned DESC, d.entry_date DESC, d.created_at DESC
            LIMIT %s OFFSET %s
        """
        
        params.extend([size, offset])
        entries = await db.execute(select_query, tuple(params))
        
        # Load stocks and tags for these entries
        if entries:
            diary_ids = [e["id"] for e in entries]
            format_strings = ','.join(['%s'] * len(diary_ids))
            
            # Fetch stocks
            stocks_query = f"""
                SELECT ds.diary_id, s.ts_code, s.name, s.market, s.industry_sw
                FROM diary_stock ds
                JOIN stock_info s ON ds.stock_id = s.id
                WHERE ds.diary_id IN ({format_strings})
            """
            stocks_res = await db.execute(stocks_query, tuple(diary_ids))
            
            # Fetch tags
            tags_query = f"""
                SELECT dt.diary_id, t.id, t.name, t.category, t.color
                FROM diary_tag dt
                JOIN diary_tag_dict t ON dt.tag_id = t.id
                WHERE dt.diary_id IN ({format_strings})
            """
            tags_res = await db.execute(tags_query, tuple(diary_ids))
            
            # Attach to entries
            entry_dict = {e["id"]: e for e in entries}
            for e in entries:
                e["stocks"] = []
                e["tags"] = []
                
            for s in stocks_res:
                if s["diary_id"] in entry_dict:
                    entry_dict[s["diary_id"]]["stocks"].append(s)
                    
            for t in tags_res:
                if t["diary_id"] in entry_dict:
                    entry_dict[t["diary_id"]]["tags"].append(t)
                    
        return list(entries), total

    async def get_by_id(self, user_id: int, diary_id: int) -> Dict[str, Any]:
        query = """
            SELECT id, user_id, entry_date, entry_type, mood, title, content, 
                   excerpt, word_count, visibility, is_pinned, mp_published_count, 
                   created_at, updated_at
            FROM diary_entry 
            WHERE id = %s AND user_id = %s AND deleted_at IS NULL
        """
        res = await db.execute(query, (diary_id, user_id))
        if not res:
            raise HTTPException(status_code=404, detail="Diary entry not found")
            
        entry = res[0]
        
        # Fetch stocks
        stocks_query = """
            SELECT s.ts_code, s.name, s.market, s.industry_sw
            FROM diary_stock ds
            JOIN stock_info s ON ds.stock_id = s.id
            WHERE ds.diary_id = %s
        """
        entry["stocks"] = await db.execute(stocks_query, (diary_id,))
        
        # Fetch tags
        tags_query = """
            SELECT t.id, t.name, t.category, t.color
            FROM diary_tag dt
            JOIN diary_tag_dict t ON dt.tag_id = t.id
            WHERE dt.diary_id = %s
        """
        entry["tags"] = await db.execute(tags_query, (diary_id,))
        
        return entry

    async def _handle_tags(self, user_id: int, diary_id: int, tag_names: List[str]):
        if not tag_names:
            return
            
        for name in tag_names:
            # Insert tag into dictionary if not exists (either global or user specific)
            # We try to find global first, if not exists, insert as user tag
            check_query = "SELECT id FROM diary_tag_dict WHERE name = %s AND (owner_user_id IS NULL OR owner_user_id = %s) LIMIT 1"
            res = await db.execute(check_query, (name, user_id))
            
            tag_id = None
            if res:
                tag_id = res[0]["id"]
            else:
                # Insert new user tag
                insert_tag_q = "INSERT INTO diary_tag_dict (owner_user_id, name) VALUES (%s, %s)"
                tag_id = await db.execute_insert(insert_tag_q, (user_id, name))
                
            if tag_id:
                # Associate tag
                assoc_q = "INSERT IGNORE INTO diary_tag (diary_id, tag_id) VALUES (%s, %s)"
                await db.execute(assoc_q, (diary_id, tag_id))
                
                # Increment usage
                update_usage_q = "UPDATE diary_tag_dict SET usage_count = usage_count + 1 WHERE id = %s"
                await db.execute(update_usage_q, (tag_id,))

    async def _handle_stocks(self, diary_id: int, ts_codes: List[str]):
        if not ts_codes:
            return
            
        for ts_code in ts_codes:
            # Find stock_id
            check_query = "SELECT id FROM stock_info WHERE ts_code = %s LIMIT 1"
            res = await db.execute(check_query, (ts_code,))
            if res:
                stock_id = res[0]["id"]
                # Associate stock
                assoc_q = "INSERT IGNORE INTO diary_stock (diary_id, stock_id, ts_code) VALUES (%s, %s, %s)"
                await db.execute(assoc_q, (diary_id, stock_id, ts_code))

    async def create(self, user_id: int, data: DiaryEntryCreate) -> Dict[str, Any]:
        word_count = len(data.content)
        excerpt = data.content[:60] if data.content else None
        
        insert_query = """
            INSERT INTO diary_entry 
            (user_id, entry_date, entry_type, mood, title, content, content_format, 
             excerpt, word_count, visibility, is_pinned, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """
        params = (
            user_id, data.entry_date, data.entry_type, data.mood, 
            data.title, data.content, data.content_format,
            excerpt, word_count, data.visibility, int(data.is_pinned)
        )
        
        diary_id = await db.execute_insert(insert_query, params)
        
        # Update user diary count
        await db.execute("UPDATE sys_user SET diary_count = diary_count + 1 WHERE id = %s", (user_id,))
        
        if data.tags:
            await self._handle_tags(user_id, diary_id, data.tags)
            
        if data.stocks:
            await self._handle_stocks(diary_id, data.stocks)
            
        return await self.get_by_id(user_id, diary_id)

    async def update(self, user_id: int, diary_id: int, data: DiaryEntryUpdate) -> Dict[str, Any]:
        # Check if exists
        check_query = "SELECT id FROM diary_entry WHERE id = %s AND user_id = %s AND deleted_at IS NULL"
        if not await db.execute(check_query, (diary_id, user_id)):
            raise HTTPException(status_code=404, detail="Diary entry not found")
            
        update_fields = []
        params = []
        
        if data.entry_type is not None:
            update_fields.append("entry_type = %s")
            params.append(data.entry_type)
        if data.mood is not None:
            update_fields.append("mood = %s")
            params.append(data.mood)
        if data.title is not None:
            update_fields.append("title = %s")
            params.append(data.title)
        if data.content is not None:
            update_fields.append("content = %s")
            params.append(data.content)
            update_fields.append("word_count = %s")
            params.append(len(data.content))
            update_fields.append("excerpt = %s")
            params.append(data.content[:60])
        if data.visibility is not None:
            update_fields.append("visibility = %s")
            params.append(data.visibility)
        if data.is_pinned is not None:
            update_fields.append("is_pinned = %s")
            params.append(int(data.is_pinned))
            
        if update_fields:
            update_fields.append("updated_at = NOW()")
            update_query = f"UPDATE diary_entry SET {', '.join(update_fields)} WHERE id = %s AND user_id = %s"
            params.extend([diary_id, user_id])
            await db.execute(update_query, tuple(params))
            
        # Re-handle tags if provided
        if data.tags is not None:
            await db.execute("DELETE FROM diary_tag WHERE diary_id = %s", (diary_id,))
            await self._handle_tags(user_id, diary_id, data.tags)
            
        # Re-handle stocks if provided
        if data.stocks is not None:
            await db.execute("DELETE FROM diary_stock WHERE diary_id = %s", (diary_id,))
            await self._handle_stocks(diary_id, data.stocks)
            
        return await self.get_by_id(user_id, diary_id)

    async def delete(self, user_id: int, diary_id: int):
        update_query = "UPDATE diary_entry SET deleted_at = NOW() WHERE id = %s AND user_id = %s AND deleted_at IS NULL"
        await db.execute(update_query, (diary_id, user_id))
        
        # Update user diary count (recalculate)
        count_query = "SELECT COUNT(*) as c FROM diary_entry WHERE user_id = %s AND deleted_at IS NULL"
        res = await db.execute(count_query, (user_id,))
        count = res[0]["c"] if res else 0
        await db.execute("UPDATE sys_user SET diary_count = %s WHERE id = %s", (count, user_id))

diary_service = DiaryService()
