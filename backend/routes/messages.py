"""Message sending routes and services"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File
from datetime import datetime, timezone
from typing import Dict, Any
from pathlib import Path
import httpx
import asyncio
import logging
import uuid
import os
import io
import pandas as pd

from models.schemas import (
    SendMessageRequest, Campaign, RecipientInfo, 
    CampaignStatus, MessageStatus, Role
)
from utils.auth import get_current_user
from utils.database import db
from utils.helpers import normalize_phone_number

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/messages", tags=["Messages"])

# BizChat API configuration
BIZCHAT_API_BASE = os.environ.get('BIZCHAT_API_BASE', 'https://bizchatapi.in/api')

# === Self-healing campaign worker registry ===
# In-process set of campaign IDs currently being worked on by this python process.
# Prevents the watchdog / startup-recovery from spawning duplicate workers
# for a campaign that is already actively being processed.
ACTIVE_CAMPAIGNS: set = set()

# Upload directory
ROOT_DIR = Path(__file__).parent.parent
UPLOAD_DIR = ROOT_DIR / "uploads"


async def send_whatsapp_message(
    phone: str,
    template_name: str,
    token: str,
    vendor_uid: str,
    recipient_data: Dict[str, Any],
    http_client: httpx.AsyncClient = None
) -> Dict[str, Any]:
    """Send a WhatsApp message via BizChat API"""
    try:
        url = f"{BIZCHAT_API_BASE}/{vendor_uid}/contact/send-template-message?token={token}"
        
        logger.info(f"BizChat API URL: {BIZCHAT_API_BASE}/{vendor_uid}/contact/send-template-message")
        
        # Build payload according to BizChat API documentation
        payload = {
            "phone_number": phone.replace('+', '').replace('-', '').replace(' ', ''),
            "template_name": template_name,
            "template_language": recipient_data.get("template_language", "en_US")
        }
        
        # Add direct field_1 through field_5 parameters (only if they have values)
        recipient_name = recipient_data.get('name', '')
        
        for i in range(1, 6):
            field_key = f"field_{i}"
            if field_key in recipient_data and recipient_data[field_key]:
                value = str(recipient_data[field_key]).strip()
                if value:
                    # Replace {name} placeholder with actual name
                    if '{name}' in value and recipient_name:
                        value = value.replace('{name}', recipient_name)
                    payload[field_key] = value
        
        # Add media headers if present
        if recipient_data.get('header_image'):
            payload['header_image'] = recipient_data['header_image']
        if recipient_data.get('header_video'):
            payload['header_video'] = recipient_data['header_video']
        if recipient_data.get('header_document'):
            payload['header_document'] = recipient_data['header_document']
        if recipient_data.get('header_document_name'):
            payload['header_document_name'] = recipient_data['header_document_name']
        if recipient_data.get('header_field_1'):
            payload['header_field_1'] = recipient_data['header_field_1']
        
        # Add location if present
        if recipient_data.get('location_latitude'):
            payload['location_latitude'] = recipient_data['location_latitude']
        if recipient_data.get('location_longitude'):
            payload['location_longitude'] = recipient_data['location_longitude']
        if recipient_data.get('location_name'):
            payload['location_name'] = recipient_data['location_name']
        if recipient_data.get('location_address'):
            payload['location_address'] = recipient_data['location_address']
        
        logger.info(f"Sending to BizChat - Phone: {phone}, Template: {template_name}")
        
        # Only retry 429s inline. Timeouts/errors fail fast — retried after campaign ends.
        max_429_retries = 5
        for attempt in range(max_429_retries):
            try:
                if http_client:
                    response = await http_client.post(url, json=payload, timeout=30.0)
                else:
                    async with httpx.AsyncClient() as client:
                        response = await client.post(url, json=payload, timeout=30.0)
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    if data.get('result') == 'failed':
                        error_msg = data.get('message', 'Unknown error from BizChat')
                        logger.error(f"BizChat returned failure: {error_msg}")
                        return {"success": False, "error": error_msg}
                    return {"success": True, "data": data}
                elif response.status_code == 429:
                    wait_time = min((attempt + 1) * 3, 15)
                    logger.warning(f"429 for {phone}, waiting {wait_time}s (attempt {attempt + 1}/{max_429_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                elif response.status_code == 403:
                    # Hosting firewall/rate limit — mark as retryable, don't waste time retrying now
                    logger.warning(f"403 Forbidden for {phone} — server blocking")
                    return {"success": False, "error": "TIMEOUT_RETRY", "retryable": True}
                else:
                    error_msg = f"HTTP {response.status_code}"
                    logger.error(f"BizChat API Error [{response.status_code}] | Response: {response.text[:300]}")
                    return {"success": False, "error": error_msg}
            except Exception as e:
                error_type = type(e).__name__
                logger.warning(f"Message to {phone} failed: {error_type}")
                return {"success": False, "error": "TIMEOUT_RETRY", "retryable": True}
        
        return {"success": False, "error": "429_RETRY", "retryable": True}
    except Exception as e:
        error_msg = f"Exception sending message: {type(e).__name__}: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}


async def process_campaign(campaign_id: str, user_token: str, vendor_uid: str):
    """Process campaign with concurrent batch sending and connection pooling.
    
    Strategy: Send messages in small concurrent batches (10 at a time),
    collect results, update DB, then proceed to next batch.
    This avoids race conditions while being ~10x faster than sequential.
    
    Self-healing: writes a `lastHeartbeatAt` timestamp to the DB on every
    batch save. A watchdog in server.py detects campaigns whose heartbeat
    is stale (worker died/crashed/server restarted) and re-spawns this
    coroutine. Duplicate spawns in the same python process are prevented
    by the ACTIVE_CAMPAIGNS set.
    """
    # Guard: refuse to spawn a duplicate worker for the same campaign
    if campaign_id in ACTIVE_CAMPAIGNS:
        logger.info(f"Campaign {campaign_id}: worker already active in this process, skipping duplicate spawn")
        return
    ACTIVE_CAMPAIGNS.add(campaign_id)
    
    try:
        await _process_campaign_impl(campaign_id, user_token, vendor_uid)
    except Exception as e:
        logger.exception(f"Campaign {campaign_id} worker crashed: {e}")
        # Do NOT mark as failed — leave in PROCESSING so watchdog can resume.
        # Heartbeat will go stale and watchdog will pick it up.
    finally:
        ACTIVE_CAMPAIGNS.discard(campaign_id)


async def _process_campaign_impl(campaign_id: str, user_token: str, vendor_uid: str):
    from utils.daily_limit import check_and_reset_daily_usage, update_last_activity
    
    campaign = await db.campaigns.find_one({"id": campaign_id})
    if not campaign:
        return
    
    user = await db.users.find_one({"id": campaign['userId']})
    if not user:
        logger.error(f"User not found for campaign {campaign_id}")
        return
    
    user = await check_and_reset_daily_usage(campaign['userId'], user)
    
    daily_usage = user.get('dailyUsage', 0)
    daily_limit = user.get('dailyLimit', 1000)
    
    pending_recipients = [r for r in campaign['recipients'] if r['status'] == MessageStatus.PENDING.value]
    
    # dailyLimit = -1 means UNLIMITED — skip the cap check entirely
    if daily_limit == -1:
        remaining = len(pending_recipients) + 1  # any positive value bigger than needed
    else:
        remaining = daily_limit - daily_usage
    
    if daily_limit != -1 and len(pending_recipients) > remaining:
        next_reset = user.get('nextResetAt', 'in 24 hours')
        logger.warning(f"Campaign {campaign_id}: Need {len(pending_recipients)} but only {remaining} available")
        await db.campaigns.update_one(
            {"id": campaign_id},
            {
                "$set": {
                    "status": CampaignStatus.PAUSED.value,
                    "error": f"Daily limit reached. Need {len(pending_recipients)} messages but only {remaining} available. Will resume after {next_reset}",
                    "updatedAt": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        return
    
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {
            "status": CampaignStatus.PROCESSING.value,
            "lastHeartbeatAt": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    sent_count = campaign.get('sentCount', 0)
    failed_count = campaign.get('failedCount', 0)
    
    BATCH_SIZE = 5  # Conservative to avoid hosting firewall blocks
    PAUSE_CHECK_EVERY = 50
    
    pending_indices = [i for i, r in enumerate(campaign['recipients']) if r['status'] == MessageStatus.PENDING.value]
    
    # Connection pooling
    limits = httpx.Limits(max_connections=10, max_keepalive_connections=5, keepalive_expiry=60)
    transport = httpx.AsyncHTTPTransport(retries=3)
    
    messages_since_db_save = 0
    batch_delay = 1.0  # 1 second between batches to avoid firewall triggers
    consecutive_errors = 0
    
    async with httpx.AsyncClient(limits=limits, transport=transport, timeout=30.0) as http_client:
        for batch_start in range(0, len(pending_indices), BATCH_SIZE):
            # Check pause status before every batch
            current = await db.campaigns.find_one({"id": campaign_id}, {"status": 1})
            if current and current.get('status') == CampaignStatus.PAUSED.value:
                logger.info(f"Campaign {campaign_id} paused at {batch_start}/{len(pending_indices)}")
                # Save current progress before exiting
                await db.campaigns.update_one(
                    {"id": campaign_id},
                    {"$set": {
                        "recipients": campaign['recipients'],
                        "sentCount": sent_count,
                        "failedCount": failed_count,
                        "pendingCount": campaign['totalCount'] - sent_count - failed_count,
                        "lastHeartbeatAt": datetime.now(timezone.utc).isoformat(),
                        "updatedAt": datetime.now(timezone.utc).isoformat()
                    }}
                )
                return
            
            batch_indices = pending_indices[batch_start:batch_start + BATCH_SIZE]
            
            # Fire all requests in this batch concurrently
            tasks = []
            for idx in batch_indices:
                recipient = campaign['recipients'][idx]
                tasks.append(send_whatsapp_message(
                    recipient['phone'],
                    campaign['templateName'],
                    user_token,
                    vendor_uid,
                    recipient,
                    http_client=http_client
                ))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            batch_errors = 0
            for j, (idx, result) in enumerate(zip(batch_indices, results)):
                if isinstance(result, Exception):
                    failed_count += 1
                    batch_errors += 1
                    campaign['recipients'][idx]['status'] = MessageStatus.FAILED.value
                    campaign['recipients'][idx]['error'] = str(result)[:200]
                    logger.error(f"Message to {campaign['recipients'][idx]['phone']} raised exception: {result}")
                elif result.get('success'):
                    sent_count += 1
                    campaign['recipients'][idx]['status'] = MessageStatus.SENT.value
                    campaign['recipients'][idx]['sentAt'] = datetime.now(timezone.utc).isoformat()
                    campaign['recipients'][idx]['messageId'] = result.get('data', {}).get('message_id')
                else:
                    failed_count += 1
                    batch_errors += 1
                    campaign['recipients'][idx]['status'] = MessageStatus.FAILED.value
                    campaign['recipients'][idx]['error'] = result.get('error', 'Unknown error')[:200]
            
            # Smart back-off: if server/hosting is struggling, slow down temporarily
            if batch_errors > len(batch_indices) * 0.5:
                consecutive_errors += 1
                batch_delay = min(1.0 * consecutive_errors, 10)
                logger.warning(f"Campaign {campaign_id}: High error rate ({batch_errors}/{len(batch_indices)}), delay={batch_delay}s")
                
                # Circuit breaker: if 3+ consecutive full-fail batches, server likely blocked us
                # Wait 60s then try again
                if consecutive_errors >= 3:
                    logger.warning(f"Campaign {campaign_id}: Circuit breaker triggered — server blocking. Waiting 60s...")
                    await asyncio.sleep(60)
                    consecutive_errors = 1  # Reset but keep cautious delay
                    batch_delay = 2.0
            elif consecutive_errors > 0:
                consecutive_errors = max(consecutive_errors - 1, 0)
                batch_delay = max(0.2, batch_delay * 0.7)
            else:
                batch_delay = 0.2
            
            # Save to DB after EVERY batch — real-time progress + heartbeat
            await db.campaigns.update_one(
                {"id": campaign_id},
                {
                    "$set": {
                        "recipients": campaign['recipients'],
                        "sentCount": sent_count,
                        "failedCount": failed_count,
                        "pendingCount": campaign['totalCount'] - sent_count - failed_count,
                        "lastHeartbeatAt": datetime.now(timezone.utc).isoformat(),
                        "updatedAt": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            
            # Minimal delay between batches
            await asyncio.sleep(batch_delay)
    
    # === Auto-retry failed messages (timeouts + 429s) ===
    RETRY_BATCH = 5  # Smaller batches for retries
    MAX_RETRY_ROUNDS = 3
    for retry_round in range(MAX_RETRY_ROUNDS):
        retryable_indices = [
            i for i, r in enumerate(campaign['recipients'])
            if r.get('status') == MessageStatus.FAILED.value and r.get('error') in ['429_RETRY', 'TIMEOUT_RETRY']
        ]
        if not retryable_indices:
            break
        
        logger.info(f"Campaign {campaign_id}: Auto-retrying {len(retryable_indices)} failed messages (round {retry_round + 1}/{MAX_RETRY_ROUNDS})")
        
        # Wait before retry round — give the server time to recover
        await asyncio.sleep(10 * (retry_round + 1))
        
        async with httpx.AsyncClient(limits=limits, transport=transport, timeout=15.0) as http_client:
            for batch_start in range(0, len(retryable_indices), RETRY_BATCH):
                batch_indices = retryable_indices[batch_start:batch_start + RETRY_BATCH]
                tasks = []
                for idx in batch_indices:
                    recipient = campaign['recipients'][idx]
                    tasks.append(send_whatsapp_message(
                        recipient['phone'], campaign['templateName'],
                        user_token, vendor_uid, recipient, http_client=http_client
                    ))
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for idx, result in zip(batch_indices, results):
                    if isinstance(result, Exception):
                        campaign['recipients'][idx]['error'] = str(result)[:200]
                    elif result.get('success'):
                        campaign['recipients'][idx]['status'] = MessageStatus.SENT.value
                        campaign['recipients'][idx]['sentAt'] = datetime.now(timezone.utc).isoformat()
                        campaign['recipients'][idx]['messageId'] = result.get('data', {}).get('message_id')
                        campaign['recipients'][idx].pop('error', None)
                        sent_count += 1
                        failed_count -= 1
                    elif result.get('retryable'):
                        pass  # Still failing, will retry next round
                    else:
                        campaign['recipients'][idx]['error'] = result.get('error', 'Unknown')[:200]
                
                await asyncio.sleep(2.0)  # Slower pace for retries
        
        # Save progress after each retry round
        await db.campaigns.update_one(
            {"id": campaign_id},
            {"$set": {
                "recipients": campaign['recipients'],
                "sentCount": sent_count,
                "failedCount": failed_count,
                "pendingCount": campaign['totalCount'] - sent_count - failed_count,
                "lastHeartbeatAt": datetime.now(timezone.utc).isoformat(),
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }}
        )
    
    # Mark any remaining retryable as clean failure message
    for r in campaign['recipients']:
        if r.get('error') in ['429_RETRY', 'TIMEOUT_RETRY']:
            r['error'] = 'Server busy - retry manually'

    # Final update
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
    
    await update_last_activity(campaign['userId'], sent_count)
    logger.info(f"Campaign {campaign_id} completed: {sent_count} sent, {failed_count} failed")


@router.post("/send")
async def send_messages(
    request: SendMessageRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
):
    """Send a bulk message campaign"""
    # Get user's BizChat credentials
    user = await db.users.find_one({"id": current_user.userId})
    if not user or not user.get('bizChatToken'):
        raise HTTPException(status_code=400, detail="BizChat API token not configured")
    if not user.get('bizChatVendorUID'):
        raise HTTPException(status_code=400, detail="BizChat Vendor UID not configured")
    
    # Check daily limit ONLY for immediate campaigns, not scheduled ones
    # Scheduled campaigns will be checked when they actually run
    is_scheduled = request.scheduledAt is not None
    
    if not is_scheduled:
        from utils.daily_limit import check_and_reset_daily_usage
        
        # Check and reset daily usage if 24 hours have passed
        user = await check_and_reset_daily_usage(current_user.userId, user)
        
        daily_usage = user.get('dailyUsage', 0)
        daily_limit = user.get('dailyLimit', 1000)
        remaining = user.get('remaining', daily_limit - daily_usage)
        
        # dailyLimit = -1 means UNLIMITED — skip cap check
        if daily_limit != -1 and len(request.recipients) > remaining:
            next_reset = user.get('nextResetAt', 'in 24 hours')
            raise HTTPException(
                status_code=400,
                detail=f"Cannot send campaign. You need {len(request.recipients)} messages but only {remaining} available. Limit resets at {next_reset}"
            )
    
    # Prepare recipients
    recipients = []
    for recipient in request.recipients:
        phone = normalize_phone_number(recipient['phone'], request.countryCode)
        recipient_info = RecipientInfo(
            phone=phone,
            name=recipient.get('name', ''),
            status=MessageStatus.PENDING
        )
        
        recipient_dict = recipient_info.model_dump()
        for key, value in recipient.items():
            if key not in ['phone', 'name']:
                recipient_dict[key] = value
        
        # Add campaign-level media and location fields
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
    
    campaign_dict['recipients'] = recipients
    
    await db.campaigns.insert_one(campaign_dict)
    
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


@router.post("/upload")
async def upload_recipients(file: UploadFile = File(...)):
    """Upload recipients from Excel or CSV file"""
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="Only Excel or CSV files are supported")
    
    try:
        contents = await file.read()
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
        
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


@router.post("/campaigns/{campaign_id}/retry-failed")
async def retry_failed_messages(
    campaign_id: str,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user)
):
    """Reset failed messages to pending and re-process the campaign"""
    campaign = await db.campaigns.find_one({"id": campaign_id, "userId": current_user.userId})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Don't allow retry while campaign is actively running
    if campaign.get('status') in [CampaignStatus.PROCESSING.value, CampaignStatus.PENDING.value]:
        raise HTTPException(status_code=400, detail="Campaign is still running. Pause it first before retrying failed messages.")

    user = await db.users.find_one({"id": current_user.userId})
    if not user or not user.get('bizChatToken') or not user.get('bizChatVendorUID'):
        raise HTTPException(status_code=400, detail="BizChat credentials not configured")

    # Count and reset failed recipients
    failed_count = 0
    for i, r in enumerate(campaign['recipients']):
        if r.get('status') == MessageStatus.FAILED.value:
            campaign['recipients'][i]['status'] = MessageStatus.PENDING.value
            campaign['recipients'][i].pop('error', None)
            failed_count += 1

    if failed_count == 0:
        raise HTTPException(status_code=400, detail="No failed messages to retry")

    # Update campaign in DB
    await db.campaigns.update_one(
        {"id": campaign_id},
        {
            "$set": {
                "recipients": campaign['recipients'],
                "failedCount": 0,
                "pendingCount": failed_count,
                "status": CampaignStatus.PROCESSING.value,
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }
        }
    )

    # Re-process
    background_tasks.add_task(
        process_campaign,
        campaign_id,
        user['bizChatToken'],
        user['bizChatVendorUID']
    )

    return {
        "message": f"Retrying {failed_count} failed messages",
        "retryCount": failed_count
    }
