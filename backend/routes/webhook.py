"""Webhook handler for incoming WhatsApp messages"""
from fastapi import APIRouter, HTTPException, Request
from datetime import datetime, timezone, timedelta
from typing import Optional
import logging
import json
import httpx
import pytz
import re

from models.reminder_schemas import Reminder, ReminderStatus, RecurrenceConfig, RecurrenceType
from utils.database import db
from services.chatbot_service import handle_chatbot_message
from services.message_status_service import process_status_payload, extract_status_data
from services.button_click_service import extract_button_click, record_button_click

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["Webhook"])


# Commands that users can send via WhatsApp
LIST_COMMANDS = ['show reminders', 'list reminders', 'my reminders', 'reminders', 'show my reminders', 'pending reminders']
HELP_COMMANDS = ['help', 'commands', 'what can you do', '?']
DELETE_ALL_COMMANDS = ['delete all', 'clear reminders', 'cancel all', 'delete all reminders', 'clear all']


async def get_reminders_list(user_id: str, user_timezone: str, phone: str = None) -> str:
    """Get formatted list of user's reminders for a specific phone number"""
    tz = pytz.timezone(user_timezone)
    now = datetime.now(tz)
    
    # Build query - filter by phone number if provided
    query = {
        "userId": user_id,
        "status": "pending"
    }
    
    # Only show reminders for the specific phone number that sent the message
    if phone:
        query["phone"] = phone
    
    # Get pending reminders
    reminders = await db.reminders.find(query).sort("scheduledAt", 1).to_list(20)
    
    if not reminders:
        return """📋 *Your Reminders*

You have no pending reminders.

💡 To create a reminder, just send:
"Remind me to call John at 3pm tomorrow"
"Remind me daily to take medicine at 9am"

_- Your WhatsApp Assistant_"""
    
    # Format the list
    reminder_list = []
    for i, r in enumerate(reminders, 1):
        try:
            scheduled_dt = datetime.fromisoformat(r['scheduledAt'].replace('Z', '+00:00'))
            local_time = scheduled_dt.astimezone(tz)
            time_str = local_time.strftime("%I:%M %p, %d %b").lstrip('0')
        except Exception:
            time_str = "Unknown time"
        
        # Add recurrence indicator
        recurrence = r.get('recurrence', {})
        recurrence_icon = ""
        if recurrence and recurrence.get('type') and recurrence.get('type') != 'none':
            recurrence_type = recurrence.get('type')
            if recurrence_type == 'daily':
                recurrence_icon = " 🔄"
            elif recurrence_type == 'weekly':
                recurrence_icon = " 🔄W"
            elif recurrence_type == 'monthly':
                recurrence_icon = " 🔄M"
            elif recurrence_type == 'custom':
                recurrence_icon = f" 🔄{recurrence.get('interval', '')}d"
        
        reminder_list.append(f"{i}. {r.get('title', 'Reminder')}{recurrence_icon}\n   ⏰ {time_str}")
    
    reminders_text = "\n\n".join(reminder_list)
    
    return f"""📋 *Your Pending Reminders*

{reminders_text}

━━━━━━━━━━━━━━━
📝 Total: {len(reminders)} reminder(s)
🔄 = Recurring

💡 Commands:
• "delete 1" - Delete reminder #1
• "delete all" - Delete all reminders
• "help" - See all commands

_- Your WhatsApp Assistant_"""


async def delete_reminder_by_name(user_id: str, search_text: str, user_timezone: str = "Asia/Kolkata", phone: str = None) -> str:
    """Delete a reminder by searching its title/message"""
    import pytz
    tz = pytz.timezone(user_timezone)
    
    # Build query - filter by phone number if provided
    query = {
        "userId": user_id,
        "status": "pending"
    }
    if phone:
        query["phone"] = phone
    
    # Get pending reminders
    reminders = await db.reminders.find(query).sort("scheduledAt", 1).to_list(200)
    
    if not reminders:
        return "❌ You have no pending reminders to delete."
    
    # Search for matching reminder (case-insensitive)
    search_lower = search_text.lower()
    matching_reminders = []
    
    for r in reminders:
        title = r.get('title', '').lower()
        message = r.get('message', '').lower()
        original = r.get('originalInput', '').lower()
        
        if search_lower in title or search_lower in message or search_lower in original:
            matching_reminders.append(r)
    
    if not matching_reminders:
        return f"""❌ No reminder found matching "{search_text}"

💡 Use "show reminders" to see your list."""
    
    if len(matching_reminders) == 1:
        # Delete the single match
        reminder = matching_reminders[0]
        await db.reminders.delete_one({"id": reminder['id']})
        return f"""✅ *Reminder Deleted*

🗑️ Deleted: {reminder.get('title', 'Reminder')}

_- Your WhatsApp Assistant_"""
    else:
        # Multiple matches - save search context and show them
        # Store the matching reminder IDs for this user
        await db.user_search_context.update_one(
            {"userId": user_id},
            {
                "$set": {
                    "userId": user_id,
                    "matchingIds": [r['id'] for r in matching_reminders],
                    "searchText": search_text,
                    "createdAt": datetime.now(timezone.utc).isoformat()
                }
            },
            upsert=True
        )
        
        # Show matches with numbers (1-based, from search results)
        match_list = []
        for i, r in enumerate(matching_reminders[:10], 1):  # Show max 10
            try:
                scheduled_dt = datetime.fromisoformat(r['scheduledAt'].replace('Z', '+00:00'))
                local_time = scheduled_dt.astimezone(tz)
                time_str = local_time.strftime("%I:%M %p, %d %b").lstrip('0')
            except Exception:
                time_str = "Unknown"
            match_list.append(f"*{i}.* {r.get('title', 'Reminder')}\n    ⏰ {time_str}")
        
        matches_text = "\n\n".join(match_list)
        more_text = f"\n\n_...and {len(matching_reminders) - 10} more_" if len(matching_reminders) > 10 else ""
        
        return f"""🔍 *Found {len(matching_reminders)} reminders matching "{search_text}":*

{matches_text}{more_text}

━━━━━━━━━━━━━━━
💡 Reply with number to delete:
• "1" - Delete #{1}
• "2" - Delete #{2}
• "delete all {search_text}" - Delete all matches

_- Your WhatsApp Assistant_"""


async def delete_from_search_context(user_id: str, number: int) -> str:
    """Delete a reminder from the last search results"""
    # Get search context
    context = await db.user_search_context.find_one({"userId": user_id})
    
    if not context or not context.get('matchingIds'):
        return None  # No search context, use regular delete
    
    matching_ids = context['matchingIds']
    
    if number < 1 or number > len(matching_ids):
        return f"❌ Invalid number. Enter 1-{len(matching_ids)} from your last search."
    
    # Get the reminder to delete
    reminder_id = matching_ids[number - 1]
    reminder = await db.reminders.find_one({"id": reminder_id})
    
    if not reminder:
        return "❌ Reminder not found. It may have already been deleted."
    
    if reminder['status'] != 'pending':
        return "❌ This reminder has already been sent or cancelled."
    
    # Delete it
    await db.reminders.delete_one({"id": reminder_id})
    
    # Clear the search context
    await db.user_search_context.delete_one({"userId": user_id})
    
    return f"""✅ *Reminder Deleted*

🗑️ Deleted: {reminder.get('title', 'Reminder')}

_- Your WhatsApp Assistant_"""


async def delete_reminder_by_number(user_id: str, reminder_num: int, user_timezone: str, phone: str = None) -> str:
    """Delete a specific reminder by its list number"""
    # Build query - filter by phone number if provided
    query = {
        "userId": user_id,
        "status": "pending"
    }
    if phone:
        query["phone"] = phone
    
    # Get pending reminders in order
    reminders = await db.reminders.find(query).sort("scheduledAt", 1).to_list(20)
    
    if not reminders:
        return "❌ You have no pending reminders to delete."
    
    if reminder_num < 1 or reminder_num > len(reminders):
        return f"❌ Invalid number. You have {len(reminders)} reminder(s). Use 'show reminders' to see the list."
    
    # Get the reminder to delete
    reminder_to_delete = reminders[reminder_num - 1]
    
    # Delete it
    await db.reminders.delete_one({"id": reminder_to_delete['id']})
    
    return f"""✅ *Reminder Deleted*

🗑️ Deleted: {reminder_to_delete.get('title', 'Reminder')}

You have {len(reminders) - 1} reminder(s) remaining.

_- Your WhatsApp Assistant_"""


async def delete_all_matching_reminders(user_id: str, search_text: str, phone: str = None) -> str:
    """Delete all reminders matching a search term"""
    # Build query - filter by phone number if provided
    query = {
        "userId": user_id,
        "status": "pending"
    }
    if phone:
        query["phone"] = phone
    
    # Get pending reminders
    reminders = await db.reminders.find(query).to_list(500)
    
    if not reminders:
        return "❌ You have no pending reminders."
    
    # Search for matching reminders
    search_lower = search_text.lower()
    matching_ids = []
    matching_titles = []
    
    for r in reminders:
        title = r.get('title', '').lower()
        message = r.get('message', '').lower()
        original = r.get('originalInput', '').lower()
        
        if search_lower in title or search_lower in message or search_lower in original:
            matching_ids.append(r['id'])
            matching_titles.append(r.get('title', 'Reminder'))
    
    if not matching_ids:
        return f"❌ No reminders found matching \"{search_text}\""
    
    # Delete all matches
    await db.reminders.delete_many({"id": {"$in": matching_ids}})
    
    # Clear search context
    await db.user_search_context.delete_one({"userId": user_id})
    
    if len(matching_ids) == 1:
        return f"""✅ *Reminder Deleted*

🗑️ Deleted: {matching_titles[0]}

_- Your WhatsApp Assistant_"""
    else:
        return f"""✅ *{len(matching_ids)} Reminders Deleted*

🗑️ Deleted all reminders matching "{search_text}"

_- Your WhatsApp Assistant_"""


async def delete_all_reminders(user_id: str, phone: str = None) -> str:
    """Delete all pending reminders for a user (filtered by phone if provided)"""
    # Build query - filter by phone number if provided
    query = {
        "userId": user_id,
        "status": "pending"
    }
    if phone:
        query["phone"] = phone
    
    result = await db.reminders.delete_many(query)
    
    if result.deleted_count == 0:
        return "📋 You have no pending reminders to delete."
    
    return f"""✅ *All Reminders Deleted*

🗑️ Deleted {result.deleted_count} reminder(s)

Your reminder list is now empty.

_- Your WhatsApp Assistant_"""


async def get_help_message() -> str:
    """Get help message with available commands"""
    return """🤖 *WhatsApp Reminder Bot*

Here's what I can do:

📌 *Create Reminders*
• "Remind me to call John at 3pm"
• "Meeting with boss tomorrow at 10am"
• "Take medicine in 2 hours"

🔄 *Recurring Reminders*
• "Remind me daily to take medicine at 9am"
• "Every Monday remind me to submit report"
• "Remind me every 2 weeks to pay rent"

📋 *View Reminders*
• "show reminders"
• "my reminders"

🗑️ *Delete Reminders*
• "delete 1" - Delete reminder #1
• "delete all" - Delete all reminders
• "cancel call meeting" - Delete by name

❓ *Get Help*
• "help"

━━━━━━━━━━━━━━━
💡 Tip: I understand natural language!

_- Your WhatsApp Assistant_"""


async def parse_reminder_from_message(message: str, user_timezone: str, api_key: str) -> dict:
    """Parse natural language message using OpenAI"""
    import pytz
    
    tz = pytz.timezone(user_timezone)
    now = datetime.now(tz)
    
    system_prompt = f"""You are a reminder parsing assistant. Parse the user's WhatsApp message and extract reminder details.

Current date/time in user's timezone ({user_timezone}): {now.strftime('%Y-%m-%d %H:%M:%S %Z')}

IMPORTANT RULES:
1. ONLY parse messages that are clearly reminder requests
2. Extract what the user wants to be reminded about
3. Parse the time/date mentioned
4. "tomorrow" means the next day, "today" means today
5. If no specific time is given, default to 9:00 AM
6. Return times in ISO 8601 format with timezone offset

RECURRENCE PATTERNS - Look for these keywords:
- "daily", "every day", "everyday" = daily recurrence
- "weekly", "every week" = weekly recurrence  
- "monthly", "every month" = monthly recurrence
- "every 2 days", "every 3 weeks" = custom interval
- "every monday", "every tue and thu" = specific weekdays (use weekdays array: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun)

For a REMINDER REQUEST, respond with JSON:
{{"title": "Short title (max 50 chars)", "message": "Full reminder message", "scheduled_time": "2025-01-22T10:00:00+05:30", "confidence": 0.95, "is_reminder": true, "recurrence": {{"type": "none|daily|weekly|monthly|custom", "interval": 1, "weekdays": []}}}}

Examples:
- "remind me daily to take medicine at 9am" -> recurrence: {{"type": "daily", "interval": 1, "weekdays": []}}
- "remind me every monday to submit report" -> recurrence: {{"type": "weekly", "interval": 1, "weekdays": [0]}}
- "remind me every 2 weeks to pay rent" -> recurrence: {{"type": "custom", "interval": 14, "weekdays": []}}

If the message is NOT a reminder request (greetings, random questions, conversations), return:
{{"is_reminder": false}}

DO NOT chat or have conversations. Only parse reminders.
"""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 300
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content']
                return json.loads(content)
            else:
                logger.error(f"OpenAI API error: {response.text}")
                return {"is_reminder": False, "reply": "Sorry, I couldn't process your message. Please try again."}
                
    except Exception as e:
        logger.error(f"Error parsing message: {str(e)}")
        return {"is_reminder": False, "reply": "Sorry, something went wrong. Please try again."}


async def send_whatsapp_reply(phone: str, message: str, token: str, vendor_uid: str):
    """Send a reply back to the user"""
    try:
        async with httpx.AsyncClient() as client:
            url = f"https://bizchatapi.in/api/{vendor_uid}/contact/send-message?token={token}"
            payload = {
                "phone_number": phone.replace('+', '').replace('-', '').replace(' ', ''),
                "message_body": message
            }
            
            response = await client.post(url, json=payload, timeout=30.0)
            logger.info(f"Reply sent to {phone}: {response.status_code}")
            return response.status_code in [200, 201]
    except Exception as e:
        logger.error(f"Error sending reply: {str(e)}")
        return False


@router.post("/bizchat")
async def handle_bizchat_webhook(request: Request):
    """Legacy webhook - handles messages from users with registered reminder numbers"""
    try:
        body = await request.json()
        logger.info(f"Received legacy webhook: {json.dumps(body)[:500]}")

        # === STATUS UPDATE (delivery / read receipts) ===
        # If the payload is a status update, route to status processor.
        # Legacy webhook doesn't carry a user_id, so we resolve it from the wamid.
        statuses = extract_status_data(body)
        if statuses:
            updated_total = 0
            for s in statuses:
                # Find which user owns this wamid
                campaign = await db.campaigns.find_one(
                    {"recipients.messageId": s['wamid']},
                    {"userId": 1, "_id": 0}
                )
                if campaign:
                    n = await process_status_payload(campaign['userId'], {"statuses": [s]})
                    updated_total += n
            return {"status": "success", "type": "status_update", "updated": updated_total}

        # === BUTTON CLICK on a campaign message ===
        click = extract_button_click(body)
        if click:
            campaign = await db.campaigns.find_one(
                {"recipients.messageId": click['wamid']},
                {"userId": 1, "_id": 0}
            )
            if campaign:
                recorded = await record_button_click(campaign['userId'], click['wamid'], click['button_text'])
                if recorded:
                    return {"status": "success", "type": "button_click", "button": click['button_text']}

        phone, message_text, is_new_message, client_name, message_id = extract_message_data(body)

        if not phone or not message_text:
            return {"status": "ignored", "reason": "missing phone or message"}
        if not is_new_message:
            return {"status": "ignored", "reason": "not a new message"}
        if is_duplicate_message(message_id):
            logger.info(f"Duplicate message {message_id} ignored")
            return {"status": "ignored", "reason": "duplicate message"}

        clean_phone = '+' + str(phone).replace('+', '').replace('-', '').replace(' ', '')

        # Find user via reminder_numbers
        number_record = await db.reminder_numbers.find_one({"phone": clean_phone})
        if not number_record:
            number_record = await db.reminder_numbers.find_one({"phone": phone.replace('-', '').replace(' ', '')})

        if not number_record:
            # Also check active chatbot conversations
            active_conv = await db.chatbot_conversations.find_one({
                "clientPhone": clean_phone,
                "status": {"$in": ["active", "followup_pending"]}
            })
            if active_conv:
                return await process_user_message(active_conv['userId'], clean_phone, message_text, client_name, body)
            return {"status": "ignored", "reason": "phone not registered"}

        user_id = number_record['userId']
        return await process_user_message(user_id, clean_phone, message_text, client_name, body)

    except Exception as e:
        logger.error(f"Legacy webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}


@router.post("/{user_id}")
async def handle_universal_webhook(user_id: str, request: Request):
    """
    Universal webhook - single URL per user that handles ALL features:
    chatbot, reminders, and any future features.
    URL: /api/webhook/{user_id}
    """
    try:
        # Verify user exists
        user = await db.users.find_one({"id": user_id})
        if not user:
            return {"status": "error", "message": "Invalid user"}

        body = await request.json()
        logger.info(f"Universal webhook for user {user_id}: {json.dumps(body)[:500]}")

        # === STATUS UPDATE (delivery / read receipts) ===
        statuses_updated = await process_status_payload(user_id, body)
        if statuses_updated > 0:
            return {"status": "success", "type": "status_update", "updated": statuses_updated}

        # === BUTTON CLICK on a campaign message ===
        click = extract_button_click(body)
        if click:
            recorded = await record_button_click(user_id, click['wamid'], click['button_text'])
            if recorded:
                return {"status": "success", "type": "button_click", "button": click['button_text']}
            # If wamid didn't belong to a campaign, fall through — could be a reply
            # to a chatbot/reminder message. Continue normal routing.

        phone, message_text, is_new_message, client_name, message_id = extract_message_data(body)

        if not phone or not message_text:
            return {"status": "ignored", "reason": "missing phone or message"}
        if not is_new_message:
            return {"status": "ignored", "reason": "not a new message"}
        if is_duplicate_message(message_id):
            logger.info(f"Duplicate message {message_id} ignored")
            return {"status": "ignored", "reason": "duplicate message"}

        clean_phone = '+' + str(phone).replace('+', '').replace('-', '').replace(' ', '')

        return await process_user_message(user_id, clean_phone, message_text, client_name, body)

    except Exception as e:
        logger.error(f"Universal webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}


@router.get("/bizchat")
async def verify_bizchat_webhook(request: Request):
    """Verify legacy webhook endpoint"""
    params = dict(request.query_params)
    if 'challenge' in params:
        return {"challenge": params['challenge']}
    if 'hub.challenge' in params:
        return int(params['hub.challenge'])
    return {"status": "ok", "message": "Webhook endpoint active"}


@router.get("/{user_id}")
async def verify_universal_webhook(user_id: str, request: Request):
    """Verify universal webhook endpoint"""
    params = dict(request.query_params)
    if 'challenge' in params:
        return {"challenge": params['challenge']}
    if 'hub.challenge' in params:
        return int(params['hub.challenge'])
    return {"status": "ok", "message": "Webhook active", "user_id": user_id}


def extract_message_data(body: dict):
    """Extract phone, message text, is_new_message, message_id, and client name from webhook payload"""
    phone = None
    if 'contact' in body and body['contact']:
        phone = body['contact'].get('phone_number')
    if not phone:
        phone = body.get('phone_number') or body.get('from') or body.get('sender')

    message_text = None
    if 'message' in body and body['message']:
        message_text = body['message'].get('body') or body['message'].get('text')
    if not message_text:
        message_text = body.get('message') or body.get('text') or body.get('body') or body.get('message_body')

    is_new_message = True
    if 'message' in body and body['message']:
        is_new_message = body['message'].get('is_new_message', True)

    # Extract WhatsApp message ID for deduplication
    message_id = None
    if 'message' in body and body['message']:
        message_id = body['message'].get('whatsapp_message_id')

    client_name = None
    if 'contact' in body and body['contact']:
        client_name = body['contact'].get('first_name', '')
        last_name = body['contact'].get('last_name', '')
        if last_name:
            client_name = f"{client_name} {last_name}".strip()

    return phone, message_text, is_new_message, client_name, message_id


# In-memory deduplication cache (TTL-based)
_processed_message_ids = {}
_DEDUP_TTL_SECONDS = 30


def is_duplicate_message(message_id: str) -> bool:
    """Check if this message was already processed (prevents duplicate webhooks)"""
    if not message_id:
        return False

    now = datetime.now(timezone.utc).timestamp()

    # Clean old entries
    expired = [mid for mid, ts in _processed_message_ids.items() if now - ts > _DEDUP_TTL_SECONDS]
    for mid in expired:
        del _processed_message_ids[mid]

    if message_id in _processed_message_ids:
        return True

    _processed_message_ids[message_id] = now
    return False


async def process_user_message(user_id: str, clean_phone: str, message_text: str, client_name: str, body: dict):
    """
    Core message processor. Routes messages through features in priority order:
    1. Chatbot (trigger keywords / active conversation)
    2. Reminder Bot (commands and natural language)
    3. Future features can be added here
    """
    logger.info(f"Processing message for user {user_id} from {clean_phone}: {message_text}")

    # === 1. CHATBOT ===
    chatbot_handled = await handle_chatbot_message(user_id, clean_phone, message_text, client_name)
    if chatbot_handled:
        logger.info(f"Message handled by chatbot for user {user_id}")
        return {"status": "success", "handler": "chatbot"}

    # === 2. REMINDER BOT ===
    # Check if user has a reminder number registered for this phone
    number_record = await db.reminder_numbers.find_one({"phone": clean_phone})
    if not number_record:
        number_record = await db.reminder_numbers.find_one({"phone": clean_phone.replace('+', '')})

    if not number_record or number_record['userId'] != user_id:
        # Phone not registered for reminders under this user - nothing more to do
        logger.info(f"No reminder number for {clean_phone} under user {user_id}")
        return {"status": "ignored", "reason": "no matching handler"}

    user = await db.users.find_one({"id": user_id})
    user_timezone = number_record.get('timezone', 'Asia/Kolkata')
    settings = await db.reminder_settings.find_one({"userId": user_id})

    message_lower = message_text.lower().strip()

    # Handle LIST commands
    if any(cmd in message_lower for cmd in LIST_COMMANDS):
        if user and user.get('bizChatToken') and user.get('bizChatVendorUID'):
            reminders_list = await get_reminders_list(user_id, user_timezone, clean_phone)
            await send_whatsapp_reply(clean_phone, reminders_list, user['bizChatToken'], user['bizChatVendorUID'])
        return {"status": "success", "action": "list_reminders"}

    # Handle HELP commands
    if any(cmd in message_lower for cmd in HELP_COMMANDS):
        if user and user.get('bizChatToken') and user.get('bizChatVendorUID'):
            help_msg = await get_help_message()
            await send_whatsapp_reply(clean_phone, help_msg, user['bizChatToken'], user['bizChatVendorUID'])
        return {"status": "success", "action": "help"}

    # Handle DELETE ALL with search term
    delete_all_search_match = re.match(r'^(delete|cancel|remove)\s+all\s+(.+)$', message_lower)
    if delete_all_search_match:
        search_text = delete_all_search_match.group(2).strip()
        if search_text and search_text not in ['reminders', 'my reminders']:
            if user and user.get('bizChatToken') and user.get('bizChatVendorUID'):
                delete_msg = await delete_all_matching_reminders(user_id, search_text, clean_phone)
                await send_whatsapp_reply(clean_phone, delete_msg, user['bizChatToken'], user['bizChatVendorUID'])
            return {"status": "success", "action": "delete_all_matching", "search": search_text}

    # Handle DELETE ALL commands
    if any(cmd in message_lower for cmd in DELETE_ALL_COMMANDS):
        if user and user.get('bizChatToken') and user.get('bizChatVendorUID'):
            delete_msg = await delete_all_reminders(user_id, clean_phone)
            await send_whatsapp_reply(clean_phone, delete_msg, user['bizChatToken'], user['bizChatVendorUID'])
        return {"status": "success", "action": "delete_all"}

    # Handle DELETE specific reminder
    delete_match = re.match(r'^(delete|cancel|remove)\s*#?\s*(\d+)$', message_lower)
    if delete_match:
        reminder_num = int(delete_match.group(2))
        if user and user.get('bizChatToken') and user.get('bizChatVendorUID'):
            delete_msg = await delete_from_search_context(user_id, reminder_num)
            if not delete_msg:
                delete_msg = await delete_reminder_by_number(user_id, reminder_num, user_timezone, clean_phone)
            await send_whatsapp_reply(clean_phone, delete_msg, user['bizChatToken'], user['bizChatVendorUID'])
        return {"status": "success", "action": "delete_reminder", "number": reminder_num}

    # Handle just a number (after search results)
    if message_lower.isdigit():
        reminder_num = int(message_lower)
        if user and user.get('bizChatToken') and user.get('bizChatVendorUID'):
            delete_msg = await delete_from_search_context(user_id, reminder_num)
            if delete_msg:
                await send_whatsapp_reply(clean_phone, delete_msg, user['bizChatToken'], user['bizChatVendorUID'])
                return {"status": "success", "action": "delete_from_search", "number": reminder_num}

    # Handle natural language cancel
    cancel_patterns = [
        r'^(delete|cancel|cancle|remove)\s+(?:reminders?\s+)?(?:to\s+)?(.+)$',
        r'^(?:please\s+)?(delete|cancel|cancle|remove)\s+(.+)$',
    ]
    for pattern in cancel_patterns:
        cancel_name_match = re.match(pattern, message_lower)
        if cancel_name_match:
            search_text = cancel_name_match.group(2).strip()
            search_text = re.sub(r'^(the\s+|my\s+|reminder\s+to\s+|reminder\s+for\s+)', '', search_text)
            if search_text and search_text not in ['all', 'all reminders', 'everything', 'all my reminders']:
                if user and user.get('bizChatToken') and user.get('bizChatVendorUID'):
                    delete_msg = await delete_reminder_by_name(user_id, search_text, user_timezone, clean_phone)
                    await send_whatsapp_reply(clean_phone, delete_msg, user['bizChatToken'], user['bizChatVendorUID'])
                return {"status": "success", "action": "delete_by_name", "search": search_text}
            break

    # For creating reminders, we need the OpenAI API key
    if not settings or not settings.get('openaiApiKey'):
        if user and user.get('bizChatToken') and user.get('bizChatVendorUID'):
            await send_whatsapp_reply(
                clean_phone,
                "⚠️ Reminder bot is not fully configured. Please set up your OpenAI API key in the dashboard.\n\n💡 You can still use:\n• \"show reminders\" - View your reminders\n• \"help\" - See available commands",
                user['bizChatToken'], user['bizChatVendorUID']
            )
        return {"status": "error", "reason": "no API key configured"}

    # Parse the message using OpenAI
    parsed = await parse_reminder_from_message(message_text, user_timezone, settings['openaiApiKey'])

    if not parsed.get('is_reminder', False):
        logger.info(f"Message from {clean_phone} was not a reminder request, ignoring")
        return {"status": "ignored", "reason": "not a reminder request"}

    # Create the reminder
    try:
        scheduled_dt = datetime.fromisoformat(parsed['scheduled_time'])
    except Exception:
        scheduled_dt = datetime.now(timezone.utc)

    recurrence_data = parsed.get('recurrence', {})
    recurrence_config = None
    if recurrence_data and recurrence_data.get('type') != 'none':
        recurrence_config = RecurrenceConfig(
            type=RecurrenceType(recurrence_data.get('type', 'none')),
            interval=recurrence_data.get('interval', 1),
            weekdays=recurrence_data.get('weekdays', [])
        )

    reminder = Reminder(
        userId=user_id,
        numberId=number_record['id'],
        phone=clean_phone,
        contactName=number_record['name'],
        title=parsed.get('title', 'Reminder')[:50],
        message=parsed.get('message', message_text),
        originalInput=message_text,
        scheduledAt=scheduled_dt,
        timezone=user_timezone,
        recurrence=recurrence_config,
        useTemplate=True if settings.get('defaultTemplateId') else False,
        templateId=settings.get('defaultTemplateId')
    )

    reminder_dict = reminder.model_dump()
    reminder_dict['createdAt'] = reminder_dict['createdAt'].isoformat()
    reminder_dict['updatedAt'] = reminder_dict['updatedAt'].isoformat()
    reminder_dict['scheduledAt'] = reminder_dict['scheduledAt'].isoformat()
    if reminder_dict.get('recurrence'):
        reminder_dict['recurrence'] = {
            'type': reminder_dict['recurrence']['type'].value if hasattr(reminder_dict['recurrence']['type'], 'value') else reminder_dict['recurrence']['type'],
            'interval': reminder_dict['recurrence']['interval'],
            'weekdays': reminder_dict['recurrence']['weekdays']
        }

    await db.reminders.insert_one(reminder_dict)
    logger.info(f"Created reminder from WhatsApp: {reminder.id}")

    # Send confirmation
    if user and user.get('bizChatToken') and user.get('bizChatVendorUID'):
        import pytz
        tz = pytz.timezone(user_timezone)
        local_time = scheduled_dt.astimezone(tz)
        formatted_time = local_time.strftime("%I:%M %p").lstrip('0')
        formatted_date = local_time.strftime("%d %b %Y")

        recurrence_text = ""
        if recurrence_config and recurrence_config.type != RecurrenceType.NONE:
            if recurrence_config.type == RecurrenceType.DAILY:
                recurrence_text = "\n🔄 Repeats: Daily"
            elif recurrence_config.type == RecurrenceType.WEEKLY:
                if recurrence_config.weekdays:
                    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
                    day_names = [days[d] for d in recurrence_config.weekdays]
                    recurrence_text = f"\n🔄 Repeats: Every {', '.join(day_names)}"
                else:
                    recurrence_text = "\n🔄 Repeats: Weekly"
            elif recurrence_config.type == RecurrenceType.MONTHLY:
                recurrence_text = "\n🔄 Repeats: Monthly"
            elif recurrence_config.type == RecurrenceType.CUSTOM:
                recurrence_text = f"\n🔄 Repeats: Every {recurrence_config.interval} days"

        confirmation = f"""✅ *Reminder Set!*

📝 {parsed.get('message', message_text)}

⏰ {formatted_time}
📅 {formatted_date}{recurrence_text}

I'll remind you at the scheduled time!

_- Your WhatsApp Assistant_"""

        await send_whatsapp_reply(clean_phone, confirmation, user['bizChatToken'], user['bizChatVendorUID'])

    return {
        "status": "success",
        "reminder_id": reminder.id,
        "scheduled_at": reminder_dict['scheduledAt'],
        "recurrence": recurrence_data if recurrence_data else None
    }


# === 3. FUTURE FEATURES can be added to process_user_message above ===
