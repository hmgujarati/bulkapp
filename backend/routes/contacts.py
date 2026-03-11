"""Contact management routes"""
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from datetime import datetime, timezone
from typing import Optional, List
import logging
import re

from models.contact_schemas import (
    Contact, ContactCreate, ContactUpdate, ContactBulkImport,
    ContactGroup, ContactGroupCreate, ContactGroupUpdate,
    AutoMessageSettings, AutoMessageSettingsUpdate
)
from utils.auth import get_current_user
from utils.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contacts", tags=["Contacts"])


def normalize_phone(phone: str, default_country_code: str = "+91") -> str:
    """Normalize phone number and add country code if missing"""
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    # If already has + at start, return as is
    if cleaned.startswith('+'):
        return cleaned
    
    # Remove leading zeros
    cleaned = cleaned.lstrip('0')
    
    # Check if it looks like it already has country code (10+ digits)
    # India numbers are 10 digits, with country code it's 12
    if len(cleaned) > 10:
        # Assume it has country code, just add +
        return f"+{cleaned}"
    
    # Add default country code
    default_code = default_country_code.replace('+', '')
    return f"+{default_code}{cleaned}"


# ==================== Contact Groups ====================

@router.get("/groups")
async def get_contact_groups(current_user=Depends(get_current_user)):
    """Get all contact groups for the user"""
    groups = await db.contact_groups.find(
        {"userId": current_user.userId},
        {"_id": 0}
    ).sort("name", 1).to_list(100)
    
    # Get contact count for each group
    for group in groups:
        count = await db.contacts.count_documents({
            "userId": current_user.userId,
            "groupId": group["id"]
        })
        group["contactCount"] = count
    
    return {"groups": groups}


@router.post("/groups")
async def create_contact_group(
    group_data: ContactGroupCreate,
    current_user=Depends(get_current_user)
):
    """Create a new contact group"""
    group = ContactGroup(
        userId=current_user.userId,
        name=group_data.name,
        description=group_data.description,
        color=group_data.color
    )
    
    group_dict = group.model_dump()
    group_dict['createdAt'] = group_dict['createdAt'].isoformat()
    group_dict['updatedAt'] = group_dict['updatedAt'].isoformat()
    
    await db.contact_groups.insert_one(group_dict)
    
    # Remove MongoDB _id before returning
    group_dict.pop('_id', None)
    
    return {"message": "Group created", "group": group_dict}


@router.put("/groups/{group_id}")
async def update_contact_group(
    group_id: str,
    group_data: ContactGroupUpdate,
    current_user=Depends(get_current_user)
):
    """Update a contact group"""
    existing = await db.contact_groups.find_one({
        "id": group_id,
        "userId": current_user.userId
    })
    
    if not existing:
        raise HTTPException(status_code=404, detail="Group not found")
    
    update_data = {k: v for k, v in group_data.model_dump().items() if v is not None}
    update_data['updatedAt'] = datetime.now(timezone.utc).isoformat()
    
    await db.contact_groups.update_one(
        {"id": group_id},
        {"$set": update_data}
    )
    
    # Update group name in contacts if name changed
    if group_data.name:
        await db.contacts.update_many(
            {"groupId": group_id},
            {"$set": {"groupName": group_data.name}}
        )
    
    return {"message": "Group updated"}


@router.delete("/groups/{group_id}")
async def delete_contact_group(
    group_id: str,
    current_user=Depends(get_current_user)
):
    """Delete a contact group (contacts in group will have groupId removed)"""
    result = await db.contact_groups.delete_one({
        "id": group_id,
        "userId": current_user.userId
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Remove group reference from contacts
    await db.contacts.update_many(
        {"groupId": group_id},
        {"$set": {"groupId": None, "groupName": None}}
    )
    
    return {"message": "Group deleted"}


# ==================== Contacts ====================

@router.get("")
async def get_contacts(
    current_user=Depends(get_current_user),
    group_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    has_birthday: Optional[bool] = Query(None),
    has_anniversary: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200)
):
    """Get contacts with optional filters"""
    query = {"userId": current_user.userId}
    
    if group_id:
        query["groupId"] = group_id
    
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}}
        ]
    
    if has_birthday is True:
        query["dob"] = {"$ne": None, "$exists": True}
    
    if has_anniversary is True:
        query["anniversary"] = {"$ne": None, "$exists": True}
    
    total = await db.contacts.count_documents(query)
    
    contacts = await db.contacts.find(
        query,
        {"_id": 0}
    ).sort("name", 1).skip(skip).limit(limit).to_list(limit)
    
    return {
        "contacts": contacts,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/{contact_id}")
async def get_contact(
    contact_id: str,
    current_user=Depends(get_current_user)
):
    """Get a single contact"""
    contact = await db.contacts.find_one(
        {"id": contact_id, "userId": current_user.userId},
        {"_id": 0}
    )
    
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    return {"contact": contact}


@router.post("")
async def create_contact(
    contact_data: ContactCreate,
    current_user=Depends(get_current_user)
):
    """Create a new contact"""
    # Get user's auto-message settings for default country code
    settings = await db.auto_message_settings.find_one({"userId": current_user.userId})
    default_code = settings.get('defaultCountryCode', '+91') if settings else '+91'
    
    # Normalize phone number
    normalized_phone = normalize_phone(contact_data.phone, default_code)
    
    # Get group name if groupId provided
    group_name = None
    if contact_data.groupId:
        group = await db.contact_groups.find_one({"id": contact_data.groupId})
        group_name = group.get('name') if group else None
    
    contact = Contact(
        userId=current_user.userId,
        name=contact_data.name,
        email=contact_data.email,
        phone=normalized_phone,
        countryCode=default_code,
        dob=contact_data.dob,
        anniversary=contact_data.anniversary,
        groupId=contact_data.groupId,
        groupName=group_name,
        notes=contact_data.notes,
        sendBirthdayWish=contact_data.sendBirthdayWish,
        sendAnniversaryWish=contact_data.sendAnniversaryWish
    )
    
    contact_dict = contact.model_dump()
    contact_dict['createdAt'] = contact_dict['createdAt'].isoformat()
    contact_dict['updatedAt'] = contact_dict['updatedAt'].isoformat()
    
    await db.contacts.insert_one(contact_dict)
    
    # Remove MongoDB _id before returning
    contact_dict.pop('_id', None)
    
    return {"message": "Contact created", "contact": contact_dict}


@router.put("/{contact_id}")
async def update_contact(
    contact_id: str,
    contact_data: ContactUpdate,
    current_user=Depends(get_current_user)
):
    """Update a contact"""
    existing = await db.contacts.find_one({
        "id": contact_id,
        "userId": current_user.userId
    })
    
    if not existing:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    update_data = {k: v for k, v in contact_data.model_dump().items() if v is not None}
    
    # Normalize phone if provided
    if 'phone' in update_data:
        settings = await db.auto_message_settings.find_one({"userId": current_user.userId})
        default_code = settings.get('defaultCountryCode', '+91') if settings else '+91'
        update_data['phone'] = normalize_phone(update_data['phone'], default_code)
    
    # Update group name if groupId changed
    if 'groupId' in update_data:
        if update_data['groupId']:
            group = await db.contact_groups.find_one({"id": update_data['groupId']})
            update_data['groupName'] = group.get('name') if group else None
        else:
            update_data['groupName'] = None
    
    update_data['updatedAt'] = datetime.now(timezone.utc).isoformat()
    
    await db.contacts.update_one(
        {"id": contact_id},
        {"$set": update_data}
    )
    
    return {"message": "Contact updated"}


@router.delete("/{contact_id}")
async def delete_contact(
    contact_id: str,
    current_user=Depends(get_current_user)
):
    """Delete a contact"""
    result = await db.contacts.delete_one({
        "id": contact_id,
        "userId": current_user.userId
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    return {"message": "Contact deleted"}


@router.post("/bulk-import")
async def bulk_import_contacts(
    import_data: ContactBulkImport,
    current_user=Depends(get_current_user)
):
    """Bulk import contacts"""
    imported = 0
    skipped = 0
    errors = []
    
    for idx, contact_data in enumerate(import_data.contacts):
        try:
            # Normalize phone
            normalized_phone = normalize_phone(
                contact_data.phone, 
                import_data.defaultCountryCode
            )
            
            # Check for duplicate
            existing = await db.contacts.find_one({
                "userId": current_user.userId,
                "phone": normalized_phone
            })
            
            if existing:
                skipped += 1
                continue
            
            # Get group name if groupId provided
            group_name = None
            if contact_data.groupId:
                group = await db.contact_groups.find_one({"id": contact_data.groupId})
                group_name = group.get('name') if group else None
            
            contact = Contact(
                userId=current_user.userId,
                name=contact_data.name,
                email=contact_data.email,
                phone=normalized_phone,
                countryCode=import_data.defaultCountryCode,
                dob=contact_data.dob,
                anniversary=contact_data.anniversary,
                groupId=contact_data.groupId,
                groupName=group_name,
                notes=contact_data.notes,
                sendBirthdayWish=contact_data.sendBirthdayWish,
                sendAnniversaryWish=contact_data.sendAnniversaryWish
            )
            
            contact_dict = contact.model_dump()
            contact_dict['createdAt'] = contact_dict['createdAt'].isoformat()
            contact_dict['updatedAt'] = contact_dict['updatedAt'].isoformat()
            
            await db.contacts.insert_one(contact_dict)
            imported += 1
            
        except Exception as e:
            errors.append(f"Row {idx + 1}: {str(e)}")
    
    return {
        "message": f"Import complete: {imported} imported, {skipped} duplicates skipped",
        "imported": imported,
        "skipped": skipped,
        "errors": errors[:10]  # Return first 10 errors
    }


# ==================== Auto-Message Settings ====================

@router.get("/settings/auto-messages")
async def get_auto_message_settings(current_user=Depends(get_current_user)):
    """Get auto-message settings"""
    settings = await db.auto_message_settings.find_one(
        {"userId": current_user.userId},
        {"_id": 0}
    )
    
    if not settings:
        # Return defaults
        settings = {
            "defaultCountryCode": "+91",
            "birthdayEnabled": True,
            "birthdayTime": "09:00",
            "birthdayTemplateName": "",
            "birthdayMessagePreview": "Happy Birthday {{name}}! Wishing you a wonderful day filled with joy and happiness!",
            "birthdayTemplateVariableCount": 1,
            "anniversaryEnabled": True,
            "anniversaryTime": "09:00",
            "anniversaryTemplateName": "",
            "anniversaryMessagePreview": "Happy Anniversary {{name}}! Wishing you many more years of love and happiness!",
            "anniversaryTemplateVariableCount": 1,
            "timezone": "Asia/Kolkata"
        }
    
    return {"settings": settings}


@router.put("/settings/auto-messages")
async def update_auto_message_settings(
    settings_data: AutoMessageSettingsUpdate,
    current_user=Depends(get_current_user)
):
    """Update auto-message settings"""
    update_data = {k: v for k, v in settings_data.model_dump().items() if v is not None}
    update_data['updatedAt'] = datetime.now(timezone.utc).isoformat()
    update_data['userId'] = current_user.userId
    
    await db.auto_message_settings.update_one(
        {"userId": current_user.userId},
        {"$set": update_data},
        upsert=True
    )
    
    return {"message": "Settings updated"}


# ==================== Birthday/Anniversary Stats ====================

@router.get("/stats/upcoming")
async def get_upcoming_events(
    current_user=Depends(get_current_user),
    days: int = Query(30, ge=1, le=365)
):
    """Get upcoming birthdays and anniversaries"""
    from datetime import date, timedelta
    
    today = date.today()
    
    # Get all contacts with DOB or anniversary
    contacts = await db.contacts.find(
        {
            "userId": current_user.userId,
            "$or": [
                {"dob": {"$ne": None}},
                {"anniversary": {"$ne": None}}
            ]
        },
        {"_id": 0}
    ).to_list(1000)
    
    upcoming_birthdays = []
    upcoming_anniversaries = []
    
    for contact in contacts:
        # Check birthday
        if contact.get('dob'):
            try:
                dob = datetime.strptime(contact['dob'], "%Y-%m-%d").date()
                this_year_bday = dob.replace(year=today.year)
                if this_year_bday < today:
                    this_year_bday = dob.replace(year=today.year + 1)
                
                days_until = (this_year_bday - today).days
                if 0 <= days_until <= days:
                    upcoming_birthdays.append({
                        "contact": contact,
                        "date": this_year_bday.isoformat(),
                        "daysUntil": days_until,
                        "age": this_year_bday.year - dob.year
                    })
            except:
                pass
        
        # Check anniversary
        if contact.get('anniversary'):
            try:
                anni = datetime.strptime(contact['anniversary'], "%Y-%m-%d").date()
                this_year_anni = anni.replace(year=today.year)
                if this_year_anni < today:
                    this_year_anni = anni.replace(year=today.year + 1)
                
                days_until = (this_year_anni - today).days
                if 0 <= days_until <= days:
                    upcoming_anniversaries.append({
                        "contact": contact,
                        "date": this_year_anni.isoformat(),
                        "daysUntil": days_until,
                        "years": this_year_anni.year - anni.year
                    })
            except:
                pass
    
    # Sort by days until
    upcoming_birthdays.sort(key=lambda x: x['daysUntil'])
    upcoming_anniversaries.sort(key=lambda x: x['daysUntil'])
    
    return {
        "birthdays": upcoming_birthdays[:20],
        "anniversaries": upcoming_anniversaries[:20],
        "totalBirthdays": len(upcoming_birthdays),
        "totalAnniversaries": len(upcoming_anniversaries)
    }
