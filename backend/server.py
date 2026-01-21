"""
WhatsApp Bulk Messenger - Main Application
Refactored modular structure
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pathlib import Path
import os
import logging
import asyncio
from datetime import datetime, timezone

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Import routes
from routes.auth import router as auth_router
from routes.users import router as users_router
from routes.templates import router as templates_router
from routes.campaigns import router as campaigns_router
from routes.messages import router as messages_router, process_campaign
from routes.upload import router as upload_router
from routes.reminder_numbers import router as reminder_numbers_router
from routes.reminders import router as reminders_router

# Import utilities
from utils.database import db, close_db_connection
from utils.auth import hash_password, SUPER_ADMIN_EMAIL
from models.schemas import User, Role, CampaignStatus

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Upload directory
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
(UPLOAD_DIR / "images").mkdir(exist_ok=True)
(UPLOAD_DIR / "videos").mkdir(exist_ok=True)
(UPLOAD_DIR / "documents").mkdir(exist_ok=True)

# Create FastAPI app
app = FastAPI(
    title="WhatsApp Bulk Messenger API",
    description="API for sending bulk WhatsApp messages",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with /api prefix
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(templates_router, prefix="/api")
app.include_router(campaigns_router, prefix="/api")
app.include_router(messages_router, prefix="/api")
app.include_router(upload_router, prefix="/api")
app.include_router(reminder_numbers_router, prefix="/api")
app.include_router(reminders_router, prefix="/api")

# Mount static files for uploads
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/api/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="api_uploads")


# Campaign resume endpoint (needs access to process_campaign from messages)
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from utils.auth import get_current_user
from models.schemas import Role, CampaignStatus

resume_router = APIRouter(prefix="/api/campaigns", tags=["Campaigns"])

@resume_router.post("/{campaign_id}/resume")
async def resume_campaign(
    campaign_id: str,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
):
    """Resume a paused campaign"""
    campaign = await db.campaigns.find_one({"id": campaign_id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if current_user.role != Role.ADMIN and campaign['userId'] != current_user.userId:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if campaign['status'] != CampaignStatus.PAUSED.value:
        raise HTTPException(status_code=400, detail="Only paused campaigns can be resumed")
    
    user = await db.users.find_one({"id": campaign['userId']})
    if not user or not user.get('bizChatToken') or not user.get('bizChatVendorUID'):
        raise HTTPException(status_code=400, detail="User BizChat credentials not configured")
    
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

app.include_router(resume_router)


async def check_scheduled_campaigns():
    """Background task to check and process scheduled campaigns"""
    while True:
        try:
            now = datetime.now(timezone.utc)
            
            scheduled_campaigns = await db.campaigns.find({
                "status": CampaignStatus.SCHEDULED.value,
                "scheduledAt": {"$lte": now.isoformat()}
            }).to_list(100)
            
            for campaign in scheduled_campaigns:
                logger.info(f"Processing scheduled campaign: {campaign['id']}")
                
                user = await db.users.find_one({"id": campaign['userId']})
                if not user or not user.get('bizChatToken') or not user.get('bizChatVendorUID'):
                    logger.error(f"User {campaign['userId']} missing BizChat credentials")
                    await db.campaigns.update_one(
                        {"id": campaign['id']},
                        {"$set": {"status": CampaignStatus.COMPLETED.value, "completedAt": now.isoformat()}}
                    )
                    continue
                
                await db.campaigns.update_one(
                    {"id": campaign['id']},
                    {"$set": {"status": CampaignStatus.PROCESSING.value}}
                )
                
                asyncio.create_task(
                    process_campaign(
                        campaign['id'],
                        user['bizChatToken'],
                        user['bizChatVendorUID']
                    )
                )
            
        except Exception as e:
            logger.error(f"Error in check_scheduled_campaigns: {str(e)}")
        
        await asyncio.sleep(60)


@app.on_event("startup")
async def startup_event():
    """Initialize app on startup"""
    # Create default admin user if not exists
    admin = await db.users.find_one({"email": SUPER_ADMIN_EMAIL})
    if not admin:
        admin_user = User(
            email=SUPER_ADMIN_EMAIL,
            firstName="BizChat",
            lastName="Admin",
            role=Role.ADMIN
        )
        admin_dict = admin_user.model_dump()
        admin_dict['password'] = hash_password("admin123")
        admin_dict['createdAt'] = admin_dict['createdAt'].isoformat()
        admin_dict['updatedAt'] = admin_dict['updatedAt'].isoformat()
        await db.users.insert_one(admin_dict)
        logger.info(f"Default admin user created: {SUPER_ADMIN_EMAIL} / admin123")
    
    # Start scheduled campaigns checker
    asyncio.create_task(check_scheduled_campaigns())
    logger.info("Scheduled campaigns checker started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await close_db_connection()


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "2.0.0"}
