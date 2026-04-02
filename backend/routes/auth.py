"""Authentication routes"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone

from models.schemas import UserRegister, UserLogin, PasswordChange, User, Role
from utils.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_admin, SUPER_ADMIN_EMAIL
)
from utils.database import db

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register")
async def register(user_data: UserRegister, current_user = Depends(require_admin)):
    """Register a new user (admin only)"""
    # Check if user already exists
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    hashed_password = hash_password(user_data.password)
    user = User(
        email=user_data.email,
        firstName=user_data.firstName,
        lastName=user_data.lastName,
        role=user_data.role or Role.USER
    )
    
    user_dict = user.model_dump()
    user_dict['password'] = hashed_password
    user_dict['createdAt'] = user_dict['createdAt'].isoformat()
    user_dict['updatedAt'] = user_dict['updatedAt'].isoformat()
    
    await db.users.insert_one(user_dict)
    
    return {"message": "User created successfully", "userId": user.id}


@router.post("/login")
async def login(credentials: UserLogin):
    """Login and get access token"""
    user = await db.users.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user['password']):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if user.get('isPaused', False):
        raise HTTPException(status_code=403, detail="Account is paused")
    
    token = create_access_token(user['id'], user['email'], user['role'])
    
    # Get user features with defaults
    default_features = {
        "bulk_messages": True,
        "reminders": True,
        "contacts": True,
        "templates": True,
        "campaigns": True,
        "indiamart": False,
        "chatbot": False
    }
    user_features = user.get('features', default_features)
    
    return {
        "token": token,
        "user": {
            "id": user['id'],
            "email": user['email'],
            "firstName": user['firstName'],
            "lastName": user['lastName'],
            "role": user['role'],
            "features": user_features
        }
    }


@router.post("/login-as/{user_id}")
async def login_as_user(user_id: str, current_user=Depends(require_admin)):
    """Admin: generate a token to log in as another user for support"""
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    token = create_access_token(target_user['id'], target_user['email'], target_user['role'])

    default_features = {
        "bulk_messages": True, "reminders": True, "contacts": True,
        "templates": True, "campaigns": True, "indiamart": False, "chatbot": False
    }

    return {
        "token": token,
        "user": {
            "id": target_user['id'],
            "email": target_user['email'],
            "firstName": target_user['firstName'],
            "lastName": target_user['lastName'],
            "role": target_user['role'],
            "features": target_user.get('features', default_features)
        }
    }


@router.get("/me")
async def get_me(current_user = Depends(get_current_user)):
    """Get current user info with daily usage status"""
    from utils.daily_limit import check_and_reset_daily_usage
    
    user = await db.users.find_one({"id": current_user.userId}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check and reset daily usage if 24 hours have passed
    user = await check_and_reset_daily_usage(current_user.userId, user)
    
    return user


@router.post("/change-password")
async def change_password(password_data: PasswordChange, current_user = Depends(get_current_user)):
    """Change user password"""
    # Get user with password
    user = await db.users.find_one({"id": current_user.userId})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify current password
    if not verify_password(password_data.currentPassword, user['password']):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Update password
    new_hashed_password = hash_password(password_data.newPassword)
    await db.users.update_one(
        {"id": current_user.userId},
        {"$set": {"password": new_hashed_password, "updatedAt": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Password changed successfully"}
