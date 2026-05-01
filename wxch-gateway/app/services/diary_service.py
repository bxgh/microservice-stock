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
    """日记服务类 (精英排版+保底复制最终版)"""

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
        count_res = await db.execute(f"SELECT COUNT(*) as total FROM diary_entry WHERE {where_str}", tuple(params))
        total = count_res[0]['total']
        
        items = await db.execute(f"SELECT * FROM diary_entry WHERE {where_str} ORDER BY entry_date DESC, created_at DESC LIMIT %s OFFSET %s", tuple(params + [size, offset]))
        
        if items:
            ids = [item['id'] for item in items]
            stocks_res = await db.execute("SELECT ds.diary_id as entry_id, s.ts_code, s.name FROM diary_stock ds JOIN stock_info s ON ds.ts_code = s.ts_code WHERE ds.diary_id IN ({})".format(",".join(["%s"] * len(ids))), tuple(ids))
            tags_res = await db.execute("SELECT dt.diary_id as entry_id, td.id, td.name, td.category, td.color FROM diary_tag dt JOIN diary_tag_dict td ON dt.tag_id = td.id WHERE dt.diary_id IN ({})".format(",".join(["%s"] * len(ids))), tuple(ids))
            for item in items:
                item['stocks'] = [s for s in stocks_res if s['entry_id'] == item['id']]
                item['tags'] = [t for t in tags_res if t['entry_id'] == item['id']]
        return items, total

    async def get_by_id(self, user_id: int, entry_id: int) -> Optional[Dict[str, Any]]:
        """获取日记详情"""
        res = await db.execute("SELECT * FROM diary_entry WHERE id = %s AND user_id = %s AND deleted_at IS NULL", (entry_id, user_id))
        if not res: return None
        item = res[0]
        item['stocks'] = await db.execute("SELECT s.ts_code, s.name, s.market, s.industry_sw FROM diary_stock ds JOIN stock_info s ON ds.ts_code = s.ts_code WHERE ds.diary_id = %s", (entry_id,))
        item['tags'] = await db.execute("SELECT td.id, td.name, td.category, td.color FROM diary_tag dt JOIN diary_tag_dict td ON dt.tag_id = td.id WHERE dt.diary_id = %s", (entry_id,))
        return item

    async def create(self, user_id: int, data: DiaryEntryCreate) -> Dict[str, Any]:
        """创建日记"""
        word_count = len(data.content)
        excerpt = data.content[:200].replace("\n", " ").strip()
        query = """INSERT INTO diary_entry (user_id, entry_date, entry_type, mood, title, content, content_format, excerpt, word_count, visibility, is_pinned) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        params = (user_id, data.entry_date, data.entry_type, data.mood, data.title, data.content, data.content_format, excerpt, word_count, data.visibility, 1 if data.is_pinned else 0)
        entry_id = await db.execute_insert(query, params)
        if data.stocks:
            stocks_found = await db.execute("SELECT id, ts_code FROM stock_info WHERE ts_code IN ({})".format(",".join(["%s"] * len(data.stocks))), tuple(data.stocks))
            if stocks_found:
                await db.execute_many("INSERT INTO diary_stock (diary_id, stock_id, ts_code) VALUES (%s, %s, %s)", [(entry_id, s['id'], s['ts_code']) for s in stocks_found])
        if data.tags:
            tags_found = await db.execute("SELECT id FROM diary_tag_dict WHERE name IN ({})".format(",".join(["%s"] * len(data.tags))), tuple(data.tags))
            if tags_found:
                await db.execute_many("INSERT INTO diary_tag (diary_id, tag_id) VALUES (%s, %s)", [(entry_id, t['id']) for t in tags_found])
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
                updates.extend(["word_count = %s", "excerpt = %s"])
                params.extend([len(update_fields['content']), update_fields['content'][:200].replace("\n", " ").strip()])
            params.extend([entry_id, user_id])
            await db.execute(f"UPDATE diary_entry SET {', '.join(updates)} WHERE id = %s AND user_id = %s", tuple(params))
        if 'stocks' in update_fields:
            await db.execute("DELETE FROM diary_stock WHERE diary_id = %s", (entry_id,))
            if update_fields['stocks']:
                stocks_found = await db.execute("SELECT id, ts_code FROM stock_info WHERE ts_code IN ({})".format(",".join(["%s"] * len(update_fields['stocks']))), tuple(update_fields['stocks']))
                if stocks_found:
                    await db.execute_many("INSERT INTO diary_stock (diary_id, stock_id, ts_code) VALUES (%s, %s, %s)", [(entry_id, s['id'], s['ts_code']) for s in stocks_found])
        if 'tags' in update_fields:
            await db.execute("DELETE FROM diary_tag WHERE diary_id = %s", (entry_id,))
            if update_fields['tags']:
                tags_found = await db.execute("SELECT id FROM diary_tag_dict WHERE name IN ({})".format(",".join(["%s"] * len(update_fields['tags']))), tuple(update_fields['tags']))
                if tags_found:
                    await db.execute_many("INSERT INTO diary_tag (diary_id, tag_id) VALUES (%s, %s)", [(entry_id, t['id']) for t in tags_found])
        return await self.get_by_id(user_id, entry_id)

    async def delete(self, user_id: int, entry_id: int) -> bool:
        """逻辑删除"""
        affected = await db.execute("UPDATE diary_entry SET deleted_at = NOW() WHERE id = %s AND user_id = %s", (entry_id, user_id))
        return affected > 0

    async def get_stats(self, user_id: int) -> Dict[str, Any]:
        """获取统计"""
        monthly_res = await db.execute("SELECT COUNT(DISTINCT entry_date) as count FROM diary_entry WHERE user_id = %s AND deleted_at IS NULL AND entry_date >= DATE_FORMAT(NOW() ,'%%Y-%%m-01')", (user_id,))
        mood_res = await db.execute("SELECT mood FROM diary_entry WHERE user_id = %s AND deleted_at IS NULL ORDER BY entry_date DESC LIMIT 1", (user_id,))
        dist_res = await db.execute("SELECT mood, COUNT(*) as count FROM diary_entry WHERE user_id = %s AND deleted_at IS NULL GROUP BY mood", (user_id,))
        return {"monthly_days": monthly_res[0]['count'] if monthly_res else 0, "latest_mood": mood_res[0]['mood'] if mood_res else None, "mood_distribution": dist_res or []}

    async def publish_to_mp(self, user_id: int, data: DiaryPublishMPRequest) -> Dict[str, Any]:
        """最终版发布逻辑：极致内联样式 + 强制返回 HTML 供复制"""
        diary = await self.get_by_id(user_id, data.entry_id)
        if not diary: raise Exception("Diary not found")
        accounts = await db.execute("SELECT id, mp_appid FROM mp_account LIMIT 1")
        if not accounts: raise Exception("No mp account found")
        account = accounts[0]
        
        # 1. 极致排版引擎
        content = data.content if data.content else diary["content"]
        content = re.sub(r'^\s*[*+-]\s*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'\n\s*\n', '\n\n', content.strip())
        html = markdown.markdown(content, extensions=['extra', 'codehilite', 'toc'])
        html = re.sub(r'<(p|li)[^>]*>\s*(?:&nbsp;|\s)*</\1>', '', html)
        
        f_serif = "'Optima', 'Source Serif Pro', 'PingFang SC', 'STSongti-SC-Regular', serif"
        c_gold = "#d4a76a"
        html = html.replace("<p>", f'<p style="font-family: {f_serif}; font-size: 14px; line-height: 1.6; color: #353535; margin: 0 0 10px 0; text-align: justify;">')
        html = re.sub(r"<h3>(.*?)</h3>", lambda m: f'<h3 style="font-family: {f_serif}; font-size: 16px; font-weight: bold; color: #222; margin: 20px 0 6px 0; padding-left: 10px; border-left: 3px solid {c_gold}; line-height: 1.4;"><span style="color: {c_gold}; margin-right: 4px;">§</span>{m.group(1)}</h3>', html)
        html = html.replace("<ul>", f'<ul style="margin: 0 0 12px 0; padding-left: 20px; font-family: {f_serif}; font-size: 14px; color: #353535;">').replace("<li>", f'<li style="margin: 0 0 4px 0; padding: 0;">')
        html = html.replace("<blockquote>", f'<blockquote style="border-left: 3px solid #eee; padding: 6px 12px; color: #777; background-color: #f9f9f9; margin: 15px 0; font-family: {f_serif}; font-size: 13px;">')
        final_html = f'<div style="padding: 0 10px 10px 10px; background-color: #ffffff; margin-top: 0 !important;"><div style="margin-top: 0 !important;">{html}</div></div>'
        
        # 2. 保底返回结构
        result = {"publish_record_id": None, "wx_media_id": None, "content_html": final_html, "message": "init"}
        author, digest = "八仙过海", (diary.get("excerpt") or (content[:60] if content else ""))
        record_id = await db.execute_insert("INSERT INTO mp_publish_record (user_id, diary_id, mp_account_id, title, author, digest, content_html, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", (user_id, data.entry_id, account['id'], diary['title'] or f"日记 {diary['entry_date']}", author, digest, final_html, 1))
        result["publish_record_id"] = record_id
        
        # 3. 尝试自动同步
        try:
            wx_media_id = await wechat_service.add_draft(account_id=account['id'], title=diary["title"] or f"股市日记 {diary['entry_date']}", content_html=final_html, author=author, digest=digest or "")
            if wx_media_id:
                await db.execute("UPDATE mp_publish_record SET status = 3, wx_media_id = %s WHERE id = %s", (wx_media_id, record_id))
                result.update({"wx_media_id": wx_media_id, "message": "success"})
            else: raise Exception("Sync failed (Account restriction)")
        except Exception as e:
            await db.execute("UPDATE mp_publish_record SET status = 4, error_message = %s WHERE id = %s", (str(e), record_id))
            result["message"] = f"API failed: {str(e)}. Use 'Copy HTML' instead."
        return result

diary_service = DiaryService()
