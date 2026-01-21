"""Reminders management routes"""
from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timezone, timedelta
from typing import Optional
import logging
import json
import httpx
import pytz

from models.reminder_schemas import (
    Reminder, ReminderCreate, ReminderCreateDirect, ReminderUpdate,
    ReminderStatus, ReminderSettings, ReminderSettingsUpdate, ParsedReminder
)
from utils.auth import get_current_user
from utils.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reminders", tags=["Reminders"])


async def parse_natural_language_reminder(
    input_text: str,
    user_timezone: str,
    api_key: str
) -> ParsedReminder:
    """Parse natural language input using OpenAI GPT-3.5-Turbo"""
    
    # Get current time in user's timezone
    tz = pytz.timezone(user_timezone)
    now = datetime.now(tz)
    
    system_prompt = f"""You are a reminder parsing assistant. Parse the user's reminder request and extract:
1. title: A short summary (max 50 chars)
2. message: The full reminder message
3. scheduled_time: When to send the reminder in ISO format

Current date/time in user's timezone ({user_timezone}): {now.strftime('%Y-%m-%d %H:%M:%S %Z')}

IMPORTANT:
- Always interpret times relative to the current date/time
- "tomorrow" means the next day
- "today" means today
- If no specific time is given, default to 9:00 AM
- Return times in ISO 8601 format with the user's timezone offset

Respond ONLY with a JSON object like this:
{{"title": "Short title", "message": "Full reminder message", "scheduled_time": "2025-01-22T10:00:00+05:30", "confidence": 0.95}}
"""

    user_prompt = f"Parse this reminder request: {input_text}"
    
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
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 200
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                logger.error(f"OpenAI API error: {response.text}")
                raise HTTPException(
                    status_code=500, 
                    detail="Failed to parse reminder. Please check your OpenAI API key."
                )
            
            data = response.json()
            content = data['choices'][0]['message']['content']
            
            # Parse the JSON response
            try:
                parsed = json.loads(content)
                scheduled_dt = datetime.fromisoformat(parsed['scheduled_time'])
                
                return ParsedReminder(
                    title=parsed['title'][:50],
                    message=parsed['message'],
                    scheduledAt=scheduled_dt,
                    confidence=parsed.get('confidence', 0.8)
                )
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.error(f"Failed to parse OpenAI response: {content}, error: {e}")
                raise HTTPException(
                    status_code=400,
                    detail="Could not understand the reminder. Please try a clearer format like 'remind me to call John at 10am tomorrow'"
                )
                
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="OpenAI request timed out")
    except Exception as e:
        logger.error(f"Error calling OpenAI: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error parsing reminder: {str(e)}")


@router.get("/settings")
async def get_reminder_settings(current_user = Depends(get_current_user)):
    """Get user's reminder settings"""
    settings = await db.reminder_settings.find_one(
        {"userId": current_user.userId},
        {"_id": 0}
    )
    
    if not settings:
        # Return default settings
        return {
            "userId": current_user.userId,
            "openaiApiKey": None,
            "hasApiKey": False,
            "defaultTemplateId": None
        }
    
    # Mask the API key for security
    return {
        "userId": settings['userId'],
        "openaiApiKey": "sk-...configured" if settings.get('openaiApiKey') else None,
        "hasApiKey": bool(settings.get('openaiApiKey')),
        "defaultTemplateId": settings.get('defaultTemplateId')
    }


@router.put("/settings")
async def update_reminder_settings(
    settings_data: ReminderSettingsUpdate,
    current_user = Depends(get_current_user)
):
    """Update user's reminder settings"""
    update_dict = {k: v for k, v in settings_data.model_dump().items() if v is not None}
    
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    update_dict['updatedAt'] = datetime.now(timezone.utc).isoformat()
    
    # Upsert settings
    await db.reminder_settings.update_one(
        {"userId": current_user.userId},
        {
            "$set": update_dict,
            "$setOnInsert": {
                "userId": current_user.userId,
                "createdAt": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )
    
    return {"message": "Settings updated successfully"}


@router.post("")
async def create_reminder(
    reminder_data: ReminderCreate,
    current_user = Depends(get_current_user)
):
    """Create a reminder using natural language parsing"""
    
    # Get user's settings
    settings = await db.reminder_settings.find_one({"userId": current_user.userId})
    if not settings or not settings.get('openaiApiKey'):
        raise HTTPException(
            status_code=400,
            detail="Please configure your OpenAI API key in settings first"
        )
    
    # Get the target number
    number = await db.reminder_numbers.find_one({
        "id": reminder_data.numberId,
        "userId": current_user.userId
    })
    if not number:
        raise HTTPException(status_code=404, detail="Phone number not found")
    
    # Parse the natural language input
    parsed = await parse_natural_language_reminder(
        reminder_data.naturalLanguageInput,
        number['timezone'],
        settings['openaiApiKey']
    )
    
    # Validate scheduled time is in the future
    now = datetime.now(timezone.utc)
    if parsed.scheduledAt.replace(tzinfo=timezone.utc) <= now:
        raise HTTPException(
            status_code=400,
            detail="Reminder time must be in the future"
        )
    
    # Create the reminder
    reminder = Reminder(
        userId=current_user.userId,
        numberId=reminder_data.numberId,
        phone=number['phone'],
        contactName=number['name'],
        title=parsed.title,
        message=parsed.message,
        originalInput=reminder_data.naturalLanguageInput,
        scheduledAt=parsed.scheduledAt,
        timezone=number['timezone'],
        useTemplate=reminder_data.useTemplate,
        templateId=reminder_data.templateId or settings.get('defaultTemplateId')
    )
    
    reminder_dict = reminder.model_dump()
    reminder_dict['createdAt'] = reminder_dict['createdAt'].isoformat()
    reminder_dict['updatedAt'] = reminder_dict['updatedAt'].isoformat()
    reminder_dict['scheduledAt'] = reminder_dict['scheduledAt'].isoformat()
    
    await db.reminders.insert_one(reminder_dict)
    
    return {
        "message": "Reminder created successfully",
        "reminderId": reminder.id,
        "reminder": {
            "id": reminder.id,
            "title": reminder.title,
            "message": reminder.message,
            "scheduledAt": reminder_dict['scheduledAt'],
            "phone": reminder.phone,
            "contactName": reminder.contactName,
            "confidence": parsed.confidence
        }
    }


@router.post("/direct")
async def create_reminder_direct(
    reminder_data: ReminderCreateDirect,
    current_user = Depends(get_current_user)
):
    """Create a reminder directly without NLP parsing"""
    
    # Get the target number
    number = await db.reminder_numbers.find_one({
        "id": reminder_data.numberId,
        "userId": current_user.userId
    })
    if not number:
        raise HTTPException(status_code=404, detail="Phone number not found")
    
    # Validate scheduled time is in the future
    now = datetime.now(timezone.utc)
    scheduled_utc = reminder_data.scheduledAt.replace(tzinfo=timezone.utc) if reminder_data.scheduledAt.tzinfo is None else reminder_data.scheduledAt
    if scheduled_utc <= now:
        raise HTTPException(
            status_code=400,
            detail="Reminder time must be in the future"
        )
    
    # Get default template from settings
    settings = await db.reminder_settings.find_one({"userId": current_user.userId})
    template_id = reminder_data.templateId or (settings.get('defaultTemplateId') if settings else None)
    
    # Create the reminder
    reminder = Reminder(
        userId=current_user.userId,
        numberId=reminder_data.numberId,
        phone=number['phone'],
        contactName=number['name'],
        title=reminder_data.title,
        message=reminder_data.message,
        originalInput=f"[Direct] {reminder_data.title}",
        scheduledAt=reminder_data.scheduledAt,
        timezone=number['timezone'],
        useTemplate=reminder_data.useTemplate,
        templateId=template_id
    )
    
    reminder_dict = reminder.model_dump()
    reminder_dict['createdAt'] = reminder_dict['createdAt'].isoformat()
    reminder_dict['updatedAt'] = reminder_dict['updatedAt'].isoformat()
    reminder_dict['scheduledAt'] = reminder_dict['scheduledAt'].isoformat()
    
    await db.reminders.insert_one(reminder_dict)
    
    return {
        "message": "Reminder created successfully",
        "reminderId": reminder.id,
        "reminder": {
            "id": reminder.id,
            "title": reminder.title,
            "message": reminder.message,
            "scheduledAt": reminder_dict['scheduledAt'],
            "phone": reminder.phone,
            "contactName": reminder.contactName
        }
    }


@router.get("")
async def get_reminders(
    filter: Optional[str] = Query("all", enum=["all", "today", "week", "pending", "sent", "failed"]),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    number_id: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """Get reminders with filtering options"""
    from models.schemas import Role
    
    # Admins can see all reminders, users only see their own
    if current_user.role == Role.ADMIN:
        query = {}  # Admin sees all
    else:
        query = {"userId": current_user.userId}
    
    # Apply filters
    now = datetime.now(timezone.utc)
    
    if filter == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        query["scheduledAt"] = {"$gte": start.isoformat(), "$lt": end.isoformat()}
    elif filter == "week":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
        query["scheduledAt"] = {"$gte": start.isoformat(), "$lt": end.isoformat()}
    elif filter == "pending":
        query["status"] = ReminderStatus.PENDING.value
    elif filter == "sent":
        query["status"] = ReminderStatus.SENT.value
    elif filter == "failed":
        query["status"] = ReminderStatus.FAILED.value
    
    # Custom date range (max 15 days)
    if start_date and end_date:
        try:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            
            if (end - start).days > 15:
                raise HTTPException(
                    status_code=400,
                    detail="Date range cannot exceed 15 days"
                )
            
            query["scheduledAt"] = {"$gte": start.isoformat(), "$lte": end.isoformat()}
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Filter by number
    if number_id:
        query["numberId"] = number_id
    
    reminders = await db.reminders.find(
        query,
        {"_id": 0}
    ).sort("scheduledAt", 1).to_list(200)
    
    return {"reminders": reminders, "count": len(reminders)}


@router.get("/{reminder_id}")
async def get_reminder(reminder_id: str, current_user = Depends(get_current_user)):
    """Get a specific reminder"""
    reminder = await db.reminders.find_one(
        {"id": reminder_id, "userId": current_user.userId},
        {"_id": 0}
    )
    
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    
    return reminder


@router.put("/{reminder_id}")
async def update_reminder(
    reminder_id: str,
    update_data: ReminderUpdate,
    current_user = Depends(get_current_user)
):
    """Update a pending reminder"""
    reminder = await db.reminders.find_one({
        "id": reminder_id,
        "userId": current_user.userId
    })
    
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    
    if reminder['status'] != ReminderStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail="Can only update pending reminders"
        )
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    # Validate scheduled time if provided
    if 'scheduledAt' in update_dict:
        scheduled_utc = update_dict['scheduledAt'].replace(tzinfo=timezone.utc) if update_dict['scheduledAt'].tzinfo is None else update_dict['scheduledAt']
        if scheduled_utc <= datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Reminder time must be in the future")
        update_dict['scheduledAt'] = update_dict['scheduledAt'].isoformat()
    
    update_dict['updatedAt'] = datetime.now(timezone.utc).isoformat()
    
    await db.reminders.update_one(
        {"id": reminder_id},
        {"$set": update_dict}
    )
    
    return {"message": "Reminder updated successfully"}


@router.delete("/{reminder_id}")
async def delete_reminder(reminder_id: str, current_user = Depends(get_current_user)):
    """Delete/cancel a reminder"""
    reminder = await db.reminders.find_one({
        "id": reminder_id,
        "userId": current_user.userId
    })
    
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    
    # If pending, we can delete it
    if reminder['status'] == ReminderStatus.PENDING.value:
        await db.reminders.delete_one({"id": reminder_id})
        return {"message": "Reminder deleted successfully"}
    
    # If already sent/failed, just mark as cancelled for history
    await db.reminders.update_one(
        {"id": reminder_id},
        {"$set": {"status": ReminderStatus.CANCELLED.value, "updatedAt": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Reminder cancelled successfully"}
