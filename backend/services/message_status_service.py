"""Message delivery / read receipt processing.

Updates campaign recipient statuses based on webhook status payloads
from BizChat (forwarded WhatsApp Cloud API delivery & read receipts).

Status precedence (never downgrade):
    pending(0) -> sent(1) -> delivered(2) -> read(3)
    `failed` is terminal — never overridden by later events.
"""
from datetime import datetime, timezone
import logging

from utils.database import db
from models.schemas import MessageStatus

logger = logging.getLogger(__name__)

# Numeric rank for "do not downgrade" comparisons
_STATUS_RANK = {
    MessageStatus.PENDING.value: 0,
    MessageStatus.SENT.value: 1,
    MessageStatus.DELIVERED.value: 2,
    MessageStatus.READ.value: 3,
}


def _normalize_status(raw: str) -> str:
    """Map any incoming status string to a known MessageStatus value, or None."""
    if not raw:
        return None
    s = str(raw).strip().lower()
    # Direct matches
    if s in ('sent', 'delivered', 'read', 'failed'):
        return s
    # Common aliases from various BSPs
    aliases = {
        'success': 'sent',
        'accepted': 'sent',
        'queued': 'sent',
        'submitted': 'sent',
        'received': 'delivered',
        'seen': 'read',
        'viewed': 'read',
        'failure': 'failed',
        'error': 'failed',
        'rejected': 'failed',
        'undeliverable': 'failed',
    }
    return aliases.get(s)


def extract_status_data(body: dict):
    """Defensively extract status updates from a webhook payload.
    
    Supports multiple BSP shapes. Returns a list of
    `{wamid, status, timestamp, error}` dicts (or empty list if none).
    
    Common shapes handled:
      1. WhatsApp Cloud API: {"statuses": [{"id": "wamid.xxx", "status": "delivered", "timestamp": "..."}]}
      2. Single status:      {"event_type": "message_status", "wamid": "...", "status": "..."}
      3. BizChat-style:      {"data": {"status": "delivered", "wamid": "..."}}
      4. Flat:               {"message_status": "delivered", "wamid": "..."} or {"message_id": ..., "status": ...}
    """
    if not isinstance(body, dict):
        return []
    
    results = []
    
    # 1. Cloud-API-style "statuses" array
    statuses = body.get('statuses')
    if isinstance(statuses, list):
        for s in statuses:
            if not isinstance(s, dict):
                continue
            wamid = s.get('id') or s.get('message_id') or s.get('wamid')
            status = _normalize_status(s.get('status'))
            if wamid and status:
                results.append({
                    'wamid': wamid,
                    'status': status,
                    'timestamp': s.get('timestamp'),
                    'error': (s.get('errors') or [{}])[0].get('title') if s.get('errors') else None,
                })
    
    # 2 / 4. Flat or event-type style
    if not results:
        wamid = (
            body.get('wamid')
            or body.get('whatsapp_message_id')
            or body.get('message_id')
            or body.get('id')
        )
        status = _normalize_status(
            body.get('status')
            or body.get('message_status')
            or body.get('event_type') if str(body.get('event_type', '')).lower() in ('sent','delivered','read','failed') else body.get('status')
        )
        # Don't pick up a regular incoming message — those have message.body
        if wamid and status and not (isinstance(body.get('message'), dict) and (body['message'].get('body') or body['message'].get('text'))):
            results.append({
                'wamid': wamid,
                'status': status,
                'timestamp': body.get('timestamp'),
                'error': body.get('error'),
            })
    
    # 3. BizChat-nested
    if not results:
        data = body.get('data')
        if isinstance(data, dict):
            wamid = data.get('wamid') or data.get('message_id') or data.get('id')
            status = _normalize_status(data.get('status') or data.get('message_status'))
            if wamid and status:
                results.append({
                    'wamid': wamid,
                    'status': status,
                    'timestamp': data.get('timestamp'),
                    'error': data.get('error'),
                })
    
    return results


async def update_message_status(user_id: str, wamid: str, new_status: str, timestamp: str = None, error: str = None) -> bool:
    """Find the campaign recipient with this wamid (under this user) and update its status.
    
    Respects status precedence: never downgrades a higher status to a lower one,
    and never overrides a `failed` recipient.
    
    Returns True if a recipient was updated, False otherwise.
    """
    # Find the campaign that contains this wamid
    campaign = await db.campaigns.find_one(
        {"userId": user_id, "recipients.messageId": wamid},
        {"_id": 0}
    )
    
    if not campaign:
        # wamid not found — likely a non-campaign message (reminder/chatbot reply)
        return False
    
    # Locate the recipient
    recipients = campaign.get('recipients', [])
    target_idx = None
    for i, r in enumerate(recipients):
        if r.get('messageId') == wamid:
            target_idx = i
            break
    
    if target_idx is None:
        return False
    
    current = recipients[target_idx]
    current_status = current.get('status') or MessageStatus.PENDING.value
    
    # Don't override terminal failure
    if current_status == MessageStatus.FAILED.value and new_status != MessageStatus.FAILED.value:
        return False
    
    # Don't downgrade
    cur_rank = _STATUS_RANK.get(current_status, 0)
    new_rank = _STATUS_RANK.get(new_status, -1)
    if new_status != MessageStatus.FAILED.value and new_rank <= cur_rank:
        return False
    
    # Build update
    now_iso = datetime.now(timezone.utc).isoformat()
    set_ops = {
        f"recipients.{target_idx}.status": new_status,
    }
    if new_status == MessageStatus.DELIVERED.value:
        set_ops[f"recipients.{target_idx}.deliveredAt"] = now_iso
    elif new_status == MessageStatus.READ.value:
        set_ops[f"recipients.{target_idx}.readAt"] = now_iso
        # If we somehow missed a delivered event, backfill deliveredAt too
        if not current.get('deliveredAt'):
            set_ops[f"recipients.{target_idx}.deliveredAt"] = now_iso
    elif new_status == MessageStatus.FAILED.value and error:
        set_ops[f"recipients.{target_idx}.error"] = str(error)[:200]
    
    set_ops["updatedAt"] = now_iso
    
    # Recompute aggregate counts after the change
    updated_recipients = list(recipients)
    updated_recipients[target_idx] = {
        **current,
        'status': new_status,
        **({k.split('.')[-1]: v for k, v in set_ops.items() if k.startswith(f"recipients.{target_idx}.")}),
    }
    
    delivered_count = sum(
        1 for r in updated_recipients
        if r.get('status') in (MessageStatus.DELIVERED.value, MessageStatus.READ.value)
    )
    read_count = sum(1 for r in updated_recipients if r.get('status') == MessageStatus.READ.value)
    failed_count = sum(1 for r in updated_recipients if r.get('status') == MessageStatus.FAILED.value)
    
    set_ops["deliveredCount"] = delivered_count
    set_ops["readCount"] = read_count
    set_ops["failedCount"] = failed_count
    
    await db.campaigns.update_one(
        {"id": campaign['id']},
        {"$set": set_ops}
    )
    
    logger.info(
        f"Status update: campaign={campaign['id']} wamid={wamid} "
        f"{current_status} -> {new_status} (delivered={delivered_count}, read={read_count})"
    )
    return True


async def process_status_payload(user_id: str, body: dict) -> int:
    """Top-level entry called from the webhook. Extracts all statuses
    from the payload and applies them. Returns the number of recipients updated.
    """
    statuses = extract_status_data(body)
    if not statuses:
        return 0
    
    updated = 0
    for s in statuses:
        ok = await update_message_status(
            user_id=user_id,
            wamid=s['wamid'],
            new_status=s['status'],
            timestamp=s.get('timestamp'),
            error=s.get('error'),
        )
        if ok:
            updated += 1
    
    return updated
