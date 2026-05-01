"""Track WhatsApp template button clicks.

When a recipient taps a Quick Reply button on a campaign message, BizChat
forwards an incoming-message webhook that includes
`message.replied_to_whatsapp_message_id` (pointing back to the original
campaign send wamid) plus the button text in `message.body`.

We use that to attribute the click to the right campaign + recipient
so admins can filter and export clickers.
"""
from datetime import datetime, timezone
import logging

from utils.database import db

logger = logging.getLogger(__name__)


def extract_button_click(body: dict):
    """Return {wamid, button_text, timestamp} if this webhook is a button click,
    otherwise None.
    
    A button click has these signals (defensive — we accept any of them):
    - `message.replied_to_whatsapp_message_id` is set (BizChat-observed shape)
    - `message.interactive.button_reply.title` (Cloud API interactive shape)
    - `message.button.text` (Cloud API quick-reply shape)
    """
    if not isinstance(body, dict):
        return None
    
    msg = body.get('message') if isinstance(body.get('message'), dict) else {}
    
    # Shape A — BizChat default: replied_to_whatsapp_message_id + body text
    replied_to = msg.get('replied_to_whatsapp_message_id') or body.get('replied_to_whatsapp_message_id')
    if replied_to:
        button_text = (msg.get('body') or msg.get('text') or '').strip()
        if button_text:
            return {
                'wamid': replied_to,
                'button_text': button_text,
                'timestamp': msg.get('timestamp') or body.get('timestamp'),
            }
    
    # Shape B — WhatsApp Cloud API interactive button_reply
    interactive = msg.get('interactive') if isinstance(msg.get('interactive'), dict) else None
    if interactive:
        br = interactive.get('button_reply') if isinstance(interactive.get('button_reply'), dict) else None
        if br:
            ctx = msg.get('context') if isinstance(msg.get('context'), dict) else {}
            wamid = ctx.get('id') or ctx.get('message_id')
            if wamid:
                return {
                    'wamid': wamid,
                    'button_text': br.get('title') or br.get('id') or '',
                    'timestamp': msg.get('timestamp') or body.get('timestamp'),
                }
    
    # Shape C — Cloud API quick-reply button
    button = msg.get('button') if isinstance(msg.get('button'), dict) else None
    if button:
        ctx = msg.get('context') if isinstance(msg.get('context'), dict) else {}
        wamid = ctx.get('id') or ctx.get('message_id')
        if wamid:
            return {
                'wamid': wamid,
                'button_text': button.get('text') or button.get('payload') or '',
                'timestamp': msg.get('timestamp') or body.get('timestamp'),
            }
    
    return None


async def record_button_click(user_id: str, wamid: str, button_text: str) -> bool:
    """Find the campaign recipient that this wamid belongs to and record the click.
    
    Returns True if a recipient was updated, False otherwise (e.g. wamid is not
    from a campaign message — could be from a chatbot reply or other context).
    """
    if not wamid or not button_text:
        return False
    
    campaign = await db.campaigns.find_one(
        {"userId": user_id, "recipients.messageId": wamid},
        {"_id": 0, "id": 1, "recipients": 1}
    )
    if not campaign:
        return False
    
    target_idx = None
    for i, r in enumerate(campaign['recipients']):
        if r.get('messageId') == wamid:
            target_idx = i
            break
    if target_idx is None:
        return False
    
    now_iso = datetime.now(timezone.utc).isoformat()
    
    # Don't overwrite an earlier click — keep the FIRST click only
    if campaign['recipients'][target_idx].get('clickedButton'):
        return False
    
    await db.campaigns.update_one(
        {"id": campaign['id']},
        {
            "$set": {
                f"recipients.{target_idx}.clickedButton": button_text[:100],
                f"recipients.{target_idx}.clickedAt": now_iso,
                "updatedAt": now_iso,
            }
        }
    )
    
    logger.info(
        f"Button click: campaign={campaign['id']} wamid={wamid[:30]}... "
        f"phone={campaign['recipients'][target_idx].get('phone')} button='{button_text[:50]}'"
    )
    return True
