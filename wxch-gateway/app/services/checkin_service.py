import logging
import random
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from fastapi import HTTPException
import json

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

from app.utils.database import db
from app.models.checkin import (
    MaximQuoteCreate,
    MaximQuoteResponseData,
    MaximCheckinSubmit,
    MaximActionRequest
)

logger = logging.getLogger("gateway.service.checkin")

def get_now_shanghai() -> datetime:
    """获取当前上海时区时间 (带时区信息或回落到系统本地时区)"""
    if ZoneInfo:
        try:
            return datetime.now(ZoneInfo("Asia/Shanghai"))
        except Exception:
            pass
    return datetime.now()

class CheckinService:
    async def create_quote(self, user_id: int, data: MaximQuoteCreate) -> Dict[str, Any]:
        """手工录入一条新格言到词库中"""
        logger.info(f"User {user_id} is creating a custom quote: {data.content[:20]}...")
        
        query = """
            INSERT INTO diary_quote_lib 
            (owner_user_id, content, source_author, source_book, category, base_weight)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (
            user_id,
            data.content,
            data.source_author,
            data.source_book,
            data.category,
            data.base_weight
        )
        
        try:
            quote_id = await db.execute_insert(query, params)
            logger.info(f"Custom quote created successfully. ID: {quote_id}")
            
            select_query = """
                SELECT id, content, source_author, source_book, category, base_weight, created_at
                FROM diary_quote_lib
                WHERE id = %s AND is_deleted = 0
            """
            res = await db.execute(select_query, (quote_id,))
            if not res:
                raise HTTPException(status_code=500, detail="Quote created but failed to retrieve")
            
            quote = res[0]
            return {
                "quote_id": quote["id"],
                "content": quote["content"],
                "created_at": quote["created_at"]
            }
        except Exception as e:
            logger.error(f"Error creating custom quote for user {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to create custom quote")

    def get_business_date(self, now: datetime) -> date:
        """根据凌晨 4:00 分界线判定当前业务归属日期"""
        if now.hour < 4:
            return (now - timedelta(days=1)).date()
        return now.date()

    async def select_daily_quote(self, user_id: int, business_date: date) -> Optional[Dict[str, Any]]:
        """按照排重、曝光周期、收藏加权、跳过扣权及大盘情绪对齐算法，挑选一条今日格言"""
        # 1. 查询格言库所有未删除记录
        quotes_query = """
            SELECT id, content, source_author, source_book, category, base_weight
            FROM diary_quote_lib
            WHERE is_deleted = 0
        """
        all_quotes = await db.execute(quotes_query)
        if not all_quotes:
            logger.info("No quotes found in diary_quote_lib")
            return None

        # 2. 查询用户状态偏好
        states_query = """
            SELECT quote_id, is_favorited, is_disliked, consecutive_skip_count, last_exposed_at
            FROM diary_quote_user_state
            WHERE user_id = %s
        """
        user_states = await db.execute(states_query, (user_id,))
        states_map = {state["quote_id"]: state for state in user_states}

        # 3. 实时提取大盘今日或最近交易日指数涨跌幅 (上证综指 000001.SH)
        pct_chg = 0.0
        try:
            index_query = """
                SELECT pct_chg FROM ods_index_daily 
                WHERE ts_code = '000001.SH' 
                ORDER BY trade_date DESC LIMIT 1
            """
            index_res = await db.execute(index_query)
            if index_res:
                pct_chg = float(index_res[0]["pct_chg"])
                logger.info(f"Retrieved latest market index change for 000001.SH: {pct_chg}")
        except Exception as e:
            logger.warning(f"Failed to query market index sentiment: {e}")

        # 4. 过滤并计算候选池权重
        candidates = []
        weights = []
        thirty_days_ago = business_date - timedelta(days=30)

        for q in all_quotes:
            qid = q["id"]
            state = states_map.get(qid)

            # (A) 排除永久屏蔽项
            if state and state["is_disliked"] == 1:
                continue

            # (B) 排除 30 天内已曝光过的项
            if state and state["last_exposed_at"]:
                last_exp = state["last_exposed_at"]
                if isinstance(last_exp, datetime):
                    last_exp = last_exp.date()
                if last_exp >= thirty_days_ago:
                    continue

            # (C) 评分权重计算
            base_w = q["base_weight"] if q["base_weight"] is not None else 50
            w = base_w

            # 连续跳过惩罚：每次跳过扣 10 分
            skip_count = state["consecutive_skip_count"] if state else 0
            w = max(1, w - skip_count * 10)

            # 收藏加权
            is_fav = state["is_favorited"] if state else 0
            if is_fav == 1:
                w += 20

            # 大盘情绪加权
            cat = q["category"]
            if pct_chg >= 0.005:  # 大盘大涨
                if cat in (1, 3):
                    w += 15
            elif pct_chg <= -0.005:  # 大盘大跌
                if cat in (2, 3):
                    w += 15

            candidates.append(q)
            weights.append(max(1, w))

        if not candidates:
            logger.info("All quotes in library were filtered out for the user")
            return None

        # 5. 加权随机概率抽取
        selected = random.choices(candidates, weights=weights, k=1)[0]
        logger.info(f"Weighted random algorithm picked quote ID {selected['id']} for user {user_id}")
        return selected

    async def _get_quote_detail_for_user(self, user_id: int, quote_id: int) -> Optional[Dict[str, Any]]:
        """获取格言详情并补充针对当前用户的行为偏好(收藏)及历史心得见解"""
        quote_query = """
            SELECT id, content, source_author, source_book, category
            FROM diary_quote_lib
            WHERE id = %s AND is_deleted = 0
        """
        res = await db.execute(quote_query, (quote_id,))
        if not res:
            return None
        q = res[0]

        # 查询是否收藏
        fav_query = """
            SELECT is_favorited FROM diary_quote_user_state
            WHERE user_id = %s AND quote_id = %s
            LIMIT 1
        """
        fav_res = await db.execute(fav_query, (user_id, quote_id))
        is_favorited = fav_res[0]["is_favorited"] if fav_res else 0

        # 查询该格言下该用户的最新一次心得打卡记录 (通过锁表关联)
        insight_query = """
            SELECT e.content, e.entry_date 
            FROM diary_checkin_lock l
            JOIN diary_entry e ON l.completed_diary_id = e.id
            WHERE l.user_id = %s 
              AND l.locked_target_id = %s 
              AND l.checkin_type = 2 
              AND l.status = 1 
              AND e.deleted_at IS NULL
            ORDER BY l.business_date DESC 
            LIMIT 1
        """
        insight_res = await db.execute(insight_query, (user_id, quote_id))
        history_insight = None
        if insight_res:
            history_insight = {
                "last_insight_content": insight_res[0]["content"],
                "last_insight_date": insight_res[0]["entry_date"]
            }

        return {
            "id": q["id"],
            "content": q["content"],
            "source_author": q["source_author"],
            "source_book": q["source_book"],
            "category": q["category"],
            "is_favorited": is_favorited,
            "history_insight": history_insight
        }

    async def get_or_lock_today_quote(self, user_id: int) -> Dict[str, Any]:
        """获取或幂等锁定今日的待打卡格言"""
        now = get_now_shanghai()
        bus_date = self.get_business_date(now)

        # 1. 检查今日是否已锁定
        lock_query = """
            SELECT locked_target_id, status, completed_diary_id 
            FROM diary_checkin_lock
            WHERE user_id = %s AND business_date = %s AND checkin_type = 2
            LIMIT 1
        """
        lock_res = await db.execute(lock_query, (user_id, bus_date))

        if lock_res:
            lock = lock_res[0]
            status = lock["status"]
            locked_qid = lock["locked_target_id"]

            if locked_qid is None:
                # 之前已被幂等锁定为空库兜底状态
                logger.info(f"User {user_id} hit locked EMPTY_LIB state for date {bus_date}")
                return {
                    "business_date": bus_date,
                    "checkin_type": 2,
                    "status": status,
                    "quote": None,
                    "msg": "EMPTY_LIB"
                }

            quote_detail = await self._get_quote_detail_for_user(user_id, locked_qid)
            if not quote_detail:
                # 兜底：若锁定的格言因物理删除损坏，静默返回 EMPTY_LIB 防止白屏
                return {
                    "business_date": bus_date,
                    "checkin_type": 2,
                    "status": status,
                    "quote": None,
                    "msg": "EMPTY_LIB"
                }

            logger.info(f"User {user_id} hit locked quote ID {locked_qid} for date {bus_date}")
            return {
                "business_date": bus_date,
                "checkin_type": 2,
                "status": status,
                "quote": quote_detail
            }

        # 2. 今日尚未锁定，开始轮询算法获取今日格言
        selected_quote = await self.select_daily_quote(user_id, bus_date)

        if not selected_quote:
            # 候选池为空或冷启动，写入空锁占位
            insert_lock_query = """
                INSERT INTO diary_checkin_lock
                (user_id, business_date, checkin_type, locked_target_id, status)
                VALUES (%s, %s, %s, %s, %s)
            """
            await db.execute_insert(insert_lock_query, (user_id, bus_date, 2, None, 0))
            logger.info(f"User {user_id} locked with EMPTY_LIB for date {bus_date} (cold start)")
            return {
                "business_date": bus_date,
                "checkin_type": 2,
                "status": 0,
                "quote": None,
                "msg": "EMPTY_LIB"
            }

        # 选出格言，原子写入锁定记录
        quote_id = selected_quote["id"]
        insert_lock_query = """
            INSERT INTO diary_checkin_lock
            (user_id, business_date, checkin_type, locked_target_id, status)
            VALUES (%s, %s, %s, %s, %s)
        """
        await db.execute_insert(insert_lock_query, (user_id, bus_date, 2, quote_id, 0))

        # 3. 记录物理曝光并更新用户状态表行为频数
        now_dt = datetime.now()
        state_check_query = """
            SELECT id FROM diary_quote_user_state
            WHERE user_id = %s AND quote_id = %s
            LIMIT 1
        """
        state_res = await db.execute(state_check_query, (user_id, quote_id))
        if state_res:
            state_id = state_res[0]["id"]
            update_state_query = """
                UPDATE diary_quote_user_state
                SET expose_count = expose_count + 1, last_exposed_at = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            await db.execute(update_state_query, (now_dt, state_id))
        else:
            insert_state_query = """
                INSERT INTO diary_quote_user_state
                (user_id, quote_id, is_favorited, is_disliked, consecutive_skip_count, expose_count, last_exposed_at)
                VALUES (%s, %s, 0, 0, 0, 1, %s)
            """
            await db.execute_insert(insert_state_query, (user_id, quote_id, now_dt))

        quote_detail = await self._get_quote_detail_for_user(user_id, quote_id)
        logger.info(f"User {user_id} newly locked quote ID {quote_id} for date {bus_date}")
        return {
            "business_date": bus_date,
            "checkin_type": 2,
            "status": 0,
            "quote": quote_detail
        }

    # --- 后续 Story 完整核心服务函数实现 ---

    async def submit_checkin(self, user_id: int, data: MaximCheckinSubmit) -> Dict[str, Any]:
        """
        提交打卡感悟，生成日记实体，并在同一事务中原子累加计数。
        - 验证今日已分配锁定的格言，并检查一致性与重复提交。
        - 组装标准的 Markdown 格式正文与精炼标题。
        - 原子写入随笔日记并更新每日打卡锁为已完成。
        - 更新并自增个性化状态表中的累计解读计数。
        """
        bus_date = self.get_business_date(get_now_shanghai())
        
        # 1. 验证今日锁定的任务格言
        lock_res = await db.execute(
            "SELECT id, locked_target_id, status FROM diary_checkin_lock WHERE user_id = %s AND business_date = %s AND checkin_type = 2",
            (user_id, bus_date)
        )
        if not lock_res:
            raise HTTPException(status_code=400, detail="今日尚未分配或锁定任何格言打卡任务！")
        
        lock_record = lock_res[0]
        locked_qid = lock_record["locked_target_id"]
        lock_status = lock_record["status"]
        
        if locked_qid is None:
            raise HTTPException(status_code=400, detail="今日没有有效的待打卡格言任务（格言词库为空）！")
            
        if locked_qid != data.quote_id:
            raise HTTPException(status_code=400, detail="提交的格言 ID 与今日分配锁定的格言任务不匹配！")
            
        if lock_status == 1:
            raise HTTPException(status_code=400, detail="今日已经提交过该格言的打卡感悟，请勿重复提交！")
            
        # 2. 查询格言详情以拼接 Markdown 正文与精炼标题
        quote_res = await db.execute(
            "SELECT content, source_author FROM diary_quote_lib WHERE id = %s",
            (data.quote_id,)
        )
        if not quote_res:
            raise HTTPException(status_code=404, detail="未找到指定的格言数据！")
            
        quote_content = quote_res[0]["content"]
        quote_author = quote_res[0]["source_author"] or "未知"
        
        # 3. 构造日记标题与 Markdown 内容
        title = f"格言解读 · {quote_author} · {quote_content[:10]}"
        content = f"#### 今日投资格言\n> {quote_content}\n\n#### 我的打卡反思\n{data.insight}"
        
        # 4. 获取今日大盘最新状态快照
        market_res = await db.execute(
            "SELECT ts_code, pct_chg FROM ods_index_daily WHERE ts_code = '000001.SH' ORDER BY trade_date DESC LIMIT 1"
        )
        market_summary = None
        if market_res:
            market_summary = {
                "ts_code": market_res[0]["ts_code"],
                "pct_chg": float(market_res[0]["pct_chg"])
            }
            
        meta_json = json.dumps({
            "raw_insight": data.insight,
            "market_summary": market_summary
        }, ensure_ascii=False)
        
        word_count = len(data.insight)
        
        # 5. 原子写入随笔日记并更新状态锁定记录
        diary_id = await db.execute_insert(
            """
            INSERT INTO diary_entry (user_id, title, content, entry_date, entry_type, mood, word_count, meta)
            VALUES (%s, %s, %s, %s, 5, %s, %s, %s)
            """,
            (user_id, title, content, bus_date, data.mood, word_count, meta_json)
        )
        
        await db.execute(
            "UPDATE diary_checkin_lock SET status = 1, completed_diary_id = %s WHERE id = %s",
            (diary_id, lock_record["id"])
        )
        
        # 6. 更新用户格言行为状态表中的累计解读计数
        is_deep = 1 if word_count >= 50 else 0
        
        state_res = await db.execute(
            "SELECT id, insight_count, deep_insight_count FROM diary_quote_user_state WHERE user_id = %s AND quote_id = %s",
            (user_id, data.quote_id)
        )
        if state_res:
            state_id = state_res[0]["id"]
            new_insight_count = state_res[0]["insight_count"] + 1
            new_deep_count = state_res[0]["deep_insight_count"] + is_deep
            await db.execute(
                "UPDATE diary_quote_user_state SET insight_count = %s, deep_insight_count = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (new_insight_count, new_deep_count, state_id)
            )
        else:
            new_insight_count = 1
            await db.execute_insert(
                """
                INSERT INTO diary_quote_user_state (user_id, quote_id, is_favorited, is_disliked, consecutive_skip_count, expose_count, insight_count, deep_insight_count)
                VALUES (%s, %s, 0, 0, 0, 0, 1, %s)
                """,
                (user_id, data.quote_id, is_deep)
            )
            
        logger.info(f"User {user_id} successfully submitted checkin diary ID {diary_id} for quote ID {data.quote_id}")
        return {
            "diary_id": diary_id,
            "title": title,
            "entry_date": bus_date,
            "accumulated_insight_count": new_insight_count
        }

    async def update_action(self, user_id: int, data: MaximActionRequest) -> None:
        """
        更新动作操作（收藏、屏蔽、跳过）。
        - 收藏：更新 is_favorited 并使曝光池分配计算享受 +20 高加成。
        - 屏蔽：更新 is_disliked，使其在曝光池挑选时永久隐消。
        - 跳过：递增该格言的连续跳过次数 skip_count 并将今日锁记录设为已跳过 (status = 2)。
        """
        state_res = await db.execute(
            "SELECT id, consecutive_skip_count FROM diary_quote_user_state WHERE user_id = %s AND quote_id = %s",
            (user_id, data.quote_id)
        )
        if state_res:
            state_id = state_res[0]["id"]
            consecutive_skip = state_res[0]["consecutive_skip_count"]
        else:
            state_id = await db.execute_insert(
                "INSERT INTO diary_quote_user_state (user_id, quote_id, is_favorited, is_disliked, consecutive_skip_count, expose_count) VALUES (%s, %s, 0, 0, 0, 0)",
                (user_id, data.quote_id)
            )
            consecutive_skip = 0
            
        if data.action_type == "favorite":
            await db.execute(
                "UPDATE diary_quote_user_state SET is_favorited = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (data.value, state_id)
            )
            logger.info(f"User {user_id} updated quote {data.quote_id} favorite state to {data.value}")
            
        elif data.action_type == "dislike":
            await db.execute(
                "UPDATE diary_quote_user_state SET is_disliked = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (data.value, state_id)
            )
            logger.info(f"User {user_id} updated quote {data.quote_id} dislike state to {data.value}")
            
        elif data.action_type == "skip":
            if data.value == 1:
                # 跳过今日锁定的待打卡任务
                new_skip = consecutive_skip + 1
                await db.execute(
                    "UPDATE diary_quote_user_state SET consecutive_skip_count = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (new_skip, state_id)
                )
                bus_date = self.get_business_date(get_now_shanghai())
                await db.execute(
                    "UPDATE diary_checkin_lock SET status = 2 WHERE user_id = %s AND business_date = %s AND checkin_type = 2",
                    (user_id, bus_date)
                )
                logger.info(f"User {user_id} skipped today locked checkin for quote {data.quote_id}")

    async def get_timeline(self, user_id: int, quote_id: int) -> Dict[str, Any]:
        """
        获取单条格言的反思历史时间轴。
        - 自动提取格言正文。
        - 倒序检索关联的 checkin_type = 2 打卡日记列表并自动解析 meta 中的大盘信息及感悟原文。
        """
        quote_res = await db.execute("SELECT content FROM diary_quote_lib WHERE id = %s AND is_deleted = 0", (quote_id,))
        if not quote_res:
            raise HTTPException(status_code=404, detail="未找到指定的格言记录！")
            
        quote_content = quote_res[0]["content"]
        
        diaries = await db.execute(
            """
            SELECT e.id, e.entry_date, e.content, e.mood, e.meta 
            FROM diary_entry e
            JOIN diary_checkin_lock l ON l.completed_diary_id = e.id
            WHERE e.user_id = %s AND l.locked_target_id = %s AND l.checkin_type = 2 AND e.deleted_at IS NULL
            ORDER BY e.entry_date DESC
            """,
            (user_id, quote_id)
        )
        
        timeline = []
        for d in diaries:
            insight = d["content"]
            market_summary = None
            if d["meta"]:
                try:
                    meta_data = json.loads(d["meta"])
                    if "raw_insight" in meta_data:
                        insight = meta_data["raw_insight"]
                    if "market_summary" in meta_data:
                        market_summary = meta_data["market_summary"]
                except Exception:
                    pass
                    
            timeline.append({
                "diary_id": d["id"],
                "date": d["entry_date"],
                "insight": insight,
                "mood": d["mood"],
                "market_summary": market_summary
            })
            
        return {
            "quote_id": quote_id,
            "content": quote_content,
            "total_insights": len(timeline),
            "timeline": timeline
        }

checkin_service = CheckinService()
