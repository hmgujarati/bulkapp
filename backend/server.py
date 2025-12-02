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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

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
BIZCHAT_API_BASE = "https://bizchatapi.in/api"
BIZCHAT_VENDOR_UID = "9a1497da-b76f-4666-a439-70402e99db57"

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
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"isPaused": pause_data.isPaused, "updatedAt": datetime.now(timezone.utc).isoformat()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
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

# Templates endpoint removed - users enter template name directly

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
            
            # Build payload with all recipient-specific parameters
            payload = {
                "phone_number": phone.replace('+', '').replace('-', '').replace(' ', ''),
                "template_name": template_name,
                "template_language": recipient_data.get("template_language", "en")
            }
            
            # Add all dynamic fields from recipient_data
            for key, value in recipient_data.items():
                if key not in ["phone", "name", "template_language"]:
                    payload[key] = value
            
            response = await client.post(url, json=payload, timeout=30.0)
            
            if response.status_code in [200, 201]:
                data = response.json()
                return {"success": True, "data": data}
            else:
                return {"success": False, "error": response.text}
    except Exception as e:
        return {"success": False, "error": str(e)}

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
    
    for i, recipient in enumerate(campaign['recipients']):
        # Check if campaign is paused
        current_campaign = await db.campaigns.find_one({"id": campaign_id})
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
    if daily_usage + len(request.recipients) > daily_limit:
        remaining = daily_limit - daily_usage
        raise HTTPException(
            status_code=400,
            detail=f"Daily limit exceeded. You can send {remaining} more messages today. Limit: {daily_limit}/day"
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
    
    # Update daily usage
    await db.users.update_one(
        {"id": current_user.userId},
        {"$inc": {"dailyUsage": len(recipients)}}
    )
    
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

# Include the router in the main app
app.include_router(api_router)

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
    admin = await db.users.find_one({"email": "admin@masswhatsapp.com"})
    if not admin:
        admin_user = User(
            email="admin@masswhatsapp.com",
            firstName="Admin",
            lastName="User",
            role=Role.ADMIN
        )
        admin_dict = admin_user.model_dump()
        admin_dict['password'] = hash_password("admin123")
        admin_dict['createdAt'] = admin_dict['createdAt'].isoformat()
        admin_dict['updatedAt'] = admin_dict['updatedAt'].isoformat()
        await db.users.insert_one(admin_dict)
        logger.info("Default admin user created: admin@masswhatsapp.com / admin123")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()