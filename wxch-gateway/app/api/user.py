from fastapi import APIRouter, Depends
from app.models.user import UserProfile, UserProfileUpdate
from app.services.user_service import user_service
from app.utils.auth import get_current_user_id

router = APIRouter()

@router.get("/profile", response_model=UserProfile, summary="获取用户个人资料")
async def get_profile(user_id: int = Depends(get_current_user_id)):
    return await user_service.get_profile(user_id)

@router.put("/profile", response_model=UserProfile, summary="更新用户个人资料")
async def update_profile(
    data: UserProfileUpdate,
    user_id: int = Depends(get_current_user_id)
):
    return await user_service.update_profile(user_id, data)
