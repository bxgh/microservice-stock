from fastapi import APIRouter, Depends, Query, Path
from typing import Optional
from app.models.diary import DiaryEntryCreate, DiaryEntryUpdate, DiaryEntryResponse, PaginatedDiaryResponse, DiaryStatsResponse
from app.services.diary_service import diary_service
from app.utils.auth import get_current_user_id

router = APIRouter()

@router.get("", response_model=PaginatedDiaryResponse, summary="获取日记列表")
async def get_diaries(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    tag: Optional[str] = Query(None, description="按标签筛选"),
    entry_type: Optional[int] = Query(None, description="按类型筛选"),
    search: Optional[str] = Query(None, description="全文搜索"),
    user_id: int = Depends(get_current_user_id)
):
    items, total = await diary_service.get_list(user_id, page, size, tag, entry_type, search)
    return PaginatedDiaryResponse(
        items=items,
        total=total,
        page=page,
        size=size
    )

@router.get("/stats", response_model=DiaryStatsResponse, summary="获取日记看板统计")
async def get_diary_stats(
    user_id: int = Depends(get_current_user_id)
):
    return await diary_service.get_stats(user_id)

@router.get("/{diary_id}", response_model=DiaryEntryResponse, summary="获取日记详情")
async def get_diary(
    diary_id: int = Path(..., description="日记 ID"),
    user_id: int = Depends(get_current_user_id)
):
    return await diary_service.get_by_id(user_id, diary_id)

@router.post("", response_model=DiaryEntryResponse, summary="创建日记")
async def create_diary(
    data: DiaryEntryCreate,
    user_id: int = Depends(get_current_user_id)
):
    return await diary_service.create(user_id, data)

@router.put("/{diary_id}", response_model=DiaryEntryResponse, summary="更新日记")
async def update_diary(
    data: DiaryEntryUpdate,
    diary_id: int = Path(..., description="日记 ID"),
    user_id: int = Depends(get_current_user_id)
):
    return await diary_service.update(user_id, diary_id, data)

@router.delete("/{diary_id}", summary="删除日记")
async def delete_diary(
    diary_id: int = Path(..., description="日记 ID"),
    user_id: int = Depends(get_current_user_id)
):
    await diary_service.delete(user_id, diary_id)
    return {"message": "Deleted successfully"}
