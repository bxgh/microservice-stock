import logging
import time
import os
import markdown
from typing import Optional, List, Dict, Any
from app.utils.database import db
from app.models.diary import DiaryEntryCreate, DiaryEntryUpdate, DiaryPublishMPRequest
from premailer import transform
from app.services.wechat_service import wechat_service

logger = logging.getLogger("gateway.service.diary")

class DiaryService:
    """日记服务类，处理日记的增删改查及同步逻辑"""

    async def get_diaries(self, user_id: int, page: int = 1, size: int = 20, 
                          start_date: Optional[str] = None, end_date: Optional[str] = None,
                          entry_type: Optional[int] = None, mood: Optional[int] = None,
                          search: Optional[str] = None) -> Dict[str, Any]:
        """获取日记列表 (带分页和筛选)"""
        offset = (page - 1) * size
        params = [user_id]
        where_clauses = ["user_id = %s"]
        
        if start_date:
            where_clauses.append("entry_date >= %s")
            params.append(start_date)
        if end_date:
            where_clauses.append("entry_date <= %s")
            params.append(end_date)
        if entry_type:
            where_clauses.append("entry_type = %s")
            params.append(entry_type)
        if mood:
            where_clauses.append("mood = %s")
            params.append(mood)
        if search:
            where_clauses.append("(title LIKE %s OR content LIKE %s)")
            params.extend([f"%{search}%", f"%{search}%"])
            
        where_str = " AND ".join(where_clauses)
        
        # 1. 查总数
        count_query = f"SELECT COUNT(*) as total FROM diary_entry WHERE {where_str}"
        count_res = await db.execute(count_query, tuple(params))
        total = count_res[0]['total']
        
        # 2. 查列表 (关联查标签和股票可以在应用层聚合或使用 GROUP_CONCAT)
        list_query = f"""
            SELECT * FROM diary_entry 
            WHERE {where_str} 
            ORDER BY entry_date DESC, created_at DESC 
            LIMIT %s OFFSET %s
        """
        list_params = params + [size, offset]
        items = await db.execute(list_query, tuple(list_params))
        
        # 3. 补充标签和股票信息 (这里为了高性能，可以再写两个批量查询)
        if items:
            ids = [item['id'] for item in items]
            
            # 查股票
            stocks_query = """
                SELECT des.entry_id, s.ts_code, s.name 
                FROM diary_entry_stock des
                JOIN stock_basic s ON des.ts_code = s.ts_code
                WHERE des.entry_id IN ({})
            """.format(",".join(["%s"] * len(ids)))
            stocks_res = await db.execute(stocks_query, tuple(ids))
            
            # 查标签
            tags_query = """
                SELECT det.entry_id, t.id, t.name, t.category, t.color
                FROM diary_entry_tag det
                JOIN sys_tag t ON det.tag_id = t.id
                WHERE det.entry_id IN ({})
            """.format(",".join(["%s"] * len(ids)))
            tags_res = await db.execute(tags_query, tuple(ids))
            
            # 聚合数据
            for item in items:
                item['stocks'] = [s for s in stocks_res if s['entry_id'] == item['id']]
                item['tags'] = [t for t in tags_res if t['entry_id'] == item['id']]
                
        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size
        }

    async def get_diary_detail(self, user_id: int, entry_id: int) -> Optional[Dict[str, Any]]:
        """获取日记详情"""
        query = "SELECT * FROM diary_entry WHERE id = %s AND user_id = %s"
        res = await db.execute(query, (entry_id, user_id))
        if not res:
            return None
        
        item = res[0]
        
        # 补充股票
        stocks_query = """
            SELECT s.ts_code, s.name, s.market, s.industry_sw
            FROM diary_entry_stock des
            JOIN stock_basic s ON des.ts_code = s.ts_code
            WHERE des.entry_id = %s
        """
        item['stocks'] = await db.execute(stocks_query, (entry_id,))
        
        # 补充标签
        tags_query = """
            SELECT t.id, t.name, t.category, t.color
            FROM diary_entry_tag det
            JOIN sys_tag t ON det.tag_id = t.id
            WHERE det.entry_id = %s
        """
        item['tags'] = await db.execute(tags_query, (entry_id,))
        
        return item

    async def create_diary(self, user_id: int, data: DiaryEntryCreate) -> int:
        """创建日记"""
        # 1. 插入主表
        # 注意：这里假设 DDL 中有 word_count 和 excerpt 字段，或者我们在代码中计算
        word_count = len(data.content)
        excerpt = data.content[:200].replace("\n", " ") # 简单生成摘要
        
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
        entry_id = await db.execute(query, params)
        
        # 2. 插入股票关联
        if data.stocks:
            stock_query = "INSERT INTO diary_entry_stock (entry_id, ts_code) VALUES (%s, %s)"
            stock_params = [(entry_id, code) for code in data.stocks]
            await db.execute_many(stock_query, stock_params)
            
        # 3. 插入标签关联 (需要先查出 tag_id)
        if data.tags:
            # 简单处理：假设标签已存在，通过名称查找
            tag_query = "SELECT id FROM sys_tag WHERE name IN ({})".format(",".join(["%s"] * len(data.tags)))
            tags_found = await db.execute(tag_query, tuple(data.tags))
            if tags_found:
                rel_query = "INSERT INTO diary_entry_tag (entry_id, tag_id) VALUES (%s, %s)"
                rel_params = [(entry_id, t['id']) for t in tags_found]
                await db.execute_many(rel_query, rel_params)
                
        return entry_id

    async def update_diary(self, user_id: int, entry_id: int, data: DiaryEntryUpdate) -> bool:
        """更新日记"""
        # 1. 检查权限
        check_q = "SELECT id FROM diary_entry WHERE id = %s AND user_id = %s"
        if not await db.execute(check_q, (entry_id, user_id)):
            return False
            
        # 2. 动态构建更新语句
        updates = []
        params = []
        
        update_fields = data.model_dump(exclude_unset=True)
        for field, value in update_fields.items():
            if field in ['stocks', 'tags']: continue
            updates.append(f"{field} = %s")
            params.append(value)
            
        if updates:
            # 如果更新了内容，重新计算字数和摘要
            if 'content' in update_fields:
                updates.append("word_count = %s")
                params.append(len(update_fields['content']))
                updates.append("excerpt = %s")
                params.append(update_fields['content'][:200].replace("\n", " "))
                
            params.append(entry_id)
            params.append(user_id)
            query = f"UPDATE diary_entry SET {', '.join(updates)} WHERE id = %s AND user_id = %s"
            await db.execute(query, tuple(params))
            
        # 3. 更新股票和标签 (简单做法：先删再增)
        if 'stocks' in update_fields:
            await db.execute("DELETE FROM diary_entry_stock WHERE entry_id = %s", (entry_id,))
            if update_fields['stocks']:
                stock_query = "INSERT INTO diary_entry_stock (entry_id, ts_code) VALUES (%s, %s)"
                stock_params = [(entry_id, code) for code in update_fields['stocks']]
                await db.execute_many(stock_query, stock_params)
                
        if 'tags' in update_fields:
            await db.execute("DELETE FROM diary_entry_tag WHERE entry_id = %s", (entry_id,))
            if update_fields['tags']:
                tag_query = "SELECT id FROM sys_tag WHERE name IN ({})".format(",".join(["%s"] * len(update_fields['tags'])))
                tags_found = await db.execute(tag_query, tuple(update_fields['tags']))
                if tags_found:
                    rel_query = "INSERT INTO diary_entry_tag (entry_id, tag_id) VALUES (%s, %s)"
                    rel_params = [(entry_id, t['id']) for t in tags_found]
                    await db.execute_many(rel_query, rel_params)
                    
        return True

    async def delete_diary(self, user_id: int, entry_id: int) -> bool:
        """删除日记"""
        # 关联表由外键级联删除或手动处理
        query = "DELETE FROM diary_entry WHERE id = %s AND user_id = %s"
        affected = await db.execute(query, (entry_id, user_id))
        return affected > 0

    async def get_diary_stats(self, user_id: int) -> Dict[str, Any]:
        """获取日记统计数据"""
        # 1. 本月记录天数
        monthly_q = """
            SELECT COUNT(DISTINCT entry_date) as count 
            FROM diary_entry 
            WHERE user_id = %s AND entry_date >= DATE_FORMAT(NOW() ,'%Y-%m-01')
        """
        monthly_res = await db.execute(monthly_q, (user_id,))
        
        # 2. 最近心情
        mood_q = "SELECT mood FROM diary_entry WHERE user_id = %s ORDER BY entry_date DESC LIMIT 1"
        mood_res = await db.execute(mood_q, (user_id,))
        
        # 3. 心情分布
        dist_q = "SELECT mood, COUNT(*) as count FROM diary_entry WHERE user_id = %s GROUP BY mood"
        dist_res = await db.execute(dist_q, (user_id,))
        
        return {
            "monthly_days": monthly_res[0]['count'] if monthly_res else 0,
            "latest_mood": mood_res[0]['mood'] if mood_res else None,
            "mood_distribution": dist_res or []
        }

    async def publish_to_mp(self, user_id: int, data: DiaryPublishMPRequest) -> Dict[str, Any]:
        """同步日记到微信公众号草稿箱"""
        # 1. 获取日记详情
        diary = await self.get_diary_detail(user_id, data.entry_id)
        if not diary:
            raise HTTPException(status_code=404, detail="Diary not found")
            
        # 2. 获取该用户的微信配置 (假设 sys_user 或单独表有关联)
        # 这里简单从 mp_account 表取第一个有效的
        account_query = "SELECT id, mp_appid FROM mp_account LIMIT 1"
        accounts = await db.execute(account_query)
        if not accounts:
            raise HTTPException(status_code=400, detail="No linked WeChat Official Account found")
        account = accounts[0]
        
        # 3. Markdown 转 HTML 并注入精美样式
        # 优先使用前端传来的“净化版”内容，如果没有则使用原内容
        source_content = data.content if data.content else diary["content"]
        
        # 定义公众号专用样式 (紧致精美版)
        WECHAT_STYLE = """
        <style>
            .entry-container {
                font-family: 'Optima', 'Source Serif Pro', 'PingFang SC', 'STSongti-SC-Regular', serif;
                font-size: 15px;
                line-height: 1.75;
                color: #353535;
                padding: 0 5px;
                text-align: justify;
            }
            h3 {
                font-size: 17px;
                font-weight: bold;
                color: #222;
                margin-top: 24px;
                margin-bottom: 8px;
                border-left: 3px solid #d4a76a;
                padding-left: 10px;
                line-height: 1.4;
            }
            p {
                margin: 0 0 12px 0;
                letter-spacing: 0.3px;
            }
            blockquote {
                border-left: 3px solid #e0e0e0;
                padding: 5px 12px;
                color: #777;
                background-color: #f9f9f9;
                margin: 15px 0;
            }
            ul, ol {
                margin-bottom: 12px;
                padding-left: 18px;
            }
            li {
                margin-bottom: 6px;
            }
            hr {
                border: 0;
                border-top: 1px solid #eee;
                margin: 24px 0;
            }
        </style>
        """
        
        raw_html = markdown.markdown(source_content, extensions=['extra', 'codehilite', 'toc'])
        # 包装容器并注入样式
        styled_html_raw = f"<html><body>{WECHAT_STYLE}<div class='entry-container'>{raw_html}</div></body></html>"
        html_content = transform(styled_html_raw)
        
        # 4. 创建发布记录 (mp_publish_record)
        author_query = "SELECT nickname FROM sys_user WHERE id = %s"
        user_res = await db.execute(author_query, (user_id,))
        author = user_res[0]["nickname"] if user_res else "Trader"
        
        digest = diary.get("excerpt") or (source_content[:60] if source_content else "")
        
        insert_record_q = """
            INSERT INTO mp_publish_record 
            (diary_id, mp_account_id, title, author, digest, content_html, status) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        record_id = await db.execute(insert_record_q, (
            data.entry_id, account['id'], diary['title'] or f"日记 {diary['entry_date']}",
            author, digest, html_content, 1 # 1=处理中
        ))
        
        # 5. 调用微信接口同步
        # 这里需要实现真实的微信草稿箱接口调用
        try:
            wx_media_id = await wechat_service.add_draft(
                account_id=account['id'],
                title=diary["title"] or f"股市日记 {diary['entry_date']}",
                content_html=html_content,
                author=author or "",
                digest=digest or ""
            )
            
            if wx_media_id:
                # 更新状态为成功
                update_q = "UPDATE mp_publish_record SET status = 3, wx_media_id = %s WHERE id = %s"
                await db.execute(update_q, (wx_media_id, record_id))
                return {"publish_record_id": record_id, "wx_media_id": wx_media_id, "message": "success"}
            else:
                raise Exception("Failed to sync to WeChat draft box")
                
        except Exception as e:
            logger.error(f"Failed to publish to mp: {str(e)}")
            # 更新状态为失败
            update_q = "UPDATE mp_publish_record SET status = 4, error_msg = %s WHERE id = %s"
            await db.execute(update_q, (str(e), record_id))
            return {"publish_record_id": record_id, "message": f"failed: {str(e)}"}

diary_service = DiaryService()
