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
from datetime import datetime, timezone, timedelta

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
from routes.webhook import router as webhook_router
from routes.contacts import router as contacts_router
from routes.indiamart import router as indiamart_router
from routes.chatbot import router as chatbot_router
from routes.bizchat_templates import router as bizchat_templates_router

# Import utilities
from utils.database import db, close_db_connection
from utils.auth import hash_password, SUPER_ADMIN_EMAIL
from models.schemas import User, Role, CampaignStatus
from services.reminder_service import process_due_reminders
from services.auto_message_service import process_auto_messages
from services.indiamart_service import start_indiamart_scheduler
from services.chatbot_service import start_chatbot_scheduler

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
app.include_router(webhook_router, prefix="/api")
app.include_router(contacts_router, prefix="/api")
app.include_router(indiamart_router, prefix="/api")
app.include_router(chatbot_router, prefix="/api")
app.include_router(bizchat_templates_router, prefix="/api")

# Mount static files for uploads
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/api/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="api_uploads")


# Campaign resume endpoint (needs access to process_campaign from messages)
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from utils.auth import get_current_user

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
        {"$set": {
            "status": CampaignStatus.PROCESSING.value,
            "lastHeartbeatAt": datetime.now(timezone.utc).isoformat()
        }}
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
                    {"$set": {
                        "status": CampaignStatus.PROCESSING.value,
                        "lastHeartbeatAt": now.isoformat()
                    }}
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


# Watchdog config
STUCK_CAMPAIGN_THRESHOLD_SECONDS = 90   # heartbeat older than this = worker dead
WATCHDOG_INTERVAL_SECONDS = 30          # how often the watchdog scans


async def _resume_stuck_campaign(campaign: dict, reason: str) -> bool:
    """Safely re-spawn a process_campaign worker for a stuck campaign.
    
    Skips if a worker is already active for this campaign in this process.
    Returns True if a new worker was spawned.
    """
    # Import here to avoid circular import at module load time
    from routes.messages import ACTIVE_CAMPAIGNS
    
    campaign_id = campaign['id']
    
    if campaign_id in ACTIVE_CAMPAIGNS:
        # A worker is actively running in this process — heartbeat will catch up shortly
        return False
    
    user = await db.users.find_one({"id": campaign['userId']})
    if not user or not user.get('bizChatToken') or not user.get('bizChatVendorUID'):
        logger.error(f"Watchdog: campaign {campaign_id} user missing BizChat credentials, pausing")
        await db.campaigns.update_one(
            {"id": campaign_id},
            {"$set": {
                "status": CampaignStatus.PAUSED.value,
                "error": "BizChat credentials missing - please configure and resume",
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }}
        )
        return False
    
    logger.warning(f"Watchdog: resuming stuck campaign {campaign_id} ({reason})")
    # Refresh heartbeat immediately so other ticks don't also try to claim it
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {"lastHeartbeatAt": datetime.now(timezone.utc).isoformat()}}
    )
    asyncio.create_task(
        process_campaign(
            campaign_id,
            user['bizChatToken'],
            user['bizChatVendorUID']
        )
    )
    return True


async def watchdog_stuck_campaigns():
    """Self-healing watchdog.
    
    Scans for campaigns that are stuck in PROCESSING status but whose worker
    has died (heartbeat stale or missing). Re-spawns the worker. The worker
    resumes from sentCount / already-sent recipients, so no duplicates are sent.
    """
    # Small grace period after boot so app has time to fully initialize
    await asyncio.sleep(5)
    
    while True:
        try:
            now = datetime.now(timezone.utc)
            stale_threshold_iso = (now - timedelta(seconds=STUCK_CAMPAIGN_THRESHOLD_SECONDS)).isoformat()
            
            # Find campaigns stuck in PROCESSING with stale or missing heartbeat
            stuck = await db.campaigns.find({
                "status": CampaignStatus.PROCESSING.value,
                "$or": [
                    {"lastHeartbeatAt": {"$lt": stale_threshold_iso}},
                    {"lastHeartbeatAt": {"$exists": False}},
                    {"lastHeartbeatAt": None},
                ]
            }).to_list(100)
            
            for campaign in stuck:
                hb = campaign.get('lastHeartbeatAt', 'never')
                await _resume_stuck_campaign(campaign, reason=f"stale heartbeat ({hb})")
            
        except Exception as e:
            logger.error(f"Error in watchdog_stuck_campaigns: {str(e)}")
        
        await asyncio.sleep(WATCHDOG_INTERVAL_SECONDS)


async def startup_resume_processing_campaigns():
    """One-shot startup routine.
    
    Immediately after boot, find every campaign left in PROCESSING status
    (from a crashed/restarted previous process) and re-spawn its worker.
    The worker is idempotent — it skips already-sent recipients.
    """
    try:
        # Give the app a couple of seconds to finish starting
        await asyncio.sleep(2)
        
        processing = await db.campaigns.find({
            "status": CampaignStatus.PROCESSING.value
        }).to_list(500)
        
        if not processing:
            logger.info("Startup recovery: no PROCESSING campaigns to resume")
            return
        
        logger.info(f"Startup recovery: found {len(processing)} campaign(s) in PROCESSING, resuming...")
        for campaign in processing:
            await _resume_stuck_campaign(campaign, reason="server restart recovery")
    except Exception as e:
        logger.error(f"Error in startup_resume_processing_campaigns: {str(e)}")


async def check_due_reminders():
    """Background task to check and send due reminders"""
    while True:
        try:
            await process_due_reminders()
        except Exception as e:
            logger.error(f"Error in check_due_reminders: {str(e)}")
        
        # Check every 30 seconds for more responsive reminders
        await asyncio.sleep(30)


async def check_auto_messages():
    """Background task to check and send birthday/anniversary wishes"""
    while True:
        try:
            await process_auto_messages()
        except Exception as e:
            logger.error(f"Error in check_auto_messages: {str(e)}")
        
        # Check every minute
        await asyncio.sleep(60)


@app.on_event("startup")
async def startup_event():
    """Initialize app on startup"""
    # === Ensure performance indexes exist ===
    # `create_index` is idempotent — safe to run on every startup.
    # Without these, queries do full collection scans (slow as data grows).
    try:
        await db.campaigns.create_index([("userId", 1), ("createdAt", -1)], background=True)
        await db.campaigns.create_index("id", unique=True, background=True)
        await db.campaigns.create_index("recipients.messageId", background=True, sparse=True)
        await db.campaigns.create_index([("status", 1), ("scheduledAt", 1)], background=True)
        await db.campaigns.create_index([("status", 1), ("lastHeartbeatAt", 1)], background=True)
        await db.users.create_index("id", unique=True, background=True)
        await db.users.create_index("email", unique=True, background=True)
        await db.reminders.create_index([("userId", 1), ("createdAt", -1)], background=True)
        await db.reminders.create_index([("status", 1), ("nextScheduledAt", 1)], background=True)
        await db.reminder_numbers.create_index("phoneNumber", background=True)
        await db.reminder_numbers.create_index("userId", background=True)
        await db.contacts.create_index([("userId", 1), ("phone", 1)], background=True)
        await db.contacts.create_index([("userId", 1), ("createdAt", -1)], background=True)
        await db.chatbot_conversations.create_index([("userId", 1), ("phone", 1)], background=True)
        await db.chatbot_leads.create_index([("userId", 1), ("createdAt", -1)], background=True)
        await db.saved_templates.create_index("userId", background=True)
        logger.info("Performance indexes ensured on all collections")
    except Exception as e:
        # Index creation failures shouldn't crash startup — they may already exist
        # with different specs, or the DB user lacks createIndex permission.
        logger.warning(f"Index creation warning (non-fatal): {e}")
    
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
    
    # Start self-healing watchdog for stuck PROCESSING campaigns
    asyncio.create_task(watchdog_stuck_campaigns())
    logger.info("Stuck-campaign watchdog started")
    
    # One-shot: resume campaigns that were left in PROCESSING by a previous process
    asyncio.create_task(startup_resume_processing_campaigns())
    logger.info("Startup campaign recovery scheduled")
    
    # Start reminders checker
    asyncio.create_task(check_due_reminders())
    logger.info("Reminders checker started")
    
    # Start auto-messages checker (birthdays/anniversaries)
    asyncio.create_task(check_auto_messages())
    logger.info("Auto-messages checker started")
    
    # Start Indiamart lead message scheduler
    asyncio.create_task(start_indiamart_scheduler())
    logger.info("Indiamart lead scheduler started")
    
    # Start chatbot follow-up scheduler
    asyncio.create_task(start_chatbot_scheduler())
    logger.info("Chatbot follow-up scheduler started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await close_db_connection()


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "2.2.0", "features": ["bulk_messaging", "reminder_bot", "contacts", "auto_wishes"]}
