from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
import httpx
import pandas as pd
import io
import re
from enum import Enum
import asyncio
import shutil
from fastapi.staticfiles import StaticFiles

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Upload directory
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
(UPLOAD_DIR / "images").mkdir(exist_ok=True)
(UPLOAD_DIR / "videos").mkdir(exist_ok=True)
(UPLOAD_DIR / "documents").mkdir(exist_ok=True)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

# BizChat API configuration
BIZCHAT_API_BASE = os.environ.get('BIZCHAT_API_BASE', 'https://bizchatapi.in/api')
BIZCHAT_VENDOR_UID = os.environ.get('BIZCHAT_VENDOR_UID', '9a1497da-b76f-4666-a439-70402e99db57')

# Super admin email - cannot be deleted or paused
SUPER_ADMIN_EMAIL = os.environ.get('SUPER_ADMIN_EMAIL', 'bizchatapi@gmail.com')

# Models
class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    firstName: str
    lastName: str
    role: Role = Role.USER
    bizChatToken: Optional[str] = None
    bizChatVendorUID: Optional[str] = None
    dailyLimit: int = 1000
    dailyUsage: int = 0
    lastResetDate: Optional[str] = None
    isPaused: bool = False
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    firstName: str
    lastName: str
    role: Optional[Role] = Role.USER

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    bizChatToken: Optional[str] = None
    bizChatVendorUID: Optional[str] = None

class PasswordChange(BaseModel):
    currentPassword: str
    newPassword: str

class UserPauseUpdate(BaseModel):
    isPaused: bool

class UserLimitUpdate(BaseModel):
    dailyLimit: int

class CampaignStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    SCHEDULED = "scheduled"
    PAUSED = "paused"
    CANCELLED = "cancelled"

class MessageStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"

class RecipientInfo(BaseModel):
    phone: str
    name: str
    status: MessageStatus = MessageStatus.PENDING
    messageId: Optional[str] = None
    error: Optional[str] = None
    sentAt: Optional[datetime] = None

class Campaign(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str
    name: str
    templateName: str
    recipients: List[RecipientInfo]
    totalCount: int
    sentCount: int = 0
    failedCount: int = 0
    pendingCount: int
    scheduledAt: Optional[datetime] = None
    status: CampaignStatus = CampaignStatus.PENDING
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completedAt: Optional[datetime] = None

class SendMessageRequest(BaseModel):
    recipients: List[Dict[str, str]]  # [{"phone": "+123", "name": "John", "field_1": "value1", ...}]
    templateName: str
    campaignName: str
    countryCode: Optional[str] = None
    scheduledAt: Optional[datetime] = None
    templateParameters: Optional[Dict[str, Any]] = None  # Template-level parameters
    # Media headers
    header_image: Optional[str] = None
    header_video: Optional[str] = None
    header_document: Optional[str] = None
    header_document_name: Optional[str] = None
    header_field_1: Optional[str] = None
    # Location data
    location_latitude: Optional[str] = None
    location_longitude: Optional[str] = None
    location_name: Optional[str] = None
    location_address: Optional[str] = None

class SavedTemplate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str
    name: str  # User-friendly name for this saved template
    templateName: str  # BizChat template name
    templateLanguage: str = "en"
    field1: Optional[str] = None
    field2: Optional[str] = None
    field3: Optional[str] = None
    field4: Optional[str] = None
    field5: Optional[str] = None
    # Media fields
    header_image: Optional[str] = None
    header_video: Optional[str] = None
    header_document: Optional[str] = None
    header_document_name: Optional[str] = None
    header_field_1: Optional[str] = None
    # Location fields
    location_latitude: Optional[str] = None
    location_longitude: Optional[str] = None
    location_name: Optional[str] = None
    location_address: Optional[str] = None
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SavedTemplateCreate(BaseModel):
    name: str
    templateName: str
    templateLanguage: str = "en"
    field1: Optional[str] = None
    field2: Optional[str] = None
    field3: Optional[str] = None
    field4: Optional[str] = None
    field5: Optional[str] = None
    # Media fields
    header_image: Optional[str] = None
    header_video: Optional[str] = None
    header_document: Optional[str] = None
    header_document_name: Optional[str] = None
    header_field_1: Optional[str] = None
    # Location fields
    location_latitude: Optional[str] = None
    location_longitude: Optional[str] = None
    location_name: Optional[str] = None
    location_address: Optional[str] = None

class TemplateParameter(BaseModel):
    type: str = "text"
    text: str

class TokenData(BaseModel):
    userId: str
    email: str
    role: Role

# Helper functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(user_id: str, email: str, role: str) -> str:
    expiration = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        'userId': user_id,
        'email': email,
        'role': role,
        'exp': expiration
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_data = TokenData(
            userId=payload['userId'],
            email=payload['email'],
            role=payload['role']
        )
        
        # Check if user exists and is not paused
        user = await db.users.find_one({"id": user_data.userId})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        if user.get('isPaused', False):
            raise HTTPException(status_code=403, detail="Account is paused")
        
        return user_data
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def require_admin(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

def normalize_phone_number(phone: str, country_code: Optional[str] = None) -> str:
    # Remove all non-digit characters
    phone = re.sub(r'\D', '', phone)
    
    # If phone already has a country code (starts with proper length), return as is
    if phone.startswith('1') and len(phone) >= 10:  # US/Canada
        return '+' + phone
    if len(phone) >= 10 and not country_code:
        return '+' + phone
    
    # Add country code if provided and phone doesn't start with it
    if country_code:
        country_code = re.sub(r'\D', '', country_code)
        if not phone.startswith(country_code):
            phone = country_code + phone
    
    return '+' + phone if not phone.startswith('+') else phone

# Auth Routes
@api_router.post("/auth/register")
async def register(user_data: UserRegister, current_user: TokenData = Depends(require_admin)):
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

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user['password']):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if user.get('isPaused', False):
        raise HTTPException(status_code=403, detail="Account is paused")
    
    token = create_access_token(user['id'], user['email'], user['role'])
    
    return {
        "token": token,
        "user": {
            "id": user['id'],
            "email": user['email'],
            "firstName": user['firstName'],
            "lastName": user['lastName'],
            "role": user['role']
        }
    }

@api_router.get("/auth/me")
async def get_me(current_user: TokenData = Depends(get_current_user)):
    user = await db.users.find_one({"id": current_user.userId}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@api_router.post("/auth/change-password")
async def change_password(password_data: PasswordChange, current_user: TokenData = Depends(get_current_user)):
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

# User Routes
@api_router.get("/users")
async def get_users(current_user: TokenData = Depends(require_admin)):
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    return {"users": users}

@api_router.get("/users/{user_id}")
async def get_user(user_id: str, current_user: TokenData = Depends(get_current_user)):
    # Users can only view their own profile unless they're admin
    if current_user.role != Role.ADMIN and current_user.userId != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@api_router.put("/users/{user_id}")
async def update_user(user_id: str, update_data: UserUpdate, current_user: TokenData = Depends(get_current_user)):
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

@api_router.put("/users/{user_id}/pause")
async def pause_user(user_id: str, pause_data: UserPauseUpdate, current_user: TokenData = Depends(require_admin)):
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

@api_router.put("/users/{user_id}/limit")
async def set_user_limit(user_id: str, limit_data: UserLimitUpdate, current_user: TokenData = Depends(require_admin)):
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"dailyLimit": limit_data.dailyLimit, "updatedAt": datetime.now(timezone.utc).isoformat()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "Daily limit updated successfully"}

@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: TokenData = Depends(require_admin)):
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
    result = await db.users.delete_one({"id": user_id})
    
    # Also delete user's campaigns, templates, and other data
    await db.campaigns.delete_many({"userId": user_id})
    await db.saved_templates.delete_many({"userId": user_id})
    
    return {"message": "User deleted successfully"}

# Saved Templates Routes (user's custom template presets)
@api_router.post("/saved-templates")
async def create_saved_template(template_data: SavedTemplateCreate, current_user: TokenData = Depends(get_current_user)):
    # Check if name already exists for this user
    existing = await db.saved_templates.find_one({"userId": current_user.userId, "name": template_data.name})
    if existing:
        raise HTTPException(status_code=400, detail="Template name already exists")
    
    template = SavedTemplate(
        userId=current_user.userId,
        **template_data.model_dump()
    )
    
    template_dict = template.model_dump()
    template_dict['createdAt'] = template_dict['createdAt'].isoformat()
    template_dict['updatedAt'] = template_dict['updatedAt'].isoformat()
    
    await db.saved_templates.insert_one(template_dict)
    
    return {"message": "Template saved successfully", "templateId": template.id}

@api_router.get("/saved-templates")
async def get_saved_templates(current_user: TokenData = Depends(get_current_user)):
    templates = await db.saved_templates.find(
        {"userId": current_user.userId},
        {"_id": 0}
    ).sort("createdAt", -1).to_list(100)
    
    return {"templates": templates}

@api_router.get("/saved-templates/{template_id}")
async def get_saved_template(template_id: str, current_user: TokenData = Depends(get_current_user)):
    template = await db.saved_templates.find_one(
        {"id": template_id, "userId": current_user.userId},
        {"_id": 0}
    )
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return template

@api_router.put("/saved-templates/{template_id}")
async def update_saved_template(
    template_id: str,
    template_data: SavedTemplateCreate,
    current_user: TokenData = Depends(get_current_user)
):
    # Check ownership
    template = await db.saved_templates.find_one({"id": template_id, "userId": current_user.userId})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Check if new name conflicts with another template
    if template_data.name != template['name']:
        existing = await db.saved_templates.find_one({
            "userId": current_user.userId,
            "name": template_data.name,
            "id": {"$ne": template_id}
        })
        if existing:
            raise HTTPException(status_code=400, detail="Template name already exists")
    
    update_dict = template_data.model_dump()
    update_dict['updatedAt'] = datetime.now(timezone.utc).isoformat()
    
    await db.saved_templates.update_one(
        {"id": template_id},
        {"$set": update_dict}
    )
    
    return {"message": "Template updated successfully"}

@api_router.delete("/saved-templates/{template_id}")
async def delete_saved_template(template_id: str, current_user: TokenData = Depends(get_current_user)):
    result = await db.saved_templates.delete_one({"id": template_id, "userId": current_user.userId})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {"message": "Template deleted successfully"}

# Message Routes
async def send_whatsapp_message(
    phone: str,
    template_name: str,
    token: str,
    vendor_uid: str,
    recipient_data: Dict[str, Any]
) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient() as client:
            url = f"{BIZCHAT_API_BASE}/{vendor_uid}/contact/send-template-message?token={token}"
            
            # Build payload according to BizChat API documentation
            payload = {
                "phone_number": phone.replace('+', '').replace('-', '').replace(' ', ''),
                "template_name": template_name,
                "template_language": recipient_data.get("template_language", "en")
            }
            
            # BizChat expects BOTH formats:
            # 1. Direct field_1, field_2, etc. for their validation
            # 2. Components array for WhatsApp Business API
            
            # Add direct field_1 through field_5 parameters
            body_params = []
            recipient_name = recipient_data.get('name', '')
            
            for i in range(1, 6):  # field_1 through field_5
                field_key = f"field_{i}"
                if field_key in recipient_data and recipient_data[field_key]:
                    value = str(recipient_data[field_key]).strip()
                    if value:
                        # Replace {name} placeholder with actual name
                        if '{name}' in value and recipient_name:
                            value = value.replace('{name}', recipient_name)
                        
                        # Add as direct field
                        payload[field_key] = value
                        # Also add to body parameters for components array
                        body_params.append({
                            "type": "text",
                            "text": value
                        })
            
            # Add components array for WhatsApp format
            if body_params:
                payload["components"] = [{
                    "type": "body",
                    "parameters": body_params
                }]
            
            # Add other direct parameters (header_image, header_video, buttons, etc.)
            for key, value in recipient_data.items():
                if key not in ["phone", "name", "template_language"] and not key.startswith("field_"):
                    if value and str(value).strip():
                        payload[key] = str(value).strip()
            
            logger.info(f"Sending to BizChat - Phone: {phone}, Template: {template_name}, Payload keys: {list(payload.keys())}")
            
            response = await client.post(url, json=payload, timeout=30.0)
            
            if response.status_code in [200, 201]:
                data = response.json()
                return {"success": True, "data": data}
            else:
                error_msg = f"BizChat API Error: Status {response.status_code}, Response: {response.text}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = f"Exception sending message: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

async def process_campaign(campaign_id: str, user_token: str, vendor_uid: str):
    """Process campaign with rate limiting (29 messages/second)"""
    import asyncio
    
    campaign = await db.campaigns.find_one({"id": campaign_id})
    if not campaign:
        return
    
    # Update status to processing
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {"status": CampaignStatus.PROCESSING.value}}
    )
    
    sent_count = campaign.get('sentCount', 0)
    failed_count = campaign.get('failedCount', 0)
    
    # Rate limiting: 29 messages per second
    delay_between_messages = 1.0 / 29  # ~0.034 seconds
    
    batch_size = 100  # Process in batches for better control
    pause_check_interval = 10  # Check for pause every 10 messages instead of every message
    
    for i, recipient in enumerate(campaign['recipients']):
        # Check if campaign is paused - only every 10 messages to avoid DB overhead
        if i % pause_check_interval == 0:
            current_campaign = await db.campaigns.find_one({"id": campaign_id}, {"status": 1})
            if current_campaign and current_campaign.get('status') == CampaignStatus.PAUSED.value:
                logger.info(f"Campaign {campaign_id} paused at message {i}")
                return
        
        if recipient['status'] != MessageStatus.PENDING.value:
            continue
        
        # Send message with recipient-specific data
        result = await send_whatsapp_message(
            recipient['phone'],
            campaign['templateName'],
            user_token,
            vendor_uid,
            recipient
        )
        
        if result['success']:
            sent_count += 1
            campaign['recipients'][i]['status'] = MessageStatus.SENT.value
            campaign['recipients'][i]['sentAt'] = datetime.now(timezone.utc).isoformat()
            campaign['recipients'][i]['messageId'] = result.get('data', {}).get('message_id')
        else:
            failed_count += 1
            campaign['recipients'][i]['status'] = MessageStatus.FAILED.value
            campaign['recipients'][i]['error'] = result['error']
        
        # Update campaign every batch or when significant change
        if (i + 1) % batch_size == 0 or (i + 1) == len(campaign['recipients']):
            await db.campaigns.update_one(
                {"id": campaign_id},
                {
                    "$set": {
                        "recipients": campaign['recipients'],
                        "sentCount": sent_count,
                        "failedCount": failed_count,
                        "pendingCount": campaign['totalCount'] - sent_count - failed_count,
                        "updatedAt": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
        
        # Rate limiting
        await asyncio.sleep(delay_between_messages)
    
    # Final update - mark as completed
    await db.campaigns.update_one(
        {"id": campaign_id},
        {
            "$set": {
                "recipients": campaign['recipients'],
                "sentCount": sent_count,
                "failedCount": failed_count,
                "pendingCount": campaign['totalCount'] - sent_count - failed_count,
                "status": CampaignStatus.COMPLETED.value,
                "completedAt": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Update user's daily usage - ONLY count successfully sent messages (not failed)
    await db.users.update_one(
        {"id": campaign['userId']},
        {"$inc": {"dailyUsage": sent_count}}
    )


async def check_scheduled_campaigns():
    """Background task to check and process scheduled campaigns"""
    while True:
        try:
            # Find campaigns that are scheduled and whose time has come
            now = datetime.now(timezone.utc)
            
            scheduled_campaigns = await db.campaigns.find({
                "status": CampaignStatus.SCHEDULED.value,
                "scheduledAt": {"$lte": now.isoformat()}
            }).to_list(100)
            
            for campaign in scheduled_campaigns:
                logger.info(f"Processing scheduled campaign: {campaign['id']}")
                
                # Get user's BizChat credentials
                user = await db.users.find_one({"id": campaign['userId']})
                if not user or not user.get('bizChatToken') or not user.get('bizChatVendorUID'):
                    logger.error(f"User {campaign['userId']} missing BizChat credentials")
                    # Mark campaign as failed
                    await db.campaigns.update_one(
                        {"id": campaign['id']},
                        {"$set": {"status": CampaignStatus.COMPLETED.value, "completedAt": now.isoformat()}}
                    )
                    continue
                
                # Update status to processing
                await db.campaigns.update_one(
                    {"id": campaign['id']},
                    {"$set": {"status": CampaignStatus.PROCESSING.value}}
                )
                
                # Process campaign in background
                asyncio.create_task(
                    process_campaign(
                        campaign['id'],
                        user['bizChatToken'],
                        user['bizChatVendorUID']
                    )
                )
            
        except Exception as e:
            logger.error(f"Error in check_scheduled_campaigns: {str(e)}")
        
        # Check every minute
        await asyncio.sleep(60)



@api_router.post("/upload/media")
async def upload_media(
    file: UploadFile = File(...),
    media_type: str = "image",  # image, video, document
    current_user: TokenData = Depends(get_current_user)
):
    """Upload media file and return URL"""
    try:
        # Validate media type
        if media_type not in ["image", "video", "document"]:
            raise HTTPException(status_code=400, detail="Invalid media type")
        
        # Validate file type
        allowed_extensions = {
            "image": [".jpg", ".jpeg", ".png", ".gif", ".webp"],
            "video": [".mp4", ".mov", ".avi", ".mkv", ".webm"],
            "document": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".csv"]
        }
        
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in allowed_extensions[media_type]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions[media_type])}"
            )
        
        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = UPLOAD_DIR / f"{media_type}s" / unique_filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Generate URL (will work with REACT_APP_BACKEND_URL)
        file_url = f"/uploads/{media_type}s/{unique_filename}"
        
        return {
            "success": True,
            "filename": file.filename,
            "url": file_url,
            "type": media_type
        }
    
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@api_router.post("/messages/send")
async def send_messages(
    request: SendMessageRequest,
    background_tasks: BackgroundTasks,
    current_user: TokenData = Depends(get_current_user)
):
    # Get user's BizChat credentials
    user = await db.users.find_one({"id": current_user.userId})
    if not user or not user.get('bizChatToken'):
        raise HTTPException(status_code=400, detail="BizChat API token not configured")
    if not user.get('bizChatVendorUID'):
        raise HTTPException(status_code=400, detail="BizChat Vendor UID not configured")
    
    # Check daily limit
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    last_reset = user.get('lastResetDate')
    daily_usage = user.get('dailyUsage', 0)
    daily_limit = user.get('dailyLimit', 1000)
    
    # Reset daily usage if it's a new day
    if last_reset != today:
        daily_usage = 0
        await db.users.update_one(
            {"id": current_user.userId},
            {"$set": {"dailyUsage": 0, "lastResetDate": today}}
        )
    
    # Check if user can send these messages
    remaining = daily_limit - daily_usage
    if len(request.recipients) > remaining:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot send campaign. You need {len(request.recipients)} messages but only {remaining} available today. Daily limit: {daily_limit}/day"
        )
    
    # Normalize phone numbers and prepare recipients with template data
    recipients = []
    for recipient in request.recipients:
        phone = normalize_phone_number(recipient['phone'], request.countryCode)
        recipient_info = RecipientInfo(
            phone=phone,
            name=recipient.get('name', ''),
            status=MessageStatus.PENDING
        )
        
        # Convert to dict and add all template parameters
        recipient_dict = recipient_info.model_dump()
        for key, value in recipient.items():
            if key not in ['phone', 'name']:
                recipient_dict[key] = value
        
        # Add campaign-level media and location fields to each recipient
        if request.header_image:
            recipient_dict['header_image'] = request.header_image
        if request.header_video:
            recipient_dict['header_video'] = request.header_video
        if request.header_document:
            recipient_dict['header_document'] = request.header_document
        if request.header_document_name:
            recipient_dict['header_document_name'] = request.header_document_name
        if request.header_field_1:
            recipient_dict['header_field_1'] = request.header_field_1
        if request.location_latitude:
            recipient_dict['location_latitude'] = request.location_latitude
        if request.location_longitude:
            recipient_dict['location_longitude'] = request.location_longitude
        if request.location_name:
            recipient_dict['location_name'] = request.location_name
        if request.location_address:
            recipient_dict['location_address'] = request.location_address
        
        recipients.append(recipient_dict)
    
    # Create campaign
    campaign = Campaign(
        userId=current_user.userId,
        name=request.campaignName,
        templateName=request.templateName,
        recipients=[RecipientInfo(**r) for r in recipients],
        totalCount=len(recipients),
        pendingCount=len(recipients),
        scheduledAt=request.scheduledAt,
        status=CampaignStatus.SCHEDULED if request.scheduledAt else CampaignStatus.PENDING
    )
    
    campaign_dict = campaign.model_dump()
    campaign_dict['createdAt'] = campaign_dict['createdAt'].isoformat()
    if campaign_dict.get('scheduledAt'):
        campaign_dict['scheduledAt'] = campaign_dict['scheduledAt'].isoformat()
    if campaign_dict.get('completedAt'):
        campaign_dict['completedAt'] = campaign_dict['completedAt'].isoformat()
    
    # Store recipients with all template parameters
    campaign_dict['recipients'] = recipients
    
    await db.campaigns.insert_one(campaign_dict)
    
    # Note: Daily usage will be updated AFTER sending, counting only successful messages
    # Not counting here to avoid counting failed messages
    
    # Process immediately if not scheduled
    if not request.scheduledAt:
        background_tasks.add_task(
            process_campaign,
            campaign.id,
            user['bizChatToken'],
            user['bizChatVendorUID']
        )
    
    return {
        "message": "Campaign created successfully",
        "campaignId": campaign.id,
        "status": "processing" if not request.scheduledAt else "scheduled",
        "dailyUsage": daily_usage + len(recipients),
        "dailyLimit": daily_limit
    }

@api_router.post("/messages/upload")
async def upload_recipients(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="Only Excel or CSV files are supported")
    
    try:
        contents = await file.read()
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
        
        # Expected columns: name, phone
        if 'phone' not in df.columns:
            raise HTTPException(status_code=400, detail="Excel file must contain 'phone' column")
        
        recipients = []
        for _, row in df.iterrows():
            recipients.append({
                "phone": str(row.get('phone', '')),
                "name": str(row.get('name', ''))
            })
        
        return {"recipients": recipients, "count": len(recipients)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")

# Campaign Routes
@api_router.get("/campaigns")
async def get_campaigns(current_user: TokenData = Depends(get_current_user)):
    query = {}
    if current_user.role != Role.ADMIN:
        query['userId'] = current_user.userId
    
    campaigns = await db.campaigns.find(query, {"_id": 0}).sort("createdAt", -1).to_list(100)
    return {"campaigns": campaigns}

@api_router.get("/campaigns/{campaign_id}")
async def get_campaign(campaign_id: str, current_user: TokenData = Depends(get_current_user)):
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Check access
    if current_user.role != Role.ADMIN and campaign['userId'] != current_user.userId:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return campaign

@api_router.get("/campaigns/{campaign_id}/stats")
async def get_campaign_stats(campaign_id: str, current_user: TokenData = Depends(get_current_user)):
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Check access
    if current_user.role != Role.ADMIN and campaign['userId'] != current_user.userId:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "campaignId": campaign_id,
        "name": campaign['name'],
        "totalCount": campaign['totalCount'],
        "sentCount": campaign['sentCount'],
        "failedCount": campaign['failedCount'],
        "pendingCount": campaign['pendingCount'],
        "status": campaign['status']
    }

@api_router.post("/campaigns/{campaign_id}/pause")
async def pause_campaign(campaign_id: str, current_user: TokenData = Depends(get_current_user)):
    campaign = await db.campaigns.find_one({"id": campaign_id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Check access
    if current_user.role != Role.ADMIN and campaign['userId'] != current_user.userId:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if campaign['status'] != CampaignStatus.PROCESSING.value:
        raise HTTPException(status_code=400, detail="Only processing campaigns can be paused")
    
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {"status": CampaignStatus.PAUSED.value}}
    )
    
    return {"message": "Campaign paused successfully"}

@api_router.post("/campaigns/{campaign_id}/resume")
async def resume_campaign(
    campaign_id: str,
    background_tasks: BackgroundTasks,
    current_user: TokenData = Depends(get_current_user)
):
    campaign = await db.campaigns.find_one({"id": campaign_id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Check access
    if current_user.role != Role.ADMIN and campaign['userId'] != current_user.userId:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if campaign['status'] != CampaignStatus.PAUSED.value:
        raise HTTPException(status_code=400, detail="Only paused campaigns can be resumed")
    
    # Get user credentials
    user = await db.users.find_one({"id": campaign['userId']})
    if not user or not user.get('bizChatToken') or not user.get('bizChatVendorUID'):
        raise HTTPException(status_code=400, detail="User BizChat credentials not configured")
    
    # Resume processing
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {"status": CampaignStatus.PROCESSING.value}}
    )
    
    background_tasks.add_task(
        process_campaign,
        campaign_id,
        user['bizChatToken'],
        user['bizChatVendorUID']
    )
    
    return {"message": "Campaign resumed successfully"}

@api_router.post("/campaigns/{campaign_id}/cancel")
async def cancel_campaign(campaign_id: str, current_user: TokenData = Depends(get_current_user)):
    campaign = await db.campaigns.find_one({"id": campaign_id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Check access
    if current_user.role != Role.ADMIN and campaign['userId'] != current_user.userId:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if campaign['status'] in [CampaignStatus.COMPLETED.value, CampaignStatus.CANCELLED.value]:
        raise HTTPException(status_code=400, detail="Campaign already completed or cancelled")
    
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {"status": CampaignStatus.CANCELLED.value}}
    )
    
    return {"message": "Campaign cancelled successfully"}

@api_router.delete("/campaigns/{campaign_id}")
async def delete_campaign(campaign_id: str, current_user: TokenData = Depends(get_current_user)):
    campaign = await db.campaigns.find_one({"id": campaign_id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Check access
    if current_user.role != Role.ADMIN and campaign['userId'] != current_user.userId:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Delete campaign (does NOT affect daily usage count - that stays as is)
    await db.campaigns.delete_one({"id": campaign_id})
    
    return {"message": "Campaign deleted successfully"}

# Include the router in the main app
app.include_router(api_router)

# Mount static files for uploaded media - AFTER api_router
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    # Create default admin user if not exists
    admin = await db.users.find_one({"email": "bizchatapi@gmail.com"})
    if not admin:
        admin_user = User(
            email="bizchatapi@gmail.com",
            firstName="BizChat",
            lastName="Admin",
            role=Role.ADMIN
        )
        admin_dict = admin_user.model_dump()
        admin_dict['password'] = hash_password("admin123")
        admin_dict['createdAt'] = admin_dict['createdAt'].isoformat()
        admin_dict['updatedAt'] = admin_dict['updatedAt'].isoformat()
        await db.users.insert_one(admin_dict)
        logger.info("Default admin user created: bizchatapi@gmail.com / admin123")
    
    # Start scheduled campaigns checker in background
    asyncio.create_task(check_scheduled_campaigns())
    logger.info("Scheduled campaigns checker started")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()