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
        
        # Use shared client if provided, otherwise create one
        max_retries = 8  # More retries for 429
        for attempt in range(max_retries):
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
                    # Rate limited — always retry with increasing backoff
                    wait_time = min((attempt + 1) * 3, 30)
                    logger.warning(f"429 for {phone}, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    error_msg = f"HTTP {response.status_code}"
                    logger.error(f"BizChat API Error [{response.status_code}] URL: {BIZCHAT_API_BASE}/{vendor_uid}/contact/send-template-message | Response: {response.text[:300]}")
                    return {"success": False, "error": error_msg}
            except Exception as e:
                error_str = str(e)
                error_type = type(e).__name__
                # Retry on any connection/network related exception
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    logger.warning(f"Retrying message to {phone} after {error_type}: {error_str[:150]} (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                logger.error(f"Failed to send to {phone} after {max_retries} attempts. Last error: {error_type}: {error_str[:200]}")
                return {"success": False, "error": f"{error_type}: {error_str[:150]}" if error_str else error_type}
        
        # If we exhausted all retries (only happens for persistent 429s)
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
    """
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
    remaining = daily_limit - daily_usage
    
    if len(pending_recipients) > remaining:
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
        {"$set": {"status": CampaignStatus.PROCESSING.value}}
    )
    
    sent_count = campaign.get('sentCount', 0)
    failed_count = campaign.get('failedCount', 0)
    
    BATCH_SIZE = 10  # 10 concurrent — safe for 2-core shared hosting
    DB_SAVE_EVERY = 100  # Save to DB every 100 messages
    PAUSE_CHECK_EVERY = 200  # Check pause status every 200 messages
    
    pending_indices = [i for i, r in enumerate(campaign['recipients']) if r['status'] == MessageStatus.PENDING.value]
    
    # Connection pooling tuned for shared hosting (2 core, 3GB)
    limits = httpx.Limits(max_connections=15, max_keepalive_connections=10, keepalive_expiry=60)
    transport = httpx.AsyncHTTPTransport(retries=3)
    
    messages_since_db_save = 0
    batch_delay = 0.3  # Base delay between batches
    consecutive_errors = 0  # Track consecutive batch errors to back off if server is struggling
    
    async with httpx.AsyncClient(limits=limits, transport=transport, timeout=30.0) as http_client:
        for batch_start in range(0, len(pending_indices), BATCH_SIZE):
            # Pause check
            if batch_start > 0 and batch_start % PAUSE_CHECK_EVERY == 0:
                current = await db.campaigns.find_one({"id": campaign_id}, {"status": 1})
                if current and current.get('status') == CampaignStatus.PAUSED.value:
                    logger.info(f"Campaign {campaign_id} paused at {batch_start}/{len(pending_indices)}")
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
            elif consecutive_errors > 0:
                consecutive_errors = max(consecutive_errors - 1, 0)
                batch_delay = max(0.3, batch_delay * 0.7)
            else:
                batch_delay = 0.3
            
            messages_since_db_save += len(batch_indices)
            
            # Save to DB periodically
            if messages_since_db_save >= DB_SAVE_EVERY or (batch_start + BATCH_SIZE) >= len(pending_indices):
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
                messages_since_db_save = 0
            
            # Minimal delay between batches
            await asyncio.sleep(batch_delay)
    
    # === Auto-retry 429 failures ===
    # Check for any recipients that failed with 429_RETRY and re-attempt them
    MAX_429_ROUNDS = 3
    for retry_round in range(MAX_429_ROUNDS):
        retryable_indices = [
            i for i, r in enumerate(campaign['recipients'])
            if r.get('status') == MessageStatus.FAILED.value and r.get('error') == '429_RETRY'
        ]
        if not retryable_indices:
            break
        
        logger.info(f"Campaign {campaign_id}: Auto-retrying {len(retryable_indices)} rate-limited messages (round {retry_round + 1})")
        
        # Wait before retry round — give the server time to recover
        await asyncio.sleep(10 * (retry_round + 1))
        
        async with httpx.AsyncClient(limits=limits, transport=transport, timeout=30.0) as http_client:
            for batch_start in range(0, len(retryable_indices), BATCH_SIZE):
                batch_indices = retryable_indices[batch_start:batch_start + BATCH_SIZE]
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
                        pass  # Still 429, will retry next round
                    else:
                        campaign['recipients'][idx]['error'] = result.get('error', 'Unknown')[:200]
                
                await asyncio.sleep(1.0)  # Slower pace for retries
        
        # Save progress after each retry round
        await db.campaigns.update_one(
            {"id": campaign_id},
            {"$set": {
                "recipients": campaign['recipients'],
                "sentCount": sent_count,
                "failedCount": failed_count,
                "pendingCount": campaign['totalCount'] - sent_count - failed_count,
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }}
        )
    
    # Mark any remaining 429_RETRY as permanent failure with clean message
    for r in campaign['recipients']:
        if r.get('error') == '429_RETRY':
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
        
        if len(request.recipients) > remaining:
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
