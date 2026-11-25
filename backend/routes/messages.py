"""Message sending routes and services"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from pathlib import Path
import httpx
import asyncio
import logging
import uuid
import os
import re
import io
import pandas as pd

from models.schemas import (
    SendMessageRequest, RecipientChunkRequest, Campaign, RecipientInfo, 
    CampaignStatus, MessageStatus, Role
)
from utils.auth import get_current_user
from utils.database import db
from utils.helpers import normalize_phone_number
from services.message_status_service import apply_pending_statuses

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/messages", tags=["Messages"])

# BizChat API configuration
BIZCHAT_API_BASE = os.environ.get('BIZCHAT_API_BASE', 'https://bizchatapi.in/api')

# Global throttle shared by ALL campaigns and users — BizChat's shared hosting
# returns HTTP 500 (DB connection refused) above ~5 parallel requests.
BIZCHAT_MAX_CONCURRENT = int(os.environ.get('BIZCHAT_MAX_CONCURRENT', 5))
BIZCHAT_BATCH_PAUSE = float(os.environ.get('BIZCHAT_BATCH_PAUSE', 0.5))
BIZCHAT_SEMAPHORE = asyncio.Semaphore(BIZCHAT_MAX_CONCURRENT)
_inflight = 0
_inflight_peak = 0
_http_client: httpx.AsyncClient = None
_success_response_logged = False

MAX_TEMPLATE_FIELDS = 15

# Optional recipient fields forwarded to BizChat as-is
PASSTHROUGH_FIELDS = (
    'header_image', 'header_video', 'header_document', 'header_document_name', 'header_field_1',
    'location_latitude', 'location_longitude', 'location_name', 'location_address',
    'buttons', 'components',
)
# Internal tracking fields that must never be sent to BizChat
INTERNAL_RECIPIENT_FIELDS = {
    'status', 'sentAt', 'messageId', 'error', 'retryCount', 'phone', 'name', 'template_language',
}

# === Self-healing campaign worker registry ===
# In-process set of campaign IDs currently being worked on by this python process.
# Prevents the watchdog / startup-recovery from spawning duplicate workers
# for a campaign that is already actively being processed.
ACTIVE_CAMPAIGNS: set = set()

# Upload directory
ROOT_DIR = Path(__file__).parent.parent
UPLOAD_DIR = ROOT_DIR / "uploads"


def get_http_client() -> httpx.AsyncClient:
    """One shared keep-alive client for every BizChat request."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(
                max_connections=BIZCHAT_MAX_CONCURRENT * 2,
                max_keepalive_connections=BIZCHAT_MAX_CONCURRENT,
                keepalive_expiry=60,
            ),
        )
    return _http_client


async def close_http_client():
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
    _http_client = None


def _extract_message_id(data) -> str:
    """Find the wamid wherever BizChat nests it."""
    if not isinstance(data, dict):
        return None
    keys = ('wamid', 'message_id', 'messageId')
    for container in (data, data.get('data')):
        if not isinstance(container, dict):
            continue
        for k in keys:
            if container.get(k):
                return str(container[k])
        messages = container.get('messages')
        if isinstance(messages, list) and messages and isinstance(messages[0], dict) and messages[0].get('id'):
            return str(messages[0]['id'])
    return None


def _document_name_for_contact(contact_name: str, original_name: str, document_url: str):
    """'Ravi Kumar' + 'price list.pdf' -> 'Ravi Kumar.pdf'. None when the contact has no name."""
    clean = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '', str(contact_name or ''))
    clean = re.sub(r'\s+', ' ', clean).strip(' .')[:80]
    if not clean:
        return None
    source = original_name or document_url.split('?')[0].rsplit('/', 1)[-1]
    ext = Path(source).suffix.lower()
    return f"{clean}{ext if 1 < len(ext) <= 6 else '.pdf'}"


def _build_payload(phone: str, template_name: str, recipient_data: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "phone_number": phone.replace('+', '').replace('-', '').replace(' ', ''),
        "template_name": template_name,
        "template_language": recipient_data.get("template_language", "en_US")
    }
    recipient_name = recipient_data.get('name', '')
    for i in range(1, MAX_TEMPLATE_FIELDS + 1):
        field_key = f"field_{i}"
        value = str(recipient_data.get(field_key) or '').strip()
        if value:
            if '{name}' in value and recipient_name:
                value = value.replace('{name}', recipient_name)
            payload[field_key] = value
    for key in PASSTHROUGH_FIELDS:
        if key not in INTERNAL_RECIPIENT_FIELDS and recipient_data.get(key):
            payload[key] = recipient_data[key]
    if recipient_data.get('document_name_from_contact') and payload.get('header_document'):
        contact_name = _document_name_for_contact(recipient_name, payload.get('header_document_name'), payload['header_document'])
        if contact_name:
            payload['header_document_name'] = contact_name
    return payload


async def send_whatsapp_message(
    phone: str,
    template_name: str,
    token: str,
    vendor_uid: str,
    recipient_data: Dict[str, Any],
    http_client: httpx.AsyncClient = None
) -> Dict[str, Any]:
    """Send one WhatsApp template via BizChat.

    Returns {success, retryable, error, message_id, data}.
    Retryable: 403, 429, 5xx, timeouts/connection errors. Permanent: result=failed/error, other 4xx.
    """
    global _inflight, _inflight_peak, _success_response_logged
    url = f"{BIZCHAT_API_BASE}/{vendor_uid}/contact/send-template-message?token={token}"
    payload = _build_payload(phone, template_name, recipient_data)
    client = http_client or get_http_client()

    async with BIZCHAT_SEMAPHORE:
        _inflight += 1
        _inflight_peak = max(_inflight_peak, _inflight)
        logger.info(f"BizChat send {phone} tpl={template_name} inflight={_inflight}/{BIZCHAT_MAX_CONCURRENT} peak={_inflight_peak}")
        try:
            response = await client.post(url, json=payload)
        except (httpx.TimeoutException, httpx.TransportError) as e:
            logger.warning(f"BizChat {type(e).__name__} for {phone}")
            return {"success": False, "retryable": True, "error": f"Network error: {type(e).__name__}", "message_id": None}
        except Exception as e:
            logger.error(f"BizChat unexpected error for {phone}: {type(e).__name__}: {e}")
            return {"success": False, "retryable": False, "error": f"{type(e).__name__}: {e}"[:200], "message_id": None}
        finally:
            _inflight -= 1

    status = response.status_code
    if status in (403, 429) or status >= 500:
        logger.warning(f"BizChat HTTP {status} for {phone} (retryable) | {response.text[:200]}")
        return {"success": False, "retryable": True, "error": f"HTTP {status}", "message_id": None}

    try:
        data = response.json()
    except ValueError:
        data = None

    if status not in (200, 201):
        msg = data.get('message') if isinstance(data, dict) and data.get('message') else response.text[:150]
        logger.error(f"BizChat HTTP {status} for {phone} (permanent) | {response.text[:300]}")
        return {"success": False, "retryable": False, "error": f"HTTP {status}: {msg}"[:200], "message_id": None}

    if isinstance(data, dict) and str(data.get('result', '')).lower() in ('failed', 'error'):
        error_msg = str(data.get('message') or 'Unknown error from BizChat')
        logger.error(f"BizChat returned failure for {phone} (permanent): {error_msg}")
        return {"success": False, "retryable": False, "error": error_msg[:200], "message_id": None}

    if not _success_response_logged:
        _success_response_logged = True
        logger.info(f"BizChat sample success response: {response.text[:2000]}")
    return {"success": True, "retryable": False, "error": None, "message_id": _extract_message_id(data), "data": data}


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


def _parse_iso(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _next_reset_at(user: dict) -> datetime:
    """When this user's daily quota frees up again."""
    return _parse_iso(user.get('nextResetAt')) or datetime.now(timezone.utc) + timedelta(hours=24)


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
    
    # === Drip campaigns: only send up to dripDailyLimit per 24h window ===
    drip_enabled = bool(campaign.get('dripEnabled')) and campaign.get('dripDailyLimit')
    send_cap = None
    drip_window_index = None
    drip_next_window_at = None
    
    if drip_enabled:
        anchor_str = campaign.get('dripStartAt') or campaign.get('createdAt')
        anchor = datetime.fromisoformat(str(anchor_str).replace('Z', '+00:00'))
        if anchor.tzinfo is None:
            anchor = anchor.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        
        if now < anchor:
            await db.campaigns.update_one(
                {"id": campaign_id},
                {"$set": {
                    "status": CampaignStatus.SCHEDULED.value,
                    "scheduledAt": anchor.isoformat(),
                    "updatedAt": now.isoformat()
                }}
            )
            logger.info(f"Campaign {campaign_id}: drip not started yet, scheduled for {anchor.isoformat()}")
            return
        
        drip_window_index = int((now - anchor).total_seconds() // 86400)
        drip_next_window_at = anchor + timedelta(days=drip_window_index + 1)
        sent_in_window = campaign.get('dripSentInWindow', 0) if campaign.get('dripWindowIndex') == drip_window_index else 0
        if campaign.get('dripWindowIndex') != drip_window_index:
            await db.campaigns.update_one(
                {"id": campaign_id},
                {"$set": {"dripWindowIndex": drip_window_index, "dripSentInWindow": 0}}
            )
        
        send_cap = int(campaign['dripDailyLimit']) - sent_in_window
        if daily_limit != -1:
            send_cap = min(send_cap, remaining)
        
        if send_cap <= 0:
            next_at = drip_next_window_at
            reset_at = user.get('nextResetAt')
            if daily_limit != -1 and remaining <= 0 and reset_at:
                try:
                    reset_dt = datetime.fromisoformat(reset_at.replace('Z', '+00:00'))
                    next_at = max(next_at, reset_dt)
                except (ValueError, TypeError):
                    pass
            await db.campaigns.update_one(
                {"id": campaign_id},
                {"$set": {
                    "status": CampaignStatus.SCHEDULED.value,
                    "scheduledAt": next_at.isoformat(),
                    "updatedAt": now.isoformat()
                }}
            )
            logger.info(f"Campaign {campaign_id}: daily drip quota used, next batch at {next_at.isoformat()}")
            return
    
    # Non-drip campaigns bigger than today's remaining quota: send what the quota
    # allows now and auto-resume after the limit resets (instead of pausing dead).
    if not drip_enabled and daily_limit != -1 and len(pending_recipients) > remaining:
        next_reset = _next_reset_at(user)
        if remaining <= 0:
            await db.campaigns.update_one(
                {"id": campaign_id},
                {"$set": {
                    "status": CampaignStatus.SCHEDULED.value,
                    "scheduledAt": next_reset.isoformat(),
                    "error": f"Daily limit reached — remaining messages resume automatically after {next_reset.isoformat()}",
                    "updatedAt": datetime.now(timezone.utc).isoformat()
                }}
            )
            logger.info(f"Campaign {campaign_id}: daily limit used up, resuming at {next_reset.isoformat()}")
            return
        send_cap = remaining
        logger.info(
            f"Campaign {campaign_id}: {len(pending_recipients)} pending but only {remaining} left today — "
            f"sending {remaining} now, rest resumes at {next_reset.isoformat()}"
        )
    
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {
            "status": CampaignStatus.PROCESSING.value,
            "lastHeartbeatAt": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    recipients = campaign['recipients']
    # Messages sent by THIS run only — daily usage is charged per run.
    run_sent_delta = 0
    retry_indices: set = set()
    
    pending_indices = [i for i, r in enumerate(recipients) if r['status'] == MessageStatus.PENDING.value]
    if send_cap is not None:
        pending_indices = pending_indices[:send_cap]
        logger.info(f"Campaign {campaign_id}: cap {send_cap}, sending up to {len(pending_indices)} messages")
    
    async def mark_sent(idx):
        """Set SENT only if the webhook hasn't already moved this recipient on; counts via $inc."""
        res = await db.campaigns.update_one(
            {"id": campaign_id, f"recipients.{idx}.status": {"$in": [MessageStatus.PENDING.value, MessageStatus.SENT.value]}},
            {"$set": {f"recipients.{idx}.status": MessageStatus.SENT.value},
             "$inc": {"sentCount": 1, "pendingCount": -1}}
        )
        if res.matched_count:
            return
        # Webhook got there first (delivered/read): keep its status, still count it as sent
        res = await db.campaigns.update_one(
            {"id": campaign_id, f"recipients.{idx}.status": {"$in": [MessageStatus.DELIVERED.value, MessageStatus.READ.value]}},
            {"$inc": {"sentCount": 1, "pendingCount": -1}}
        )
        if not res.matched_count:
            # Webhook reported failed (it already incremented failedCount)
            await db.campaigns.update_one({"id": campaign_id}, {"$inc": {"pendingCount": -1}})
    
    async def mark_failed(indices, error_for):
        if not indices:
            return
        set_ops = {}
        for idx in indices:
            recipients[idx]['status'] = MessageStatus.FAILED.value
            recipients[idx]['error'] = error_for(idx)
            set_ops[f"recipients.{idx}.status"] = MessageStatus.FAILED.value
            set_ops[f"recipients.{idx}.error"] = recipients[idx]['error']
        await db.campaigns.update_one(
            {"id": campaign_id},
            {"$set": set_ops, "$inc": {"failedCount": len(indices), "pendingCount": -len(indices)}}
        )
    
    async def send_batch(batch_indices) -> bool:
        """Send one batch and write results to MongoDB immediately. True if any error was retryable."""
        nonlocal run_sent_delta
        results = await asyncio.gather(*[
            send_whatsapp_message(recipients[idx]['phone'], campaign['templateName'], user_token, vendor_uid, recipients[idx])
            for idx in batch_indices
        ], return_exceptions=True)
        now_iso = datetime.now(timezone.utc).isoformat()
        set_ops = {"lastHeartbeatAt": now_iso, "updatedAt": now_iso}
        sent_idx, failed_errors, had_retryable = [], {}, False
        for idx, result in zip(batch_indices, results):
            if isinstance(result, Exception):
                result = {"success": False, "retryable": False, "error": str(result)[:200]}
            if result['success']:
                sent_idx.append(idx)
                retry_indices.discard(idx)
                recipients[idx].update(status=MessageStatus.SENT.value, sentAt=now_iso,
                                       messageId=result.get('message_id'), error=None)
                for f in ('sentAt', 'messageId', 'error'):
                    set_ops[f"recipients.{idx}.{f}"] = recipients[idx][f]
            elif result.get('retryable'):
                had_retryable = True
                retry_indices.add(idx)
                recipients[idx]['retryCount'] = int(recipients[idx].get('retryCount') or 0) + 1
                recipients[idx]['error'] = result.get('error')
                set_ops[f"recipients.{idx}.retryCount"] = recipients[idx]['retryCount']
                set_ops[f"recipients.{idx}.error"] = recipients[idx]['error']
            else:
                retry_indices.discard(idx)
                failed_errors[idx] = result.get('error') or 'Unknown error'
        
        # messageId first so delivered/read webhooks can find the recipient right away
        update_doc = {"$set": set_ops}
        if drip_enabled and sent_idx:
            update_doc["$inc"] = {"dripSentInWindow": len(sent_idx)}
        await db.campaigns.update_one({"id": campaign_id}, update_doc)
        await asyncio.gather(*[mark_sent(idx) for idx in sent_idx])
        await apply_pending_statuses(campaign['userId'], [recipients[i]['messageId'] for i in sent_idx if recipients[i]['messageId']])
        await mark_failed(list(failed_errors), failed_errors.get)
        run_sent_delta += len(sent_idx)
        return had_retryable
    
    async def run_indices(indices) -> bool:
        """Send indices in batches with backoff. Returns False if paused/cancelled."""
        processed = 0
        next_threshold = 25
        backoff_step = 0
        for batch_start in range(0, len(indices), BIZCHAT_MAX_CONCURRENT):
            batch = indices[batch_start:batch_start + BIZCHAT_MAX_CONCURRENT]
            had_retryable = await send_batch(batch)
            processed += len(batch)
            
            if processed >= next_threshold:
                while processed >= next_threshold:
                    next_threshold += 25
                logger.info(f"Campaign {campaign_id}: progress {processed}/{len(indices)}")
                current = await db.campaigns.find_one({"id": campaign_id}, {"status": 1})
                if current and current.get('status') in (CampaignStatus.PAUSED.value, CampaignStatus.CANCELLED.value):
                    logger.info(f"Campaign {campaign_id} {current.get('status')} at {processed}/{len(indices)}")
                    return False
            
            if had_retryable:
                backoff_step += 1
                delay = min(3 * backoff_step, 30)
                logger.warning(f"Campaign {campaign_id}: retryable errors in batch, backing off {delay}s")
            else:
                backoff_step = 0
                delay = BIZCHAT_BATCH_PAUSE
            await asyncio.sleep(delay)
        return True
    
    async def stop_paused():
        if run_sent_delta:
            await update_last_activity(campaign['userId'], run_sent_delta)
    
    if not await run_indices(pending_indices):
        return await stop_paused()
    
    # === Retry rounds for retryable failures (429 / 403 / 5xx / network) ===
    MAX_RETRY_ROUNDS = 3
    for retry_round in range(1, MAX_RETRY_ROUNDS + 1):
        if not retry_indices:
            break
        wait = 5 * retry_round
        logger.info(f"Campaign {campaign_id}: retry round {retry_round}/{MAX_RETRY_ROUNDS} for {len(retry_indices)} messages in {wait}s")
        await db.campaigns.update_one({"id": campaign_id}, {"$set": {"lastHeartbeatAt": datetime.now(timezone.utc).isoformat()}})
        await asyncio.sleep(wait)
        if not await run_indices(sorted(retry_indices)):
            return await stop_paused()
    
    # Anything still pending after all retry rounds is FAILED (so "retry failed" can resend it)
    await mark_failed(
        sorted(retry_indices),
        lambda idx: f"{recipients[idx].get('error') or 'Server busy'} — gave up after {MAX_RETRY_ROUNDS} retries"
    )
    retry_indices.clear()

    # Drip campaigns: if messages are still pending, park the campaign until the
    # next daily window instead of marking it complete.
    if drip_enabled:
        still_pending = any(r['status'] == MessageStatus.PENDING.value for r in campaign['recipients'])
        if still_pending:
            await db.campaigns.update_one(
                {"id": campaign_id},
                {"$set": {
                    "status": CampaignStatus.SCHEDULED.value,
                    "scheduledAt": drip_next_window_at.isoformat(),
                    "updatedAt": datetime.now(timezone.utc).isoformat()
                }}
            )
            await update_last_activity(campaign['userId'], run_sent_delta)
            logger.info(f"Campaign {campaign_id}: daily batch done ({run_sent_delta} sent), next batch at {drip_next_window_at.isoformat()}")
            return
    
    # Non-drip campaign that ran out of today's quota mid-way: park it and let the
    # scheduler pick it up once the daily limit resets.
    if not drip_enabled and send_cap is not None:
        still_pending = any(r['status'] == MessageStatus.PENDING.value for r in campaign['recipients'])
        if still_pending:
            fresh_user = await db.users.find_one({"id": campaign['userId']})
            next_reset = _next_reset_at(await check_and_reset_daily_usage(campaign['userId'], fresh_user))
            await db.campaigns.update_one(
                {"id": campaign_id},
                {"$set": {
                    "status": CampaignStatus.SCHEDULED.value,
                    "scheduledAt": next_reset.isoformat(),
                    "error": f"Daily limit reached — remaining messages resume automatically after {next_reset.isoformat()}",
                    "updatedAt": datetime.now(timezone.utc).isoformat()
                }}
            )
            await update_last_activity(campaign['userId'], run_sent_delta)
            logger.info(f"Campaign {campaign_id}: daily quota used ({run_sent_delta} sent), resuming at {next_reset.isoformat()}")
            return
    
    # Final update — only mark completion. Don't overwrite recipients/counts:
    # those have been maintained via per-index $set + $inc throughout, and
    # webhooks may have applied delivered/read/click updates we must preserve.
    await db.campaigns.update_one(
        {"id": campaign_id},
        {
            "$set": {
                "status": CampaignStatus.COMPLETED.value,
                "completedAt": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    await update_last_activity(campaign['userId'], run_sent_delta)
    final = await db.campaigns.find_one({"id": campaign_id}, {"sentCount": 1, "failedCount": 1})
    logger.info(f"Campaign {campaign_id} completed: {final.get('sentCount')} sent, {final.get('failedCount')} failed")
    
    await _start_next_in_chain(campaign)


async def _start_next_in_chain(campaign: dict):
    """Big lists run as several small campaigns — start the next queued part."""
    chain_id = campaign.get('chainId')
    sequence = campaign.get('chainSequence')
    if not chain_id or not sequence:
        return
    
    next_campaign = await db.campaigns.find_one(
        {
            "chainId": chain_id,
            "chainSequence": sequence + 1,
            "status": CampaignStatus.QUEUED.value
        },
        {"recipients": 0}
    )
    if not next_campaign:
        return
    
    user = await db.users.find_one({"id": campaign['userId']})
    if not user or not user.get('bizChatToken') or not user.get('bizChatVendorUID'):
        logger.error(f"Chain {chain_id}: cannot start part {sequence + 1}, BizChat credentials missing")
        return
    
    await db.campaigns.update_one(
        {"id": next_campaign['id']},
        {"$set": {
            "status": CampaignStatus.PROCESSING.value,
            "lastHeartbeatAt": datetime.now(timezone.utc).isoformat(),
            "updatedAt": datetime.now(timezone.utc).isoformat()
        }}
    )
    logger.info(f"Chain {chain_id}: starting part {sequence + 1} ({next_campaign['id']})")
    asyncio.create_task(
        process_campaign(next_campaign['id'], user['bizChatToken'], user['bizChatVendorUID'])
    )


def _send_defaults(request: SendMessageRequest) -> Dict[str, Any]:
    """Campaign-level fields copied onto every recipient at send time."""
    keys = [
        'header_image', 'header_video', 'header_document', 'header_document_name',
        'header_field_1', 'location_latitude', 'location_longitude',
        'location_name', 'location_address', 'document_name_from_contact'
    ]
    return {k: getattr(request, k) for k in keys if getattr(request, k)}


def build_recipient_docs(raw_recipients, country_code, defaults: Dict[str, Any]):
    """Normalize phones and attach per-campaign media/location fields."""
    docs = []
    for recipient in raw_recipients:
        phone = normalize_phone_number(recipient['phone'], country_code)
        doc = RecipientInfo(
            phone=phone,
            name=recipient.get('name', ''),
            status=MessageStatus.PENDING
        ).model_dump()
        for key, value in recipient.items():
            if key not in ['phone', 'name']:
                doc[key] = value
        doc.update(defaults)
        docs.append(doc)
    return docs


async def _validate_campaign_request(request: SendMessageRequest, user_id: str, total_count: int):
    """Shared validation for the single-shot and chunked create flows."""
    if not (request.campaignName or '').strip():
        raise HTTPException(status_code=400, detail="Campaign name is required")

    user = await db.users.find_one({"id": user_id})
    if not user or not user.get('bizChatToken'):
        raise HTTPException(status_code=400, detail="BizChat API token not configured")
    if not user.get('bizChatVendorUID'):
        raise HTTPException(status_code=400, detail="BizChat Vendor UID not configured")

    drip_enabled = bool(request.dripEnabled and request.dripDailyLimit)
    if request.dripEnabled and (not request.dripDailyLimit or request.dripDailyLimit < 1):
        raise HTTPException(status_code=400, detail="Please enter how many messages to send per day")
    if drip_enabled:
        account_limit = user.get('dailyLimit', 1000)
        if account_limit != -1 and request.dripDailyLimit > account_limit:
            raise HTTPException(
                status_code=400,
                detail=f"Messages per day ({request.dripDailyLimit}) cannot exceed your account daily limit ({account_limit}). Please lower it or contact admin."
            )

    is_scheduled = request.scheduledAt is not None
    daily_usage = user.get('dailyUsage', 0)
    daily_limit = user.get('dailyLimit', 1000)

    if not is_scheduled and not drip_enabled:
        from utils.daily_limit import check_and_reset_daily_usage
        user = await check_and_reset_daily_usage(user_id, user)
        daily_usage = user.get('dailyUsage', 0)
        daily_limit = user.get('dailyLimit', 1000)
        remaining = user.get('remaining', daily_limit - daily_usage)

        if daily_limit != -1 and total_count > remaining:
            next_reset = user.get('nextResetAt', 'in 24 hours')
            raise HTTPException(
                status_code=400,
                detail=f"Cannot send campaign. You need {total_count} messages but only {remaining} available. Limit resets at {next_reset}"
            )

    drip_start_at = None
    if drip_enabled:
        drip_start_at = request.dripStartAt or datetime.now(timezone.utc)
        if drip_start_at.tzinfo is None:
            drip_start_at = drip_start_at.replace(tzinfo=timezone.utc)
        drip_start_at = drip_start_at.isoformat()

    starts_later = bool(request.scheduledAt) or (
        drip_enabled and request.dripStartAt is not None and
        datetime.fromisoformat(drip_start_at) > datetime.now(timezone.utc)
    )

    return user, drip_enabled, drip_start_at, starts_later, daily_usage, daily_limit


@router.post("/campaigns/init")
async def init_campaign(
    request: SendMessageRequest,
    current_user = Depends(get_current_user)
):
    """Step 1 of the chunked flow: create an empty campaign (for large lists).

    Big lists (30k+) can't be posted in one request — proxies reject bodies over
    ~1MB — so recipients are appended in chunks and the campaign starts last.
    """
    expected = request.totalCount or 0
    if expected < 1:
        raise HTTPException(status_code=400, detail="totalCount is required")

    user, drip_enabled, drip_start_at, starts_later, _, _ = await _validate_campaign_request(
        request, current_user.userId, expected
    )

    campaign = Campaign(
        userId=current_user.userId,
        name=request.campaignName.strip(),
        templateName=request.templateName,
        templateReference=(request.templateReference or '').strip() or None,
        recipients=[],
        totalCount=0,
        pendingCount=0,
        scheduledAt=request.scheduledAt,
        dripEnabled=drip_enabled,
        dripDailyLimit=request.dripDailyLimit if drip_enabled else None,
        dripStartAt=drip_start_at,
        chainId=request.chainId,
        chainSequence=request.chainSequence,
        chainTotal=request.chainTotal,
        chainLabel=request.chainLabel,
        status=CampaignStatus.DRAFT
    )

    campaign_dict = campaign.model_dump()
    campaign_dict['createdAt'] = campaign_dict['createdAt'].isoformat()
    if campaign_dict.get('scheduledAt'):
        campaign_dict['scheduledAt'] = campaign_dict['scheduledAt'].isoformat()
    elif starts_later:
        campaign_dict['scheduledAt'] = drip_start_at
    campaign_dict['completedAt'] = None
    campaign_dict['recipients'] = []
    campaign_dict['expectedCount'] = expected
    campaign_dict['countryCode'] = request.countryCode
    campaign_dict['sendDefaults'] = _send_defaults(request)
    campaign_dict['startsLater'] = starts_later

    await db.campaigns.insert_one(campaign_dict)
    logger.info(f"Campaign {campaign.id} initialized for chunked upload of {expected} recipients")

    return {"campaignId": campaign.id, "expectedCount": expected}


@router.post("/campaigns/{campaign_id}/recipients")
async def append_recipients(
    campaign_id: str,
    payload: RecipientChunkRequest,
    current_user = Depends(get_current_user)
):
    """Step 2 of the chunked flow: append a chunk of recipients to a draft campaign"""
    campaign = await db.campaigns.find_one(
        {"id": campaign_id, "userId": current_user.userId},
        {"recipients": 0}
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.get('status') != CampaignStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail="Campaign already started")

    docs = build_recipient_docs(
        payload.recipients,
        campaign.get('countryCode'),
        campaign.get('sendDefaults') or {}
    )

    await db.campaigns.update_one(
        {"id": campaign_id},
        {
            "$push": {"recipients": {"$each": docs}},
            "$inc": {"totalCount": len(docs), "pendingCount": len(docs)}
        }
    )

    return {"added": len(docs), "totalCount": campaign.get('totalCount', 0) + len(docs)}


@router.post("/campaigns/{campaign_id}/start")
async def start_uploaded_campaign(
    campaign_id: str,
    background_tasks: BackgroundTasks,
    queued: bool = False,
    current_user = Depends(get_current_user)
):
    """Step 3 of the chunked flow: start, schedule, or queue the uploaded campaign.

    `queued=true` parks the campaign until the previous part of its chain finishes,
    so a big list runs as several small campaigns one after another.
    """
    campaign = await db.campaigns.find_one(
        {"id": campaign_id, "userId": current_user.userId},
        {"recipients": 0}
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.get('status') != CampaignStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail="Campaign already started")
    if campaign.get('totalCount', 0) < 1:
        raise HTTPException(status_code=400, detail="No recipients were uploaded")

    user = await db.users.find_one({"id": current_user.userId})
    starts_later = bool(campaign.get('startsLater'))

    if queued:
        new_status = CampaignStatus.QUEUED.value
    elif starts_later:
        new_status = CampaignStatus.SCHEDULED.value
    else:
        new_status = CampaignStatus.PENDING.value

    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {
            "status": new_status,
            "updatedAt": datetime.now(timezone.utc).isoformat()
        }}
    )

    if new_status == CampaignStatus.PENDING.value:
        background_tasks.add_task(
            process_campaign,
            campaign_id,
            user['bizChatToken'],
            user['bizChatVendorUID']
        )

    return {
        "message": "Campaign created successfully",
        "campaignId": campaign_id,
        "status": "queued" if queued else ("scheduled" if starts_later else "processing"),
        "totalCount": campaign.get('totalCount', 0)
    }


@router.post("/send")
async def send_messages(
    request: SendMessageRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
):
    """Send a bulk message campaign in one request (small lists)"""
    if not (request.campaignName or '').strip():
        raise HTTPException(status_code=400, detail="Campaign name is required")
    
    # Get user's BizChat credentials
    user = await db.users.find_one({"id": current_user.userId})
    if not user or not user.get('bizChatToken'):
        raise HTTPException(status_code=400, detail="BizChat API token not configured")
    if not user.get('bizChatVendorUID'):
        raise HTTPException(status_code=400, detail="BizChat Vendor UID not configured")
    
    # Drip validation: per-day count must fit inside the account's daily limit
    drip_enabled = bool(request.dripEnabled and request.dripDailyLimit)
    if request.dripEnabled and (not request.dripDailyLimit or request.dripDailyLimit < 1):
        raise HTTPException(status_code=400, detail="Please enter how many messages to send per day")
    if drip_enabled:
        account_limit = user.get('dailyLimit', 1000)
        if account_limit != -1 and request.dripDailyLimit > account_limit:
            raise HTTPException(
                status_code=400,
                detail=f"Messages per day ({request.dripDailyLimit}) cannot exceed your account daily limit ({account_limit}). Please lower it or contact admin."
            )
    
    # Check daily limit ONLY for immediate campaigns, not scheduled ones
    # Scheduled campaigns will be checked when they actually run
    is_scheduled = request.scheduledAt is not None
    daily_usage = user.get('dailyUsage', 0)
    daily_limit = user.get('dailyLimit', 1000)
    
    if not is_scheduled and not drip_enabled:
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
        if request.document_name_from_contact:
            recipient_dict['document_name_from_contact'] = True
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
    
    # Drip campaigns: anchor = chosen start time, or now for "start now"
    drip_start_at = None
    if drip_enabled:
        drip_start_at = (request.dripStartAt or datetime.now(timezone.utc))
        if drip_start_at.tzinfo is None:
            drip_start_at = drip_start_at.replace(tzinfo=timezone.utc)
        drip_start_at = drip_start_at.isoformat()
    
    starts_later = bool(request.scheduledAt) or (
        drip_enabled and request.dripStartAt is not None and
        datetime.fromisoformat(drip_start_at) > datetime.now(timezone.utc)
    )
    
    # Create campaign
    campaign = Campaign(
        userId=current_user.userId,
        name=request.campaignName.strip(),
        templateName=request.templateName,
        templateReference=(request.templateReference or '').strip() or None,
        recipients=[RecipientInfo(**r) for r in recipients],
        totalCount=len(recipients),
        pendingCount=len(recipients),
        scheduledAt=request.scheduledAt,
        dripEnabled=drip_enabled,
        dripDailyLimit=request.dripDailyLimit if drip_enabled else None,
        dripStartAt=drip_start_at,
        status=CampaignStatus.SCHEDULED if starts_later else CampaignStatus.PENDING
    )
    
    campaign_dict = campaign.model_dump()
    campaign_dict['createdAt'] = campaign_dict['createdAt'].isoformat()
    if campaign_dict.get('scheduledAt'):
        campaign_dict['scheduledAt'] = campaign_dict['scheduledAt'].isoformat()
    elif starts_later:
        campaign_dict['scheduledAt'] = drip_start_at
    if campaign_dict.get('completedAt'):
        campaign_dict['completedAt'] = campaign_dict['completedAt'].isoformat()
    
    campaign_dict['recipients'] = recipients
    
    await db.campaigns.insert_one(campaign_dict)
    
    # Process immediately if it isn't waiting for a start time
    if not starts_later:
        background_tasks.add_task(
            process_campaign,
            campaign.id,
            user['bizChatToken'],
            user['bizChatVendorUID']
        )
    
    return {
        "message": "Campaign created successfully",
        "campaignId": campaign.id,
        "status": "scheduled" if starts_later else "processing",
        "dailyUsage": daily_usage if drip_enabled else daily_usage + len(recipients),
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
            },
            "$unset": {"completedAt": "", "error": ""}
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
