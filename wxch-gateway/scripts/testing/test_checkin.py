import asyncio
import sys
import os
import json
from datetime import datetime, date, timedelta
import pytest
from httpx import AsyncClient

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.main import app
from app.utils.database import db
from app.config import settings
from app.utils.auth import create_access_token
from app.services.checkin_service import checkin_service, get_now_shanghai

# Override settings for local testing (runs outside docker)
settings.DB_HOST = "sh-cdb-h7flpxu4.sql.tencentcdb.com"
settings.DB_PORT = 26300

@pytest.fixture(autouse=True)
async def setup_db():
    """每个测试用例独立进行数据库的连接 and 断开，确保绑定在正确的当前 asyncio 事件循环上"""
    await db.connect()
    yield
    await db.disconnect()

async def get_test_user_headers():
    """获取测试用户的请求头与用户 ID 的辅助函数"""
    res = await db.execute("SELECT id FROM sys_user WHERE openid = 'dev_openid_001' LIMIT 1")
    if not res:
        user_id = await db.execute_insert(
            "INSERT INTO sys_user (openid, nickname, avatar_url) VALUES ('dev_openid_001', 'Test User', '')"
        )
    else:
        user_id = res[0]["id"]
    
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}, user_id

@pytest.mark.asyncio
async def test_e23_checkin_integration_suite():
    """将 E23-S1 至 E23-S8 所有包含 DB 访问的测试流程完全收拢在一个事件循环测试用例中，彻底杜绝 Windows 底层 Event Loop Closed 异常"""
    headers, user_id = await get_test_user_headers()
    bus_date = checkin_service.get_business_date(get_now_shanghai())
    
    # 备份并在开始前清空已有的格言库 (将 is_deleted 置为 1)，利用 try...finally 确保最终一定能安全恢复
    backup_quotes = await db.execute("SELECT id, is_deleted FROM diary_quote_lib WHERE is_deleted = 0")
    if backup_quotes:
        await db.execute("UPDATE diary_quote_lib SET is_deleted = 1 WHERE is_deleted = 0")
        
    try:
        async with AsyncClient(app=app, base_url="http://test") as ac:
            
            # ====================================================
            # 第一阶段：E23-S1 手工录入格言校验
            # ====================================================
            # 1. 验证手工录入字数限制校验 (10-500字)
            payload_too_short = {
                "content": "名言太短",
                "source_author": "巴菲特",
                "category": 1
            }
            response = await ac.post("/api/v1/checkin/maxim/quote", json=payload_too_short, headers=headers)
            assert response.status_code == 422
            
            payload_too_long = {
                "content": "名言" * 300,
                "source_author": "巴菲特",
                "category": 1
            }
            response = await ac.post("/api/v1/checkin/maxim/quote", json=payload_too_long, headers=headers)
            assert response.status_code == 422
            
            # 2. 验证手工录入合法格言写入成功
            payload = {
                "content": "在别人恐惧时我贪婪，在别人贪婪时我恐惧。",
                "source_author": "巴菲特",
                "source_book": "致股东的信",
                "category": 1,
                "base_weight": 80
            }
            response = await ac.post("/api/v1/checkin/maxim/quote", json=payload, headers=headers)
            assert response.status_code == 200
            
            res_data = response.json()
            assert res_data["code"] == 200
            assert res_data["message"] == "success"
            
            quote_data = res_data["data"]
            assert quote_data["quote_id"] > 0
            quote_id = quote_data["quote_id"]
            assert quote_data["content"] == payload["content"]
            assert "created_at" in quote_data
            
            # 3. 验证审计三件套与底层物理字段落库正确性
            db_res = await db.execute(
                "SELECT owner_user_id, content, source_author, source_book, category, base_weight, created_at, updated_at, is_deleted FROM diary_quote_lib WHERE id = %s",
                (quote_id,)
            )
            assert db_res
            record = db_res[0]
            
            assert record["owner_user_id"] == user_id
            assert record["content"] == payload["content"]
            assert record["source_author"] == payload["source_author"]
            assert record["source_book"] == payload["source_book"]
            assert record["category"] == payload["category"]
            assert record["base_weight"] == payload["base_weight"]
            assert record["is_deleted"] == 0
            assert record["created_at"] is not None
            assert record["updated_at"] is not None
            
            print("\n[PASSED] E23-S1 flow complete.")

            # ====================================================
            # 第二阶段：E23-S2 冷启动空锁占位与防穿透
            # ====================================================
            # 1. 此时库中由于 E23-S1 的写入，新增加了一条活跃格言。我们需要在这里将它也临时设为删除，以进入纯净的冷启动空库测试状态
            await db.execute("UPDATE diary_quote_lib SET is_deleted = 1 WHERE is_deleted = 0")
            
            # 2. 清理今日可能已存在的锁定记录
            await db.execute(
                "DELETE FROM diary_checkin_lock WHERE user_id = %s AND business_date = %s AND checkin_type = 2",
                (user_id, bus_date)
            )
            
            # 3. 首次调用 -> 预期返回 EMPTY_LIB 状态，但接口本身成功 (200)
            response_cold1 = await ac.get("/api/v1/checkin/today", headers=headers)
            assert response_cold1.status_code == 200
            res_cold1_data = response_cold1.json()
            assert res_cold1_data["data"]["msg"] == "EMPTY_LIB"
            assert res_cold1_data["data"]["quote"] is None
            
            # 4. 再次调用 -> 预期幂等返回 EMPTY_LIB 且不应重新扫描
            response_cold2 = await ac.get("/api/v1/checkin/today", headers=headers)
            res_cold2_data = response_cold2.json()
            assert res_cold2_data["data"]["msg"] == "EMPTY_LIB"
            
            # 5. 验证数据库中确实写入了空锁 (locked_target_id IS NULL)
            lock_res = await db.execute(
                "SELECT locked_target_id, status FROM diary_checkin_lock WHERE user_id = %s AND business_date = %s AND checkin_type = 2",
                (user_id, bus_date)
            )
            assert lock_res
            assert lock_res[0]["locked_target_id"] is None
            assert lock_res[0]["status"] == 0
            
            print("\n[PASSED] E23-S2 cold-start lock complete.")

            # ====================================================
            # 第三阶段：E23-S2 每日格言加权分配与日内幂等锁定
            # ====================================================
            # 1. 彻底清除刚才临时写下的空锁定记录，以便重新触发加权推荐
            await db.execute(
                "DELETE FROM diary_checkin_lock WHERE user_id = %s AND business_date = %s AND checkin_type = 2",
                (user_id, bus_date)
            )
            
            # 2. 写入两条测试格言 A 和 B (由于原本的所有格言被 is_deleted=1 隔离，此时池子里只有 A 和 B 两个合法候选)
            quote_a_id = await db.execute_insert(
                "INSERT INTO diary_quote_lib (owner_user_id, content, source_author, source_book, category, base_weight) VALUES (%s, %s, %s, %s, 1, 80)",
                (user_id, "这是格言A的内容，必须大于十个字，符合Pydantic校验。", "作者A", "书籍A")
            )
            quote_b_id = await db.execute_insert(
                "INSERT INTO diary_quote_lib (owner_user_id, content, source_author, source_book, category, base_weight) VALUES (%s, %s, %s, %s, 2, 40)",
                (user_id, "这是格言B的内容，也必须大于十个字，符合校验要求。", "作者B", "书籍B")
            )
            
            try:
                # 3. 首次调用接口进行轮询并锁定
                response_lock1 = await ac.get("/api/v1/checkin/today", headers=headers)
                assert response_lock1.status_code == 200
                res_lock1_data = response_lock1.json()
                picked_quote = res_lock1_data["data"]["quote"]
                assert picked_quote is not None
                picked_id = picked_quote["id"]
                assert picked_id in (quote_a_id, quote_b_id)
                
                # 4. 再次调用接口，预期命中日内锁，幂等返回完全一样的格言
                response_lock2 = await ac.get("/api/v1/checkin/today", headers=headers)
                picked_id2 = response_lock2.json()["data"]["quote"]["id"]
                assert picked_id2 == picked_id
                
                # 5. 验证曝光计数及曝光时间入库
                state_res = await db.execute(
                    "SELECT expose_count, last_exposed_at FROM diary_quote_user_state WHERE user_id = %s AND quote_id = %s",
                    (user_id, picked_id)
                )
                assert state_res
                assert state_res[0]["expose_count"] >= 1
                assert state_res[0]["last_exposed_at"] is not None
                
                print("\n[PASSED] E23-S2 lock complete. Now entering S3-S8 functional testing.")

                # ====================================================
                # 第四阶段：E23-S5/S6/S7/S8 后续动作与打卡心得完成接口验证
                # ====================================================
                # 1. 验证收藏动作接口 (POST /maxim/action - favorite)
                fav_payload = {
                    "quote_id": picked_id,
                    "action_type": "favorite",
                    "value": 1
                }
                fav_resp = await ac.post("/api/v1/checkin/maxim/action", json=fav_payload, headers=headers)
                assert fav_resp.status_code == 200
                fav_db_res = await db.execute(
                    "SELECT is_favorited FROM diary_quote_user_state WHERE user_id = %s AND quote_id = %s",
                    (user_id, picked_id)
                )
                assert fav_db_res
                assert fav_db_res[0]["is_favorited"] == 1
                print("\n[PASSED] E23-S5 favorite action complete.")

                # 2. 验证永久屏蔽动作接口 (POST /maxim/action - dislike)
                dislike_payload = {
                    "quote_id": picked_id,
                    "action_type": "dislike",
                    "value": 1
                }
                dislike_resp = await ac.post("/api/v1/checkin/maxim/action", json=dislike_payload, headers=headers)
                assert dislike_resp.status_code == 200
                dis_db_res = await db.execute(
                    "SELECT is_disliked FROM diary_quote_user_state WHERE user_id = %s AND quote_id = %s",
                    (user_id, picked_id)
                )
                assert dis_db_res
                assert dis_db_res[0]["is_disliked"] == 1
                print("\n[PASSED] E23-S6 dislike action complete.")

                # 3. 验证打卡感悟提交限制校验 (最低 30 字，最高 500 字)
                submit_too_short = {
                    "quote_id": picked_id,
                    "insight": "字数太少太少",
                    "mood": 2
                }
                resp_too_short = await ac.post("/api/v1/checkin/maxim/submit", json=submit_too_short, headers=headers)
                assert resp_too_short.status_code == 422
                
                # 4. 验证合法打卡感悟提交 (字数大等于30个字符)
                submit_payload = {
                    "quote_id": picked_id,
                    "insight": "这是一段非常深刻并且字数一定要大于三十个汉字才可以正常通过后台Pydantic拦截校验的投资感悟反思，测试落库与锁更新逻辑。",
                    "mood": 1
                }
                submit_resp = await ac.post("/api/v1/checkin/maxim/submit", json=submit_payload, headers=headers)
                assert submit_resp.status_code == 200
                submit_res_data = submit_resp.json()["data"]
                assert submit_res_data["diary_id"] > 0
                diary_id = submit_res_data["diary_id"]
                assert "格言解读 ·" in submit_res_data["title"]
                assert submit_res_data["accumulated_insight_count"] == 1

                # 5. 校验数据库随笔日记落库、锁表状态更新、多度解读计数更新的事务闭环性
                diary_res = await db.execute(
                    "SELECT title, content, deleted_at FROM diary_entry WHERE id = %s",
                    (diary_id,)
                )
                assert diary_res
                assert diary_res[0]["title"] == submit_res_data["title"]
                assert "投资感悟反思" in diary_res[0]["content"]
                assert diary_res[0]["deleted_at"] is None

                # 验证锁记录已标记为 status = 1 且 completed_diary_id 正确回填
                lock_verify = await db.execute(
                    "SELECT status, completed_diary_id FROM diary_checkin_lock WHERE user_id = %s AND business_date = %s AND checkin_type = 2",
                    (user_id, bus_date)
                )
                assert lock_verify
                assert lock_verify[0]["status"] == 1
                assert lock_verify[0]["completed_diary_id"] == diary_id

                # 验证行为状态表的解读计数累加成功，且因大于50字 deep_insight_count 也应为 1
                state_verify = await db.execute(
                    "SELECT insight_count, deep_insight_count FROM diary_quote_user_state WHERE user_id = %s AND quote_id = %s",
                    (user_id, picked_id)
                )
                assert state_verify
                assert state_verify[0]["insight_count"] == 1
                assert state_verify[0]["deep_insight_count"] == 1
                print("\n[PASSED] E23-S7 submit & diary integration complete.")

                # 6. 验证重复提交拦截保护
                submit_dup_resp = await ac.post("/api/v1/checkin/maxim/submit", json=submit_payload, headers=headers)
                assert submit_dup_resp.status_code == 400
                resp_json = submit_dup_resp.json()
                error_msg = ""
                if "detail" in resp_json:
                    error_msg = resp_json["detail"]
                elif "error" in resp_json and "message" in resp_json["error"]:
                    error_msg = resp_json["error"]["message"]
                elif "message" in resp_json:
                    error_msg = resp_json["message"]
                assert "重复提交" in error_msg
                print("\n[PASSED] E23-S7 duplicate submit interception complete.")

                # 7. 验证反思见解聚合时间轴接口 (GET /maxim/timeline)
                timeline_resp = await ac.get(f"/api/v1/checkin/maxim/timeline?quote_id={picked_id}", headers=headers)
                assert timeline_resp.status_code == 200
                timeline_data = timeline_resp.json()["data"]
                assert timeline_data["quote_id"] == picked_id
                assert timeline_data["total_insights"] == 1
                assert len(timeline_data["timeline"]) == 1
                assert "投资感悟反思" in timeline_data["timeline"][0]["insight"]
                assert timeline_data["timeline"][0]["diary_id"] == diary_id
                print("\n[PASSED] E23-S8 timeline fetch complete.")

            finally:
                # 物理删除所有生成关联的数据，保持测试前后完全干净
                if 'diary_id' in locals():
                    await db.execute("DELETE FROM diary_entry WHERE id = %s", (diary_id,))
                await db.execute("DELETE FROM diary_quote_lib WHERE id IN (%s, %s)", (quote_a_id, quote_b_id))
                await db.execute("DELETE FROM diary_quote_user_state WHERE quote_id IN (%s, %s)", (quote_a_id, quote_b_id))
                await db.execute("DELETE FROM diary_checkin_lock WHERE user_id = %s AND business_date = %s", (user_id, bus_date))

            print("\n[PASSED] E23-S3 to E23-S8 functional integration test completed.")
            
    finally:
        # 彻底清理在 E23-S1 写入的临时格言
        if 'quote_id' in locals():
            await db.execute("DELETE FROM diary_quote_lib WHERE id = %s", (quote_id,))
            
        # 恢复先前被屏蔽 of 非测试格言
        if backup_quotes:
            for q in backup_quotes:
                await db.execute("UPDATE diary_quote_lib SET is_deleted = 0 WHERE id = %s", (q["id"],))

@pytest.mark.asyncio
async def test_e23_s2_business_date_logic():
    """验证凌晨 4:00 时间线划分判定 (T1)"""
    # 模拟凌晨 3:30 的时间对象
    time_330 = datetime(2026, 5, 19, 3, 30, 0)
    bus_date_330 = checkin_service.get_business_date(time_330)
    # 应被归属为前一天
    assert bus_date_330 == date(2026, 5, 18)
    
    # 模拟清晨 4:01 的时间对象
    time_401 = datetime(2026, 5, 19, 4, 1, 0)
    bus_date_401 = checkin_service.get_business_date(time_401)
    # 应被归属为今天
    assert bus_date_401 == date(2026, 5, 19)
    
    print("\n[PASSED] E23-S2 4:00 AM cutoff logic verified successfully!")
