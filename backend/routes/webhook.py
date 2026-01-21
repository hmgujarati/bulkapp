"""Webhook handler for incoming WhatsApp messages"""
from fastapi import APIRouter, HTTPException, Request
from datetime import datetime, timezone, timedelta
from typing import Optional
import logging
import json
import httpx
import pytz

from models.reminder_schemas import Reminder, ReminderStatus
from utils.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["Webhook"])


# Commands that users can send via WhatsApp
LIST_COMMANDS = ['show reminders', 'list reminders', 'my reminders', 'reminders', 'show my reminders', 'pending reminders']
HELP_COMMANDS = ['help', 'commands', 'what can you do', '?']
DELETE_COMMANDS = ['delete all', 'clear reminders', 'cancel all']


async def get_reminders_list(user_id: str, user_timezone: str) -> str:
    """Get formatted list of user's reminders"""
    tz = pytz.timezone(user_timezone)
    now = datetime.now(tz)
    
    # Get pending reminders
    reminders = await db.reminders.find({
        "userId": user_id,
        "status": "pending"
    }).sort("scheduledAt", 1).to_list(20)
    
    if not reminders:
        return """📋 *Your Reminders*

You have no pending reminders.

💡 To create a reminder, just send:
"Remind me to call John at 3pm tomorrow"

_- Your WhatsApp Assistant_"""
    
    # Format the list
    reminder_list = []
    for i, r in enumerate(reminders, 1):
        try:
            scheduled_dt = datetime.fromisoformat(r['scheduledAt'].replace('Z', '+00:00'))
            local_time = scheduled_dt.astimezone(tz)
            time_str = local_time.strftime("%I:%M %p, %d %b").lstrip('0')
        except:
            time_str = "Unknown time"
        
        reminder_list.append(f"{i}. {r.get('title', 'Reminder')}\n   ⏰ {time_str}")
    
    reminders_text = "\n\n".join(reminder_list)
    
    return f"""📋 *Your Pending Reminders*

{reminders_text}

━━━━━━━━━━━━━━━
📝 Total: {len(reminders)} reminder(s)

💡 Commands:
• "show reminders" - View this list
• "help" - See all commands

_- Your WhatsApp Assistant_"""


async def get_help_message() -> str:
    """Get help message with available commands"""
    return """🤖 *WhatsApp Reminder Bot*

Here's what I can do:

📌 *Create Reminders*
Just send a message like:
• "Remind me to call John at 3pm"
• "Meeting with boss tomorrow at 10am"
• "Take medicine in 2 hours"

📋 *View Reminders*
• "show reminders"
• "my reminders"
• "list reminders"

❓ *Get Help*
• "help"
• "commands"

━━━━━━━━━━━━━━━
💡 Tip: I understand natural language, so just tell me what you need!

_- Your WhatsApp Assistant_"""


async def parse_reminder_from_message(message: str, user_timezone: str, api_key: str) -> dict:
    """Parse natural language message using OpenAI"""
    import pytz
    
    tz = pytz.timezone(user_timezone)
    now = datetime.now(tz)
    
    system_prompt = f"""You are a reminder parsing assistant. Parse the user's WhatsApp message and extract reminder details.

Current date/time in user's timezone ({user_timezone}): {now.strftime('%Y-%m-%d %H:%M:%S %Z')}

IMPORTANT:
- Extract what the user wants to be reminded about
- Parse the time/date mentioned
- "tomorrow" means the next day
- "today" means today
- If no specific time is given, default to 9:00 AM
- Return times in ISO 8601 format with timezone offset

Respond ONLY with a JSON object:
{{"title": "Short title (max 50 chars)", "message": "Full reminder message", "scheduled_time": "2025-01-22T10:00:00+05:30", "confidence": 0.95, "is_reminder": true}}

If the message is NOT a reminder request (just a greeting or random message), return:
{{"is_reminder": false, "reply": "Your suggested reply to the user"}}
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
    """Handle incoming WhatsApp messages from BizChat"""
    try:
        # Get the raw body
        body = await request.json()
        logger.info(f"Received webhook: {json.dumps(body)[:500]}")
        
        # BizChat webhook format:
        # {
        #   "contact": {"phone_number": "918200663263", "first_name": "...", ...},
        #   "message": {"body": "message text", "is_new_message": true, ...}
        # }
        
        # Extract phone number - try multiple possible locations
        phone = None
        if 'contact' in body and body['contact']:
            phone = body['contact'].get('phone_number')
        if not phone:
            phone = body.get('phone_number') or body.get('from') or body.get('sender')
        
        # Extract message text - try multiple possible locations
        message_text = None
        if 'message' in body and body['message']:
            message_text = body['message'].get('body') or body['message'].get('text')
        if not message_text:
            message_text = body.get('message') or body.get('text') or body.get('body') or body.get('message_body')
        
        # Check if it's a new message (ignore status updates)
        is_new_message = True
        if 'message' in body and body['message']:
            is_new_message = body['message'].get('is_new_message', True)
        
        if not phone or not message_text:
            logger.warning(f"Missing phone or message in webhook data")
            return {"status": "ignored", "reason": "missing phone or message"}
        
        if not is_new_message:
            logger.info(f"Ignoring non-new message (status update)")
            return {"status": "ignored", "reason": "not a new message"}
        
        # Clean phone number
        clean_phone = '+' + str(phone).replace('+', '').replace('-', '').replace(' ', '')
        
        logger.info(f"Processing incoming message from {clean_phone}: {message_text}")
        
        # Find the user associated with this phone number (check reminder_numbers)
        number_record = await db.reminder_numbers.find_one({"phone": clean_phone})
        
        if not number_record:
            # Try without + prefix
            number_record = await db.reminder_numbers.find_one({"phone": phone.replace('-', '').replace(' ', '')})
        
        if not number_record:
            logger.info(f"Phone {clean_phone} not registered for reminders")
            return {"status": "ignored", "reason": "phone not registered"}
        
        user_id = number_record['userId']
        user_timezone = number_record.get('timezone', 'Asia/Kolkata')
        
        # Get user's settings (OpenAI key) and BizChat credentials
        settings = await db.reminder_settings.find_one({"userId": user_id})
        user = await db.users.find_one({"id": user_id})
        
        if not settings or not settings.get('openaiApiKey'):
            logger.warning(f"User {user_id} has no OpenAI API key configured")
            # Send reply if possible
            if user and user.get('bizChatToken') and user.get('bizChatVendorUID'):
                await send_whatsapp_reply(
                    clean_phone,
                    "⚠️ Reminder bot is not fully configured. Please set up your OpenAI API key in the dashboard.",
                    user['bizChatToken'],
                    user['bizChatVendorUID']
                )
            return {"status": "error", "reason": "no API key configured"}
        
        # Parse the message using OpenAI
        parsed = await parse_reminder_from_message(
            message_text,
            user_timezone,
            settings['openaiApiKey']
        )
        
        # Check if it's a reminder request
        if not parsed.get('is_reminder', False):
            # Send a reply if it's not a reminder
            if user and user.get('bizChatToken') and user.get('bizChatVendorUID'):
                reply = parsed.get('reply', "Hi! Send me a reminder request like 'Remind me to call John at 3pm tomorrow'")
                await send_whatsapp_reply(
                    clean_phone,
                    reply,
                    user['bizChatToken'],
                    user['bizChatVendorUID']
                )
            return {"status": "replied", "is_reminder": False}
        
        # Create the reminder
        try:
            scheduled_dt = datetime.fromisoformat(parsed['scheduled_time'])
        except:
            scheduled_dt = datetime.now(timezone.utc)
        
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
            useTemplate=False,
            templateId=settings.get('defaultTemplateId')
        )
        
        reminder_dict = reminder.model_dump()
        reminder_dict['createdAt'] = reminder_dict['createdAt'].isoformat()
        reminder_dict['updatedAt'] = reminder_dict['updatedAt'].isoformat()
        reminder_dict['scheduledAt'] = reminder_dict['scheduledAt'].isoformat()
        
        await db.reminders.insert_one(reminder_dict)
        logger.info(f"Created reminder from WhatsApp: {reminder.id}")
        
        # Send confirmation
        if user and user.get('bizChatToken') and user.get('bizChatVendorUID'):
            # Format the scheduled time nicely
            import pytz
            tz = pytz.timezone(user_timezone)
            local_time = scheduled_dt.astimezone(tz)
            formatted_time = local_time.strftime("%I:%M %p").lstrip('0')
            formatted_date = local_time.strftime("%d %b %Y")
            
            confirmation = f"""✅ *Reminder Set!*

📝 {parsed.get('message', message_text)}

⏰ {formatted_time}
📅 {formatted_date}

I'll remind you at the scheduled time!

_- Your WhatsApp Assistant_"""
            
            await send_whatsapp_reply(
                clean_phone,
                confirmation,
                user['bizChatToken'],
                user['bizChatVendorUID']
            )
        
        return {
            "status": "success",
            "reminder_id": reminder.id,
            "scheduled_at": reminder_dict['scheduledAt']
        }
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}


@router.get("/bizchat")
async def verify_webhook(request: Request):
    """Verify webhook endpoint (some services require GET for verification)"""
    # Return challenge if provided
    params = dict(request.query_params)
    if 'challenge' in params:
        return {"challenge": params['challenge']}
    if 'hub.challenge' in params:
        return int(params['hub.challenge'])
    return {"status": "ok", "message": "Webhook endpoint active"}
