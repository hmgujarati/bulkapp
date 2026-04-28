"""Indiamart routes - webhook and lead management"""
from fastapi import APIRouter, HTTPException, Depends, Request, Query, BackgroundTasks
from datetime import datetime, timezone, timedelta
from typing import Optional
import logging
import asyncio
import os

from utils.database import db
from utils.auth import get_current_user
from models.indiamart_schemas import (
    IndiamartLead, IndiamartSettings, IndiamartSettingsUpdate, 
    LeadUpdate, LeadStatus
)
from services.indiamart_service import process_new_lead

router = APIRouter(prefix="/indiamart", tags=["indiamart"])
logger = logging.getLogger(__name__)


# ============= WEBHOOK ENDPOINT =============

@router.post("/webhook/{user_id}")
async def indiamart_webhook(
    user_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    secret: Optional[str] = Query(None)
):
    """
    Webhook endpoint for Indiamart Push API
    URL format: /api/indiamart/webhook/{user_id}?secret={webhook_secret}
    """
    try:
        # Verify user exists and has Indiamart enabled
        user = await db.users.find_one({"id": user_id})
        if not user:
            logger.warning(f"Indiamart webhook: User {user_id} not found")
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check feature access
        features = user.get('features', {})
        if not features.get('indiamart', False):
            logger.warning(f"Indiamart webhook: Feature not enabled for user {user_id}")
            raise HTTPException(status_code=403, detail="Indiamart feature not enabled")
        
        # Get user's Indiamart settings
        settings = await db.indiamart_settings.find_one({"userId": user_id})
        if not settings or not settings.get('isActive'):
            logger.warning(f"Indiamart webhook: Integration not active for user {user_id}")
            raise HTTPException(status_code=403, detail="Indiamart integration not active")
        
        # Verify webhook secret
        if secret != settings.get('webhookSecret'):
            logger.warning(f"Indiamart webhook: Invalid secret for user {user_id}")
            raise HTTPException(status_code=401, detail="Invalid webhook secret")
        
        # Parse the lead data
        data = await request.json()
        logger.info(f"Indiamart webhook received for user {user_id}: {data}")
        
        # Check for duplicate lead
        unique_query_id = data.get('UNIQUE_QUERY_ID', '')
        existing_lead = await db.indiamart_leads.find_one({
            "userId": user_id,
            "uniqueQueryId": unique_query_id
        })
        
        if existing_lead:
            logger.info(f"Duplicate lead detected: {unique_query_id}")
            return {"status": "success", "message": "Lead already exists", "lead_id": existing_lead['id']}
        
        # Create new lead
        lead = IndiamartLead(
            userId=user_id,
            uniqueQueryId=unique_query_id,
            queryType=data.get('QUERY_TYPE', ''),
            queryTime=data.get('QUERY_TIME', ''),
            senderName=data.get('SENDER_NAME', ''),
            senderMobile=data.get('SENDER_MOBILE', ''),
            senderEmail=data.get('SENDER_EMAIL'),
            senderCompany=data.get('SENDER_COMPANY'),
            senderAddress=data.get('SENDER_ADDRESS'),
            senderCity=data.get('SENDER_CITY'),
            senderState=data.get('SENDER_STATE'),
            senderPincode=data.get('SENDER_PINCODE'),
            senderCountry=data.get('SENDER_COUNTRY_ISO', 'IN'),
            subject=data.get('SUBJECT'),
            productName=data.get('QUERY_PRODUCT_NAME'),
            queryMessage=data.get('QUERY_MESSAGE'),
            categoryName=data.get('CATEGORY_NAME')
        )
        
        # Save lead to database
        await db.indiamart_leads.insert_one(lead.model_dump())
        logger.info(f"New Indiamart lead created: {lead.id}")
        
        # Schedule auto-reply with configured delay
        send_delay = settings.get('sendDelay', 0)
        if settings.get('autoReplyEnabled') and settings.get('templateName'):
            if send_delay > 0:
                # Schedule for later
                scheduled_time = datetime.now(timezone.utc) + timedelta(minutes=send_delay)
                await db.indiamart_leads.update_one(
                    {"id": lead.id},
                    {"$set": {"nextMessageAt": scheduled_time.isoformat()}}
                )
                logger.info(f"Lead {lead.id} scheduled for message at {scheduled_time}")
            else:
                # Send immediately in background
                background_tasks.add_task(process_new_lead, lead.id)
                logger.info(f"Lead {lead.id} queued for immediate message")
        
        return {"status": "success", "message": "Lead received", "lead_id": lead.id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Indiamart webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhook/{user_id}")
async def verify_indiamart_webhook(user_id: str, secret: Optional[str] = Query(None)):
    """Verification endpoint for Indiamart webhook setup"""
    settings = await db.indiamart_settings.find_one({"userId": user_id})
    if settings and secret == settings.get('webhookSecret'):
        return {"status": "success", "message": "Webhook verified"}
    raise HTTPException(status_code=401, detail="Invalid webhook secret")


# ============= SETTINGS ENDPOINTS =============

@router.get("/settings")
async def get_indiamart_settings(current_user = Depends(get_current_user)):
    """Get user's Indiamart integration settings"""
    settings = await db.indiamart_settings.find_one(
        {"userId": current_user.userId},
        {"_id": 0}
    )
    
    if not settings:
        # Create default settings
        default_settings = IndiamartSettings(userId=current_user.userId)
        await db.indiamart_settings.insert_one(default_settings.model_dump())
        settings = default_settings.model_dump()
    
    # Build webhook URL - use environment variable for base URL
    base_url = os.environ.get('APP_BASE_URL', 'https://whatsapp-qa-flow.preview.emergentagent.com')
    webhook_url = f"{base_url}/api/indiamart/webhook/{current_user.userId}?secret={settings['webhookSecret']}"
    
    return {
        "settings": settings,
        "webhookUrl": webhook_url
    }


@router.put("/settings")
async def update_indiamart_settings(
    update_data: IndiamartSettingsUpdate,
    current_user = Depends(get_current_user)
):
    """Update user's Indiamart integration settings"""
    settings = await db.indiamart_settings.find_one({"userId": current_user.userId})
    
    if not settings:
        # Create new settings
        default_settings = IndiamartSettings(userId=current_user.userId)
        await db.indiamart_settings.insert_one(default_settings.model_dump())
        settings = default_settings.model_dump()
    
    # Update fields
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    update_dict["updatedAt"] = datetime.now(timezone.utc).isoformat()
    
    await db.indiamart_settings.update_one(
        {"userId": current_user.userId},
        {"$set": update_dict}
    )
    
    return {"message": "Settings updated successfully"}


@router.post("/settings/regenerate-secret")
async def regenerate_webhook_secret(current_user = Depends(get_current_user)):
    """Regenerate the webhook secret"""
    import uuid
    new_secret = str(uuid.uuid4())[:16]
    
    await db.indiamart_settings.update_one(
        {"userId": current_user.userId},
        {"$set": {"webhookSecret": new_secret, "updatedAt": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )
    
    return {"message": "Webhook secret regenerated", "newSecret": new_secret}


# ============= LEADS ENDPOINTS =============

@router.get("/leads")
async def get_leads(
    current_user = Depends(get_current_user),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """Get user's Indiamart leads"""
    query = {"userId": current_user.userId}
    
    if status:
        query["status"] = status
    
    skip = (page - 1) * limit
    
    leads = await db.indiamart_leads.find(
        query,
        {"_id": 0}
    ).sort("createdAt", -1).skip(skip).limit(limit).to_list(length=limit)
    
    total = await db.indiamart_leads.count_documents(query)
    
    # Get stats
    stats = {
        "total": total,
        "new": await db.indiamart_leads.count_documents({**query, "status": "new"}),
        "messageSent": await db.indiamart_leads.count_documents({**query, "status": "message_sent"}),
        "messageFailed": await db.indiamart_leads.count_documents({**query, "status": "message_failed"}),
        "converted": await db.indiamart_leads.count_documents({**query, "status": "converted"}),
    }
    
    return {
        "leads": leads,
        "total": total,
        "page": page,
        "totalPages": (total + limit - 1) // limit,
        "stats": stats
    }


@router.get("/leads/{lead_id}")
async def get_lead(lead_id: str, current_user = Depends(get_current_user)):
    """Get a specific lead"""
    lead = await db.indiamart_leads.find_one(
        {"id": lead_id, "userId": current_user.userId},
        {"_id": 0}
    )
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return lead


@router.put("/leads/{lead_id}")
async def update_lead(
    lead_id: str,
    update_data: LeadUpdate,
    current_user = Depends(get_current_user)
):
    """Update a lead (status, notes, follow-up date)"""
    lead = await db.indiamart_leads.find_one({"id": lead_id, "userId": current_user.userId})
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    update_dict["updatedAt"] = datetime.now(timezone.utc).isoformat()
    
    await db.indiamart_leads.update_one(
        {"id": lead_id},
        {"$set": update_dict}
    )
    
    return {"message": "Lead updated successfully"}


@router.post("/leads/{lead_id}/resend")
async def resend_lead_message(
    lead_id: str,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
):
    """Manually resend message to a lead"""
    lead = await db.indiamart_leads.find_one({"id": lead_id, "userId": current_user.userId})
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Queue for processing
    background_tasks.add_task(process_new_lead, lead_id)
    
    return {"message": "Message queued for sending"}


@router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str, current_user = Depends(get_current_user)):
    """Delete a lead"""
    result = await db.indiamart_leads.delete_one({
        "id": lead_id,
        "userId": current_user.userId
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return {"message": "Lead deleted successfully"}
