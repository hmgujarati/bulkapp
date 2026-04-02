"""User management routes"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone

from models.schemas import UserUpdate, UserPauseUpdate, UserLimitUpdate, Role
from utils.auth import get_current_user, require_admin, SUPER_ADMIN_EMAIL
from utils.database import db

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("")
async def get_users(current_user = Depends(require_admin)):
    """Get all users (admin only)"""
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    return {"users": users}


@router.get("/{user_id}")
async def get_user(user_id: str, current_user = Depends(get_current_user)):
    """Get a specific user"""
    # Users can only view their own profile unless they're admin
    if current_user.role != Role.ADMIN and current_user.userId != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}")
async def update_user(user_id: str, update_data: UserUpdate, current_user = Depends(get_current_user)):
    """Update a user's profile"""
    # Users can only update their own profile unless they're admin
    if current_user.role != Role.ADMIN and current_user.userId != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    update_dict['updatedAt'] = datetime.now(timezone.utc).isoformat()
    
    result = await db.users.update_one({"id": user_id}, {"$set": update_dict})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User updated successfully"}


@router.put("/{user_id}/pause")
async def pause_user(user_id: str, pause_data: UserPauseUpdate, current_user = Depends(require_admin)):
    """Pause or unpause a user (admin only)"""
    # Check if user is super admin
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user['email'] == SUPER_ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Cannot pause super admin account")
    
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"isPaused": pause_data.isPaused, "updatedAt": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": f"User {'paused' if pause_data.isPaused else 'unpaused'} successfully"}


@router.put("/{user_id}/limit")
async def set_user_limit(user_id: str, limit_data: UserLimitUpdate, current_user = Depends(require_admin)):
    """Set user's daily message limit (admin only)"""
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"dailyLimit": limit_data.dailyLimit, "updatedAt": datetime.now(timezone.utc).isoformat()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "Daily limit updated successfully"}


@router.put("/{user_id}/features")
async def update_user_features(user_id: str, features: dict, current_user = Depends(require_admin)):
    """Update user's feature access (admin only)"""
    # Validate features dict
    valid_features = ["bulk_messages", "reminders", "contacts", "templates", "campaigns", "indiamart", "chatbot"]
    for key in features.keys():
        if key not in valid_features:
            raise HTTPException(status_code=400, detail=f"Invalid feature: {key}")
    
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Merge with existing features
    existing_features = user.get('features', {
        "bulk_messages": True,
        "reminders": True,
        "contacts": True,
        "templates": True,
        "campaigns": True,
        "indiamart": False,
        "chatbot": False
    })
    existing_features.update(features)
    
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"features": existing_features, "updatedAt": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "User features updated successfully", "features": existing_features}




@router.delete("/{user_id}")
async def delete_user(user_id: str, current_user = Depends(require_admin)):
    """Delete a user (admin only)"""
    # Get user to check if super admin
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting super admin
    if user['email'] == SUPER_ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Cannot delete super admin account")
    
    # Prevent deleting yourself
    if user_id == current_user.userId:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    # Delete user
    await db.users.delete_one({"id": user_id})
    
    # Also delete user's campaigns, templates, and other data
    await db.campaigns.delete_many({"userId": user_id})
    await db.saved_templates.delete_many({"userId": user_id})
    
    return {"message": "User deleted successfully"}
