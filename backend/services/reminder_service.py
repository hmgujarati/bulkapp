"""Reminder sending service"""
from datetime import datetime, timezone
from typing import Dict, Any
import httpx
import logging
import os
import pytz

from utils.database import db
from models.reminder_schemas import ReminderStatus

logger = logging.getLogger(__name__)

BIZCHAT_API_BASE = os.environ.get('BIZCHAT_API_BASE', 'https://bizchatapi.in/api')


def format_reminder_message(title: str, message: str, scheduled_time: str, recipient_timezone: str) -> str:
    """Format reminder message to be professional and visually appealing"""
    try:
        # Parse the scheduled time
        scheduled_dt = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
        
        # Convert to recipient's timezone
        tz = pytz.timezone(recipient_timezone)
        local_time = scheduled_dt.astimezone(tz)
        
        # Format time nicely (e.g., "4:30 PM")
        formatted_time = local_time.strftime("%I:%M %p").lstrip('0')
        formatted_date = local_time.strftime("%d %b %Y")
    except:
        formatted_time = "your scheduled time"
        formatted_date = ""
    
    # Build the professional message
    formatted_message = f"""🔔 *Reminder Alert*

✨ {message}

⏰ Scheduled: {formatted_time}
📅 {formatted_date}

_- Your WhatsApp Assistant_"""
    
    return formatted_message


async def send_reminder_message(
    phone: str,
    message: str,
    template_id: str,
    token: str,
    vendor_uid: str,
    use_template: bool = True,
    scheduled_time: str = None,
    recipient_timezone: str = "Asia/Kolkata",
    title: str = None
) -> Dict[str, Any]:
    """Send a reminder message via BizChat API"""
    try:
        async with httpx.AsyncClient() as client:
            # Clean phone number
            clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
            
            # Format the message professionally
            formatted_message = format_reminder_message(
                title=title or "Reminder",
                message=message,
                scheduled_time=scheduled_time or datetime.now(timezone.utc).isoformat(),
                recipient_timezone=recipient_timezone
            )
            
            if use_template and template_id:
                # Use pre-approved template
                url = f"{BIZCHAT_API_BASE}/{vendor_uid}/contact/send-template-message?token={token}"
                payload = {
                    "phone_number": clean_phone,
                    "template_name": template_id,
                    "template_language": "en",
                    "field_1": formatted_message
                }
            else:
                # Use session message (24-hour window) - direct text
                url = f"{BIZCHAT_API_BASE}/{vendor_uid}/contact/send-message?token={token}"
                payload = {
                    "phone_number": clean_phone,
                    "message_body": formatted_message
                }
            
            logger.info(f"Sending reminder to {phone}")
            
            response = await client.post(url, json=payload, timeout=30.0)
            
            if response.status_code in [200, 201]:
                data = response.json()
                return {"success": True, "data": data}
            else:
                error_msg = f"BizChat API Error: Status {response.status_code}, Response: {response.text}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
                
    except Exception as e:
        error_msg = f"Exception sending reminder: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}


async def process_due_reminders():
    """Process all due reminders"""
    now = datetime.now(timezone.utc)
    
    # Find all pending reminders that are due
    due_reminders = await db.reminders.find({
        "status": ReminderStatus.PENDING.value,
        "scheduledAt": {"$lte": now.isoformat()}
    }).to_list(100)
    
    if not due_reminders:
        return
    
    logger.info(f"Processing {len(due_reminders)} due reminders")
    
    for reminder in due_reminders:
        try:
            # Get user's BizChat credentials
            user = await db.users.find_one({"id": reminder['userId']})
            
            if not user or not user.get('bizChatToken') or not user.get('bizChatVendorUID'):
                logger.error(f"User {reminder['userId']} missing BizChat credentials")
                await db.reminders.update_one(
                    {"id": reminder['id']},
                    {
                        "$set": {
                            "status": ReminderStatus.FAILED.value,
                            "error": "BizChat credentials not configured",
                            "updatedAt": now.isoformat()
                        }
                    }
                )
                continue
            
            # Send the reminder
            result = await send_reminder_message(
                phone=reminder['phone'],
                message=reminder['message'],
                template_id=reminder.get('templateId'),
                token=user['bizChatToken'],
                vendor_uid=user['bizChatVendorUID'],
                use_template=reminder.get('useTemplate', True)
            )
            
            if result['success']:
                await db.reminders.update_one(
                    {"id": reminder['id']},
                    {
                        "$set": {
                            "status": ReminderStatus.SENT.value,
                            "sentAt": now.isoformat(),
                            "messageId": result.get('data', {}).get('message_id'),
                            "updatedAt": now.isoformat()
                        }
                    }
                )
                logger.info(f"Reminder {reminder['id']} sent successfully")
            else:
                await db.reminders.update_one(
                    {"id": reminder['id']},
                    {
                        "$set": {
                            "status": ReminderStatus.FAILED.value,
                            "error": result.get('error', 'Unknown error'),
                            "updatedAt": now.isoformat()
                        }
                    }
                )
                logger.error(f"Reminder {reminder['id']} failed: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Error processing reminder {reminder['id']}: {str(e)}")
            await db.reminders.update_one(
                {"id": reminder['id']},
                {
                    "$set": {
                        "status": ReminderStatus.FAILED.value,
                        "error": str(e),
                        "updatedAt": now.isoformat()
                    }
                }
            )
