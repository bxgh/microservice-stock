import logging
import time
import os
import markdown
import re
from typing import Optional, List, Dict, Any
from app.utils.database import db
from app.models.diary import DiaryEntryCreate, DiaryEntryUpdate, DiaryPublishMPRequest
from app.services.wechat_service import wechat_service

logger = logging.getLogger("gateway.service.diary")

class DiaryService:
    """日记服务类，处理日记的增删改查及同步逻辑"""

    async def get_list(self, user_id: int, page: int = 1, size: int = 20, 
                          tag: Optional[str] = None, entry_type: Optional[int] = None,
                          search: Optional[str] = None) -> tuple:
        """获取日记列表"""
        offset = (page - 1) * size
        params = [user_id]
        where_clauses = ["user_id = %s", "deleted_at IS NULL"]
        
        if tag:
            where_clauses.append("id IN (SELECT diary_id FROM diary_tag dt JOIN diary_tag_dict td ON dt.tag_id = td.id WHERE td.name = %s)")
            params.append(tag)
        if entry_type:
            where_clauses.append("entry_type = %s")
            params.append(entry_type)
        if search:
            where_clauses.append("(title LIKE %s OR content LIKE %s)")
            params.extend([f"%{search}%", f"%{search}%"])
            
        where_str = " AND ".join(where_clauses)
        
        count_query = f"SELECT COUNT(*) as total FROM diary_entry WHERE {where_str}"
        count_res = await db.execute(count_query, tuple(params))
        total = count_res[0]['total']
        
        list_query = f"""
            SELECT * FROM diary_entry 
            WHERE {where_str} 
            ORDER BY entry_date DESC, created_at DESC 
            LIMIT %s OFFSET %s
        """
        list_params = params + [size, offset]
        items = await db.execute(list_query, tuple(list_params))
        
        if items:
            ids = [item['id'] for item in items]
            stocks_query = """
                SELECT ds.diary_id as entry_id, s.ts_code, s.name 
                FROM diary_stock ds
                JOIN stock_info s ON ds.ts_code = s.ts_code
                WHERE ds.diary_id IN ({})
            """.format(",".join(["%s"] * len(ids)))
            stocks_res = await db.execute(stocks_query, tuple(ids))
            
            tags_query = """
                SELECT dt.diary_id as entry_id, td.id, td.name, td.category, td.color
                FROM diary_tag dt
                JOIN diary_tag_dict td ON dt.tag_id = td.id
                WHERE dt.diary_id IN ({})
            """.format(",".join(["%s"] * len(ids)))
            tags_res = await db.execute(tags_query, tuple(ids))
            
            for item in items:
                item['stocks'] = [s for s in stocks_res if s['entry_id'] == item['id']]
                item['tags'] = [t for t in tags_res if t['entry_id'] == item['id']]
                
        return items, total

    async def get_by_id(self, user_id: int, entry_id: int) -> Optional[Dict[str, Any]]:
        """获取日记详情"""
        query = "SELECT * FROM diary_entry WHERE id = %s AND user_id = %s AND deleted_at IS NULL"
        res = await db.execute(query, (entry_id, user_id))
        if not res:
            return None
        
        item = res[0]
        stocks_query = """
            SELECT s.ts_code, s.name, s.market, s.industry_sw
            FROM diary_stock ds
            JOIN stock_info s ON ds.ts_code = s.ts_code
            WHERE ds.diary_id = %s
        """
        item['stocks'] = await db.execute(stocks_query, (entry_id,))
        
        tags_query = """
            SELECT td.id, td.name, td.category, td.color
            FROM diary_tag dt
            JOIN diary_tag_dict td ON dt.tag_id = td.id
            WHERE dt.diary_id = %s
        """
        item['tags'] = await db.execute(tags_query, (entry_id,))
        return item

    async def create(self, user_id: int, data: DiaryEntryCreate) -> Dict[str, Any]:
        """创建日记"""
        word_count = len(data.content)
        excerpt = data.content[:200].replace("\n", " ").strip()
        
        query = """
            INSERT INTO diary_entry (
                user_id, entry_date, entry_type, mood, title, content, 
                content_format, excerpt, word_count, visibility, is_pinned
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            user_id, data.entry_date, data.entry_type, data.mood, data.title, 
            data.content, data.content_format, excerpt, word_count, 
            data.visibility, 1 if data.is_pinned else 0
        )
        entry_id = await db.execute_insert(query, params)
        
        if data.stocks:
            stock_info_q = "SELECT id, ts_code FROM stock_info WHERE ts_code IN ({})".format(",".join(["%s"] * len(data.stocks)))
            stocks_found = await db.execute(stock_info_q, tuple(data.stocks))
            if stocks_found:
                stock_rel_q = "INSERT INTO diary_stock (diary_id, stock_id, ts_code) VALUES (%s, %s, %s)"
                stock_rel_params = [(entry_id, s['id'], s['ts_code']) for s in stocks_found]
                await db.execute_many(stock_rel_q, stock_rel_params)
            
        if data.tags:
            tag_query = "SELECT id FROM diary_tag_dict WHERE name IN ({})".format(",".join(["%s"] * len(data.tags)))
            tags_found = await db.execute(tag_query, tuple(data.tags))
            if tags_found:
                rel_query = "INSERT INTO diary_tag (diary_id, tag_id) VALUES (%s, %s)"
                rel_params = [(entry_id, t['id']) for t in tags_found]
                await db.execute_many(rel_query, rel_params)
                
        return await self.get_by_id(user_id, entry_id)

    async def update(self, user_id: int, entry_id: int, data: DiaryEntryUpdate) -> Dict[str, Any]:
        """更新日记"""
        updates = []
        params = []
        update_fields = data.model_dump(exclude_unset=True)
        for field, value in update_fields.items():
            if field in ['stocks', 'tags']: continue
            updates.append(f"{field} = %s")
            params.append(value)
            
        if updates:
            if 'content' in update_fields:
                updates.append("word_count = %s")
                params.append(len(update_fields['content']))
                updates.append("excerpt = %s")
                params.append(update_fields['content'][:200].replace("\n", " ").strip())
            params.extend([entry_id, user_id])
            query = f"UPDATE diary_entry SET {', '.join(updates)} WHERE id = %s AND user_id = %s"
            await db.execute(query, tuple(params))
            
        if 'stocks' in update_fields:
            await db.execute("DELETE FROM diary_stock WHERE diary_id = %s", (entry_id,))
            if update_fields['stocks']:
                stock_info_q = "SELECT id, ts_code FROM stock_info WHERE ts_code IN ({})".format(",".join(["%s"] * len(update_fields['stocks'])))
                stocks_found = await db.execute(stock_info_q, tuple(update_fields['stocks']))
                if stocks_found:
                    stock_rel_q = "INSERT INTO diary_stock (diary_id, stock_id, ts_code) VALUES (%s, %s, %s)"
                    stock_rel_params = [(entry_id, s['id'], s['ts_code']) for s in stocks_found]
                    await db.execute_many(stock_rel_q, stock_rel_params)
                
        if 'tags' in update_fields:
            await db.execute("DELETE FROM diary_tag WHERE diary_id = %s", (entry_id,))
            if update_fields['tags']:
                tag_query = "SELECT id FROM diary_tag_dict WHERE name IN ({})".format(",".join(["%s"] * len(update_fields['tags'])))
                tags_found = await db.execute(tag_query, tuple(update_fields['tags']))
                if tags_found:
                    rel_query = "INSERT INTO diary_tag (diary_id, tag_id) VALUES (%s, %s)"
                    rel_params = [(entry_id, t['id']) for t in tags_found]
                    await db.execute_many(rel_query, rel_params)
                    
        return await self.get_by_id(user_id, entry_id)

    async def delete(self, user_id: int, entry_id: int) -> bool:
        """逻辑删除"""
        query = "UPDATE diary_entry SET deleted_at = NOW() WHERE id = %s AND user_id = %s"
        affected = await db.execute(query, (entry_id, user_id))
        return affected > 0

    async def get_stats(self, user_id: int) -> Dict[str, Any]:
        """获取统计"""
        monthly_q = """
            SELECT COUNT(DISTINCT entry_date) as count 
            FROM diary_entry 
            WHERE user_id = %s AND deleted_at IS NULL AND entry_date >= DATE_FORMAT(NOW() ,'%%Y-%%m-01')
        """
        monthly_res = await db.execute(monthly_q, (user_id,))
        mood_q = "SELECT mood FROM diary_entry WHERE user_id = %s AND deleted_at IS NULL ORDER BY entry_date DESC LIMIT 1"
        mood_res = await db.execute(mood_q, (user_id,))
        dist_q = "SELECT mood, COUNT(*) as count FROM diary_entry WHERE user_id = %s AND deleted_at IS NULL GROUP BY mood"
        dist_res = await db.execute(dist_q, (user_id,))
        
        return {
            "monthly_days": monthly_res[0]['count'] if monthly_res else 0,
            "latest_mood": mood_res[0]['mood'] if mood_res else None,
            "mood_distribution": dist_res or []
        }

    async def publish_to_mp(self, user_id: int, data: DiaryPublishMPRequest) -> Dict[str, Any]:
        """同步日记到微信公众号草稿箱 (认真排版终极版)"""
        diary = await self.get_by_id(user_id, data.entry_id)
        if not diary:
            raise Exception("Diary not found")
        
        account_query = "SELECT id, mp_appid FROM mp_account LIMIT 1"
        accounts = await db.execute(account_query)
        if not accounts:
            raise Exception("No linked WeChat Official Account found")
        account = accounts[0]
        
        source_content = data.content if data.content else diary["content"]
        
        # 1. 源码清理：物理切除只含列表符号的空行
        source_content = re.sub(r'^\s*[*+-]\s*$', '', source_content, flags=re.MULTILINE)
        source_content = re.sub(r'\n\s*\n', '\n\n', source_content.strip())
        
        # 2. 基础 Markdown 转 HTML
        html_content = markdown.markdown(source_content, extensions=['extra', 'codehilite', 'toc'])
        
        # 3. HTML 深度净化：清理所有无效标签
        html_content = re.sub(r'<(p|li)[^>]*>\s*(?:&nbsp;|\s)*</\1>', '', html_content)
        
        # 4. 样式变量定义
        font_serif = "'Optima', 'Source Serif Pro', 'PingFang SC', 'STSongti-SC-Regular', serif"
        color_gold = "#d4a76a"
        
        # 5. 标签样式硬注入
        html_content = html_content.replace("<p>", f'<p style="font-family: {font_serif}; font-size: 14px; line-height: 1.6; color: #353535; margin: 0 0 10px 0; text-align: justify;">')
        def h3_replacer(match):
            title_text = match.group(1)
            return f'<h3 style="font-family: {font_serif}; font-size: 16px; font-weight: bold; color: #222; margin: 20px 0 6px 0; padding-left: 10px; border-left: 3px solid {color_gold}; line-height: 1.4;"><span style="color: {color_gold}; margin-right: 4px;">§</span>{title_text}</h3>'
        html_content = re.sub(r"<h3>(.*?)</h3>", h3_replacer, html_content)
        html_content = html_content.replace("<ul>", f'<ul style="margin: 0 0 12px 0; padding-left: 20px; font-family: {font_serif}; font-size: 14px; color: #353535;">')
        html_content = html_content.replace("<li>", f'<li style="margin: 0 0 4px 0; padding: 0;">')
        html_content = html_content.replace("<blockquote>", f'<blockquote style="border-left: 3px solid #eee; padding: 6px 12px; color: #777; background-color: #f9f9f9; margin: 15px 0; font-family: {font_serif}; font-size: 13px;">')
        
        # 6. 特殊处理：确保第一个元素的 margin-top 绝对为 0
        final_html = f'<div class="entry-container" style="padding: 0 10px 10px 10px; background-color: #ffffff; margin-top: 0 !important;">' \
                     f'<div style="margin-top: 0 !important;">{html_content}</div></div>'
        
        # 7. 作者、发布记录
        author = ""
        digest = diary.get("excerpt") or (source_content[:60] if source_content else "")
        
        insert_record_q = """
            INSERT INTO mp_publish_record 
            (user_id, diary_id, mp_account_id, title, author, digest, content_html, status) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        record_id = await db.execute_insert(insert_record_q, (
            user_id, data.entry_id, account['id'], diary['title'] or f"日记 {diary['entry_date']}",
            author, digest, final_html, 1 
        ))
        
        try:
            wx_media_id = await wechat_service.add_draft(
                account_id=account['id'],
                title=diary["title"] or f"股市日记 {diary['entry_date']}",
                content_html=final_html,
                author=author,
                digest=digest or ""
            )
            if wx_media_id:
                update_q = "UPDATE mp_publish_record SET status = 3, wx_media_id = %s WHERE id = %s"
                await db.execute(update_q, (wx_media_id, record_id))
                return {"publish_record_id": record_id, "wx_media_id": wx_media_id, "message": "success"}
            else:
                raise Exception("Failed to sync to WeChat draft box")
        except Exception as e:
            logger.error(f"Failed to publish to mp: {str(e)}")
            # 修正：修正字段名为 error_message
            update_q = "UPDATE mp_publish_record SET status = 4, error_message = %s WHERE id = %s"
            await db.execute(update_q, (str(e), record_id))
            return {"publish_record_id": record_id, "message": f"failed: {str(e)}"}

diary_service = DiaryService()
