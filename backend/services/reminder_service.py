"""Reminder sending service"""
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
import httpx
import logging
import os
import pytz
import uuid

from utils.database import db
from models.reminder_schemas import ReminderStatus, RecurrenceType

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
                    "template_language": "en_US",
                    "field_1": message,
                    "field_2": "",
                    "field_3": ""
                }
                
                # Try to extract time and date for template fields
                try:
                    scheduled_dt = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
                    tz = pytz.timezone(recipient_timezone)
                    local_time = scheduled_dt.astimezone(tz)
                    payload["field_2"] = local_time.strftime("%I:%M %p").lstrip('0')
                    payload["field_3"] = local_time.strftime("%d %b %Y")
                except:
                    pass
            else:
                # Use session message (24-hour window) - direct text
                url = f"{BIZCHAT_API_BASE}/{vendor_uid}/contact/send-message?token={token}"
                payload = {
                    "phone_number": clean_phone,
                    "message_body": formatted_message
                }
            
            logger.info(f"Sending reminder to {phone}, URL: {url}")
            logger.info(f"Payload: {payload}")
            
            response = await client.post(url, json=payload, timeout=30.0)
            response_text = response.text
            
            logger.info(f"BizChat Response Status: {response.status_code}")
            logger.info(f"BizChat Response Body: {response_text}")
            
            # Parse response
            try:
                data = response.json()
            except:
                data = {"raw_response": response_text}
            
            # Check for success - BizChat API may return 200 but with error in body
            if response.status_code in [200, 201]:
                # Check if response indicates actual success
                # Common patterns: {"success": true}, {"status": "sent"}, {"message_id": "xxx"}
                is_success = False
                error_in_response = None
                
                if isinstance(data, dict):
                    # Check for explicit success indicators
                    if data.get('success') == True:
                        is_success = True
                    elif data.get('status') in ['sent', 'queued', 'delivered']:
                        is_success = True
                    elif data.get('message_id') or data.get('messageId'):
                        is_success = True
                    elif data.get('id'):
                        is_success = True
                    # Check for error indicators even with 200 status
                    elif data.get('error'):
                        error_in_response = data.get('error')
                    elif data.get('message') and 'error' in str(data.get('message', '')).lower():
                        error_in_response = data.get('message')
                    elif data.get('success') == False:
                        error_in_response = data.get('message') or data.get('error') or str(data)
                    else:
                        # Assume success if no error indicators and status is 200
                        is_success = True
                
                if is_success:
                    return {"success": True, "data": data, "response_code": response.status_code}
                else:
                    error_msg = f"API returned 200 but message may not be sent. Response: {error_in_response or response_text[:500]}"
                    logger.warning(error_msg)
                    return {"success": False, "error": error_msg, "response_code": response.status_code, "data": data}
            else:
                error_msg = f"HTTP {response.status_code}: {response_text[:500]}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg, "response_code": response.status_code}
                
    except httpx.TimeoutException:
        error_msg = "Request timeout - BizChat API did not respond in 30 seconds"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}
    except httpx.ConnectError as e:
        error_msg = f"Connection error to BizChat API: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = f"Exception: {type(e).__name__}: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}


def calculate_next_occurrence(current_scheduled: datetime, recurrence: dict, user_timezone: str) -> datetime:
    """Calculate the next occurrence for a recurring reminder"""
    recurrence_type = recurrence.get('type', 'none')
    interval = recurrence.get('interval', 1)
    weekdays = recurrence.get('weekdays', [])
    
    tz = pytz.timezone(user_timezone)
    current_local = current_scheduled.astimezone(tz)
    
    if recurrence_type == 'daily':
        next_time = current_local + timedelta(days=interval)
    
    elif recurrence_type == 'weekly':
        if weekdays:
            # Find next matching weekday
            next_time = current_local + timedelta(days=1)
            days_checked = 0
            while days_checked < 14:  # Max 2 weeks search
                if next_time.weekday() in weekdays:
                    break
                next_time += timedelta(days=1)
                days_checked += 1
        else:
            next_time = current_local + timedelta(weeks=interval)
    
    elif recurrence_type == 'monthly':
        # Add month(s)
        month = current_local.month + interval
        year = current_local.year
        while month > 12:
            month -= 12
            year += 1
        # Handle day overflow (e.g., Jan 31 -> Feb 28)
        day = min(current_local.day, 28)  # Safe day for all months
        next_time = current_local.replace(year=year, month=month, day=day)
    
    elif recurrence_type == 'custom':
        # Custom interval in days
        next_time = current_local + timedelta(days=interval)
    
    else:
        return None
    
    return next_time


async def create_next_recurring_reminder(reminder: dict) -> bool:
    """Create the next occurrence for a recurring reminder"""
    recurrence = reminder.get('recurrence')
    if not recurrence or recurrence.get('type') == 'none':
        return False
    
    # Parse current scheduled time
    scheduled_str = reminder.get('scheduledAt', '')
    try:
        current_scheduled = datetime.fromisoformat(scheduled_str.replace('Z', '+00:00'))
    except:
        logger.error(f"Failed to parse scheduled time for recurring reminder {reminder['id']}")
        return False
    
    # Calculate next occurrence
    next_scheduled = calculate_next_occurrence(
        current_scheduled, 
        recurrence, 
        reminder.get('timezone', 'Asia/Kolkata')
    )
    
    if not next_scheduled:
        return False
    
    now = datetime.now(timezone.utc)
    
    # Create new reminder
    new_reminder = {
        "id": str(uuid.uuid4()),
        "userId": reminder['userId'],
        "numberId": reminder['numberId'],
        "phone": reminder['phone'],
        "contactName": reminder['contactName'],
        "title": reminder['title'],
        "message": reminder['message'],
        "originalInput": reminder.get('originalInput', ''),
        "scheduledAt": next_scheduled.isoformat(),
        "timezone": reminder.get('timezone', 'Asia/Kolkata'),
        "status": ReminderStatus.PENDING.value,
        "recurrence": recurrence,
        "parentReminderId": reminder.get('parentReminderId') or reminder['id'],
        "useTemplate": reminder.get('useTemplate', True),
        "templateId": reminder.get('templateId'),
        "createdAt": now.isoformat(),
        "updatedAt": now.isoformat()
    }
    
    await db.reminders.insert_one(new_reminder)
    logger.info(f"Created next recurring reminder {new_reminder['id']} scheduled for {next_scheduled}")
    return True


async def process_due_reminders():
    """Process all due reminders"""
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    
    # Find all pending reminders
    pending_reminders = await db.reminders.find({
        "status": ReminderStatus.PENDING.value
    }).to_list(100)
    
    if not pending_reminders:
        return
    
    # Filter reminders that are due (handle timezone properly)
    due_reminders = []
    for reminder in pending_reminders:
        try:
            scheduled_str = reminder.get('scheduledAt', '')
            if scheduled_str:
                # Parse the scheduled time and convert to UTC for comparison
                scheduled_dt = datetime.fromisoformat(scheduled_str.replace('Z', '+00:00'))
                # Convert to UTC if it has timezone info
                if scheduled_dt.tzinfo:
                    scheduled_utc = scheduled_dt.astimezone(timezone.utc)
                else:
                    scheduled_utc = scheduled_dt.replace(tzinfo=timezone.utc)
                
                # Check if it's due
                if scheduled_utc <= now:
                    due_reminders.append(reminder)
        except Exception as e:
            logger.error(f"Error parsing scheduled time for reminder {reminder.get('id')}: {e}")
    
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
                use_template=reminder.get('useTemplate', True),
                scheduled_time=reminder.get('scheduledAt'),
                recipient_timezone=reminder.get('timezone', 'Asia/Kolkata'),
                title=reminder.get('title')
            )
            
            if result['success']:
                await db.reminders.update_one(
                    {"id": reminder['id']},
                    {
                        "$set": {
                            "status": ReminderStatus.SENT.value,
                            "sentAt": now.isoformat(),
                            "messageId": result.get('data', {}).get('message_id') or result.get('data', {}).get('id'),
                            "apiResponse": str(result.get('data', {}))[:500],
                            "responseCode": result.get('response_code'),
                            "updatedAt": now.isoformat()
                        }
                    }
                )
                logger.info(f"Reminder {reminder['id']} sent successfully")
                
                # Create next occurrence for recurring reminders
                if reminder.get('recurrence') and reminder['recurrence'].get('type') != 'none':
                    await create_next_recurring_reminder(reminder)
            else:
                # Store detailed error info
                error_details = result.get('error', 'Unknown error')
                response_code = result.get('response_code', 'N/A')
                api_data = str(result.get('data', {}))[:500] if result.get('data') else None
                
                full_error = f"[HTTP {response_code}] {error_details}"
                if api_data:
                    full_error += f"\nAPI Response: {api_data}"
                
                await db.reminders.update_one(
                    {"id": reminder['id']},
                    {
                        "$set": {
                            "status": ReminderStatus.FAILED.value,
                            "error": full_error,
                            "responseCode": response_code,
                            "updatedAt": now.isoformat()
                        }
                    }
                )
                logger.error(f"Reminder {reminder['id']} failed: {full_error}")
                
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
