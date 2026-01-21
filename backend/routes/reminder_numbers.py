"""Reminder Numbers management routes"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import List
import re

from models.reminder_schemas import (
    ReminderNumber, ReminderNumberCreate, ReminderNumberUpdate
)
from utils.auth import get_current_user
from utils.database import db

router = APIRouter(prefix="/reminder-numbers", tags=["Reminder Numbers"])

# Valid timezone list (common ones)
VALID_TIMEZONES = [
    "Asia/Kolkata", "Asia/Dubai", "Asia/Singapore", "Asia/Tokyo", "Asia/Shanghai",
    "Asia/Hong_Kong", "Asia/Seoul", "Asia/Jakarta", "Asia/Manila", "Asia/Bangkok",
    "Europe/London", "Europe/Paris", "Europe/Berlin", "Europe/Moscow", "Europe/Rome",
    "America/New_York", "America/Los_Angeles", "America/Chicago", "America/Denver",
    "America/Toronto", "America/Sao_Paulo", "America/Mexico_City",
    "Australia/Sydney", "Australia/Melbourne", "Australia/Perth",
    "Pacific/Auckland", "Africa/Cairo", "Africa/Lagos", "UTC"
]


def normalize_phone(phone: str) -> str:
    """Normalize phone number to E.164 format"""
    # Remove all non-digit characters except +
    phone = re.sub(r'[^\d+]', '', phone)
    # Ensure it starts with +
    if not phone.startswith('+'):
        phone = '+' + phone
    return phone


@router.post("")
async def create_reminder_number(
    number_data: ReminderNumberCreate,
    current_user = Depends(get_current_user)
):
    """Add a new phone number for reminders"""
    # Validate timezone
    if number_data.timezone not in VALID_TIMEZONES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid timezone. Valid options include: {', '.join(VALID_TIMEZONES[:10])}..."
        )
    
    # Normalize phone number
    phone = normalize_phone(number_data.phone)
    
    # Check if number already exists for this user
    existing = await db.reminder_numbers.find_one({
        "userId": current_user.userId,
        "phone": phone
    })
    if existing:
        raise HTTPException(status_code=400, detail="This phone number is already added")
    
    # If setting as default, unset other defaults
    if number_data.isDefault:
        await db.reminder_numbers.update_many(
            {"userId": current_user.userId, "isDefault": True},
            {"$set": {"isDefault": False}}
        )
    
    # Create the number
    reminder_number = ReminderNumber(
        userId=current_user.userId,
        phone=phone,
        name=number_data.name,
        timezone=number_data.timezone,
        isDefault=number_data.isDefault
    )
    
    number_dict = reminder_number.model_dump()
    number_dict['createdAt'] = number_dict['createdAt'].isoformat()
    number_dict['updatedAt'] = number_dict['updatedAt'].isoformat()
    
    await db.reminder_numbers.insert_one(number_dict)
    
    return {
        "message": "Phone number added successfully",
        "numberId": reminder_number.id,
        "number": {
            "id": reminder_number.id,
            "phone": phone,
            "name": number_data.name,
            "timezone": number_data.timezone,
            "isDefault": number_data.isDefault
        }
    }


@router.get("")
async def get_reminder_numbers(current_user = Depends(get_current_user)):
    """Get all reminder numbers for the current user"""
    numbers = await db.reminder_numbers.find(
        {"userId": current_user.userId},
        {"_id": 0}
    ).sort("createdAt", -1).to_list(100)
    
    return {"numbers": numbers}


@router.get("/timezones")
async def get_available_timezones():
    """Get list of available timezones"""
    return {"timezones": VALID_TIMEZONES}


@router.get("/{number_id}")
async def get_reminder_number(number_id: str, current_user = Depends(get_current_user)):
    """Get a specific reminder number"""
    number = await db.reminder_numbers.find_one(
        {"id": number_id, "userId": current_user.userId},
        {"_id": 0}
    )
    
    if not number:
        raise HTTPException(status_code=404, detail="Number not found")
    
    return number


@router.put("/{number_id}")
async def update_reminder_number(
    number_id: str,
    update_data: ReminderNumberUpdate,
    current_user = Depends(get_current_user)
):
    """Update a reminder number"""
    # Check ownership
    number = await db.reminder_numbers.find_one({
        "id": number_id, 
        "userId": current_user.userId
    })
    if not number:
        raise HTTPException(status_code=404, detail="Number not found")
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    # Validate timezone if provided
    if 'timezone' in update_dict and update_dict['timezone'] not in VALID_TIMEZONES:
        raise HTTPException(status_code=400, detail="Invalid timezone")
    
    # If setting as default, unset other defaults
    if update_dict.get('isDefault'):
        await db.reminder_numbers.update_many(
            {"userId": current_user.userId, "isDefault": True, "id": {"$ne": number_id}},
            {"$set": {"isDefault": False}}
        )
    
    update_dict['updatedAt'] = datetime.now(timezone.utc).isoformat()
    
    await db.reminder_numbers.update_one(
        {"id": number_id},
        {"$set": update_dict}
    )
    
    return {"message": "Number updated successfully"}


@router.delete("/{number_id}")
async def delete_reminder_number(number_id: str, current_user = Depends(get_current_user)):
    """Delete a reminder number"""
    # Check ownership
    number = await db.reminder_numbers.find_one({
        "id": number_id, 
        "userId": current_user.userId
    })
    if not number:
        raise HTTPException(status_code=404, detail="Number not found")
    
    # Check if there are pending reminders for this number
    pending_count = await db.reminders.count_documents({
        "numberId": number_id,
        "status": "pending"
    })
    
    if pending_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete number with {pending_count} pending reminders. Cancel them first."
        )
    
    # Delete the number
    await db.reminder_numbers.delete_one({"id": number_id})
    
    return {"message": "Number deleted successfully"}
