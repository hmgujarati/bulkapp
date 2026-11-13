"""Message delivery / read receipt processing.

Updates campaign recipient statuses based on webhook status payloads
from BizChat (forwarded WhatsApp Cloud API delivery & read receipts).

Status precedence (never downgrade):
    pending(0) -> sent(1) -> delivered(2) -> read(3)
    `failed` is terminal — never overridden by later events.
"""
from datetime import datetime, timezone, timedelta
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


def _is_status_not_incoming(msg: dict, status: str) -> bool:
    """wamid + status = status update. A body/text is allowed when it is a failure
    reason or BizChat flags the event as not-new; otherwise it's a real incoming message."""
    has_body = bool(msg.get('body') or msg.get('text'))
    return not has_body or status == MessageStatus.FAILED.value or msg.get('is_new_message') is False


def _error_text(obj: dict, status: str):
    if not isinstance(obj, dict):
        return None
    err = obj.get('error') or obj.get('error_message') or obj.get('errors')
    if isinstance(err, list):
        err = err[0] if err else None
    if isinstance(err, dict):
        err = err.get('title') or err.get('message') or err.get('details') or str(err)
    if not err and status == MessageStatus.FAILED.value:
        text = obj.get('body') or obj.get('text')
        err = text.get('body') if isinstance(text, dict) else text
    return str(err)[:200] if err else None


def extract_status_data(body: dict):
    """Defensively extract status updates from a webhook payload.
    
    Supports multiple BSP shapes. Returns a list of
    `{wamid, status, timestamp, error}` dicts (or empty list if none).
    
    Common shapes handled:
      1. WhatsApp Cloud API: {"statuses": [{"id": "wamid.xxx", "status": "delivered", "timestamp": "..."}]}
      2. Single status:      {"event_type": "message_status", "wamid": "...", "status": "..."}
      3. BizChat-style (REAL, observed): 
         {"contact": {...}, "message": {"whatsapp_message_id": "wamid.xxx", "status": "delivered", "body": null, "is_new_message": false, ...}}
      4. BizChat-nested data: {"data": {"status": "delivered", "wamid": "..."}}
      5. Flat:               {"message_status": "delivered", "wamid": "..."} or {"message_id": ..., "status": ...}
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
    
    # 3. BizChat actual shape: message.{whatsapp_message_id, status} with body=null
    # This is the OBSERVED shape from bizchatapi.in production webhooks.
    if not results:
        msg = body.get('message')
        if isinstance(msg, dict):
            wamid = msg.get('whatsapp_message_id') or msg.get('id') or msg.get('message_id')
            raw_status = msg.get('status')
            status = _normalize_status(raw_status)
            if wamid and status and _is_status_not_incoming(msg, status):
                results.append({
                    'wamid': wamid,
                    'status': status,
                    'timestamp': msg.get('timestamp'),
                    'error': _error_text(msg, status),
                })
    
    # 2 / 5. Flat or event-type style
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
        msg = body.get('message') if isinstance(body.get('message'), dict) else {}
        if wamid and status and _is_status_not_incoming(msg, status):
            results.append({
                'wamid': wamid,
                'status': status,
                'timestamp': body.get('timestamp'),
                'error': _error_text(body, status) or _error_text(msg, status),
            })
    
    # 4. BizChat-nested "data" key
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
                    'error': _error_text(data, status),
                })
    
    return results


_TERMINAL_SENT = (MessageStatus.SENT.value, MessageStatus.DELIVERED.value, MessageStatus.READ.value)
_DELIVERED_OR_READ = (MessageStatus.DELIVERED.value, MessageStatus.READ.value)
PENDING_STATUS_TTL = timedelta(hours=24)
_pending_index_ready = False


def _transition(cur: str, new: str):
    """Return the $inc doc for cur -> new, or None if the transition must be ignored."""
    if cur == MessageStatus.FAILED.value:
        return None
    if new != MessageStatus.FAILED.value and _STATUS_RANK.get(new, -1) <= _STATUS_RANK.get(cur, 0):
        return None
    was_delivered, was_read = cur in _DELIVERED_OR_READ, cur == MessageStatus.READ.value
    inc = {}
    if new == MessageStatus.DELIVERED.value and not was_delivered:
        inc["deliveredCount"] = 1
    elif new == MessageStatus.READ.value:
        if not was_delivered:
            inc["deliveredCount"] = 1
        inc["readCount"] = 1
    elif new == MessageStatus.FAILED.value:
        inc["failedCount"] = 1
        if cur in _TERMINAL_SENT:
            inc["sentCount"] = -1
        if was_delivered:
            inc["deliveredCount"] = -1
        if was_read:
            inc["readCount"] = -1
    return inc


async def update_message_status(user_id: str, wamid: str, new_status: str, timestamp: str = None, error: str = None) -> bool:
    """Apply a status to the recipient with this wamid. Never downgrades; failed is terminal.
    The $set is conditional on the status we read, so concurrent webhooks can't double-apply.
    Returns True if the recipient was found (and updated or already at/above this status)."""
    query = {"recipients.messageId": wamid}
    if user_id:
        query["userId"] = user_id
    for _ in range(5):
        campaign = await db.campaigns.find_one(
            query, {"_id": 0, "id": 1, "recipients.messageId": 1, "recipients.status": 1, "recipients.deliveredAt": 1}
        )
        if not campaign:
            return False
        idx = next((i for i, r in enumerate(campaign.get('recipients', [])) if r.get('messageId') == wamid), None)
        if idx is None:
            return False
        current = campaign['recipients'][idx]
        stored_status = current.get('status')
        cur = stored_status or MessageStatus.PENDING.value
        
        now_iso = datetime.now(timezone.utc).isoformat()
        if cur == MessageStatus.FAILED.value:
            if new_status == MessageStatus.FAILED.value and error:
                await db.campaigns.update_one(
                    {"id": campaign['id'], f"recipients.{idx}.status": MessageStatus.FAILED.value},
                    {"$set": {f"recipients.{idx}.error": str(error)[:200]}}
                )
            return True
        inc = _transition(cur, new_status)
        if inc is None:
            return True
        
        set_ops = {f"recipients.{idx}.status": new_status, "updatedAt": now_iso}
        if new_status == MessageStatus.DELIVERED.value:
            set_ops[f"recipients.{idx}.deliveredAt"] = now_iso
        elif new_status == MessageStatus.READ.value:
            set_ops[f"recipients.{idx}.readAt"] = now_iso
            if not current.get('deliveredAt'):
                set_ops[f"recipients.{idx}.deliveredAt"] = now_iso
        elif new_status == MessageStatus.FAILED.value:
            set_ops[f"recipients.{idx}.error"] = str(error or 'Failed (reported by WhatsApp)')[:200]
        
        update_doc = {"$set": set_ops}
        if inc:
            update_doc["$inc"] = inc
        res = await db.campaigns.update_one(
            {"id": campaign['id'], f"recipients.{idx}.status": stored_status}, update_doc
        )
        if res.matched_count:
            logger.info(f"Status update: campaign={campaign['id']} wamid={wamid} {cur} -> {new_status} inc={inc}")
            return True
        # Another webhook / the worker changed this recipient meanwhile — re-read and re-evaluate
    logger.warning(f"Status update for {wamid} -> {new_status} gave up after repeated conflicts")
    return True


async def _ensure_pending_index():
    global _pending_index_ready
    if not _pending_index_ready:
        await db.pending_statuses.create_index("wamid")
        await db.pending_statuses.create_index("receivedAt", expireAfterSeconds=int(PENDING_STATUS_TTL.total_seconds()))
        _pending_index_ready = True


async def queue_pending_status(s: dict, user_id: str = None) -> bool:
    """wamid not in any campaign yet (worker hasn't saved messageId): park the status.
    Returns True if it was applied after all (worker saved the messageId meanwhile)."""
    await _ensure_pending_index()
    inserted = await db.pending_statuses.insert_one({
        "wamid": s['wamid'], "status": s['status'], "error": s.get('error'), "receivedAt": datetime.now(timezone.utc),
    })
    # Close the race with the worker's apply step: retry once after parking
    if await update_message_status(user_id, s['wamid'], s['status'], s.get('timestamp'), s.get('error')):
        await db.pending_statuses.delete_one({"_id": inserted.inserted_id})
        logger.info(f"Pending status {s['wamid']} -> {s['status']} applied immediately after queueing")
        return True
    logger.info(f"Queued pending status {s['wamid']} -> {s['status']} (no campaign recipient yet)")
    return False


async def apply_pending_statuses(user_id: str, wamids: list) -> int:
    """Called by the campaign worker right after it saves messageIds."""
    if not wamids:
        return 0
    await _ensure_pending_index()
    entries = await db.pending_statuses.find({"wamid": {"$in": wamids}}).sort("receivedAt", 1).to_list(None)
    applied = 0
    for e in entries:
        if await update_message_status(user_id, e['wamid'], e['status'], error=e.get('error')):
            applied += 1
            await db.pending_statuses.delete_one({"_id": e['_id']})
    if applied:
        logger.info(f"Applied {applied} queued status(es) for {len(wamids)} new messageIds")
    return applied


async def process_status_payload(user_id: str, body: dict, statuses: list = None) -> int:
    """Apply every status in the payload; unmatched ones are queued in pending_statuses.
    Returns the number of statuses found (applied or queued)."""
    statuses = extract_status_data(body) if statuses is None else statuses
    for s in statuses:
        matched = await update_message_status(
            user_id=user_id, wamid=s['wamid'], new_status=s['status'],
            timestamp=s.get('timestamp'), error=s.get('error'),
        )
        logger.info(f"[webhook-status] wamid={s['wamid']} status={s['status']} error={s.get('error')} matched={matched}")
        if not matched:
            await queue_pending_status(s, user_id)
    return len(statuses)
