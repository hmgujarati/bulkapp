"""Birthday and Anniversary Auto-Message Service"""
from datetime import datetime, timezone, date
from typing import Dict, Any
import httpx
import logging
import pytz
import os

from utils.database import db

logger = logging.getLogger(__name__)

BIZCHAT_API_BASE = os.environ.get('BIZCHAT_API_BASE', 'https://bizchatapi.in/api')


async def send_wish_message(
    phone: str,
    template_name: str,
    contact_name: str,
    message_preview: str,
    token: str,
    vendor_uid: str,
    wish_type: str,  # "birthday" or "anniversary"
    template_variable_count: int = 1  # Number of template variables
) -> Dict[str, Any]:
    """Send a birthday or anniversary wish via WhatsApp template"""
    try:
        async with httpx.AsyncClient() as client:
            clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
            
            url = f"{BIZCHAT_API_BASE}/{vendor_uid}/contact/send-template-message?token={token}"
            
            # Replace {{name}} in message preview
            message = message_preview.replace("{{name}}", contact_name)
            
            # Build base payload
            payload = {
                "phone_number": clean_phone,
                "template_name": template_name,
                "template_language": "en_US"
            }
            
            # DYNAMIC FIELD BUILDING: Only include the exact number of fields the template expects
            var_count = template_variable_count if template_variable_count and template_variable_count > 0 else 1
            
            # Prepare field values in order (adjust based on typical wish template structure)
            field_values = [
                contact_name,   # field_1 = name
                message,        # field_2 = message
                "",             # field_3 (placeholder)
                "",             # field_4 (placeholder)
                ""              # field_5 (placeholder)
            ]
            
            # Only add the exact number of fields the template expects
            for i in range(min(var_count, 5)):
                payload[f"field_{i + 1}"] = field_values[i]
            
            logger.info(f"Sending {wish_type} wish to {phone}, Template: {template_name}, Variables: {var_count}")
            
            response = await client.post(url, json=payload, timeout=30.0)
            response_text = response.text
            
            logger.info(f"BizChat Response: {response.status_code} - {response_text[:200]}")
            
            if response.status_code in [200, 201]:
                try:
                    data = response.json()
                    return {"success": True, "data": data}
                except Exception:
                    return {"success": True, "data": {"raw": response_text}}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}: {response_text[:300]}"}
                
    except Exception as e:
        error_msg = f"Exception: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}


async def process_birthday_wishes():
    """Check for birthdays today and send wishes"""
    today = date.today()
    today_str = today.strftime("%m-%d")  # MM-DD format for matching
    current_year = str(today.year)
    
    logger.info(f"Checking for birthdays on {today_str}")
    
    # Get all users' settings
    all_settings = await db.auto_message_settings.find({
        "birthdayEnabled": True,
        "birthdayTemplateName": {"$ne": "", "$exists": True}
    }).to_list(100)
    
    for settings in all_settings:
        user_id = settings['userId']
        template_name = settings.get('birthdayTemplateName', '')
        message_preview = settings.get('birthdayMessagePreview', 'Happy Birthday!')
        user_timezone = settings.get('timezone', 'Asia/Kolkata')
        send_time = settings.get('birthdayTime', '09:00')
        template_var_count = settings.get('birthdayTemplateVariableCount', 1)
        
        if not template_name:
            continue
        
        # Check if it's time to send (within 5 minutes of scheduled time)
        try:
            tz = pytz.timezone(user_timezone)
            now_local = datetime.now(tz)
            scheduled_hour, scheduled_min = map(int, send_time.split(':'))
            
            # Only process if within the scheduled hour
            if now_local.hour != scheduled_hour:
                continue
            # And within first 5 minutes of the hour (scheduler runs every minute)
            if now_local.minute > 5:
                continue
        except Exception as e:
            logger.error(f"Error parsing time for user {user_id}: {e}")
            continue
        
        # Get user's BizChat credentials
        user = await db.users.find_one({"id": user_id})
        if not user or not user.get('bizChatToken') or not user.get('bizChatVendorUID'):
            logger.warning(f"User {user_id} missing BizChat credentials")
            continue
        
        # Find contacts with birthday today who haven't received wish this year
        contacts = await db.contacts.find({
            "userId": user_id,
            "sendBirthdayWish": True,
            "dob": {"$regex": f"-{today_str}$"}  # Matches YYYY-MM-DD ending with -MM-DD
        }).to_list(500)
        
        for contact in contacts:
            # Check if already sent this year
            if contact.get('lastBirthdayWishSent') == current_year:
                continue
            
            # Send the wish
            result = await send_wish_message(
                phone=contact['phone'],
                template_name=template_name,
                contact_name=contact['name'],
                message_preview=message_preview,
                token=user['bizChatToken'],
                vendor_uid=user['bizChatVendorUID'],
                wish_type="birthday",
                template_variable_count=template_var_count
            )
            
            if result['success']:
                # Mark as sent for this year
                await db.contacts.update_one(
                    {"id": contact['id']},
                    {"$set": {
                        "lastBirthdayWishSent": current_year,
                        "updatedAt": datetime.now(timezone.utc).isoformat()
                    }}
                )
                logger.info(f"Birthday wish sent to {contact['name']} ({contact['phone']})")
            else:
                logger.error(f"Failed to send birthday wish to {contact['name']}: {result.get('error')}")


async def process_anniversary_wishes():
    """Check for anniversaries today and send wishes"""
    today = date.today()
    today_str = today.strftime("%m-%d")  # MM-DD format for matching
    current_year = str(today.year)
    
    logger.info(f"Checking for anniversaries on {today_str}")
    
    # Get all users' settings
    all_settings = await db.auto_message_settings.find({
        "anniversaryEnabled": True,
        "anniversaryTemplateName": {"$ne": "", "$exists": True}
    }).to_list(100)
    
    for settings in all_settings:
        user_id = settings['userId']
        template_name = settings.get('anniversaryTemplateName', '')
        message_preview = settings.get('anniversaryMessagePreview', 'Happy Anniversary!')
        user_timezone = settings.get('timezone', 'Asia/Kolkata')
        send_time = settings.get('anniversaryTime', '09:00')
        template_var_count = settings.get('anniversaryTemplateVariableCount', 1)
        
        if not template_name:
            continue
        
        # Check if it's time to send
        try:
            tz = pytz.timezone(user_timezone)
            now_local = datetime.now(tz)
            scheduled_hour, scheduled_min = map(int, send_time.split(':'))
            
            if now_local.hour != scheduled_hour:
                continue
            if now_local.minute > 5:
                continue
        except Exception as e:
            logger.error(f"Error parsing time for user {user_id}: {e}")
            continue
        
        # Get user's BizChat credentials
        user = await db.users.find_one({"id": user_id})
        if not user or not user.get('bizChatToken') or not user.get('bizChatVendorUID'):
            continue
        
        # Find contacts with anniversary today
        contacts = await db.contacts.find({
            "userId": user_id,
            "sendAnniversaryWish": True,
            "anniversary": {"$regex": f"-{today_str}$"}
        }).to_list(500)
        
        for contact in contacts:
            if contact.get('lastAnniversaryWishSent') == current_year:
                continue
            
            result = await send_wish_message(
                phone=contact['phone'],
                template_name=template_name,
                contact_name=contact['name'],
                message_preview=message_preview,
                token=user['bizChatToken'],
                vendor_uid=user['bizChatVendorUID'],
                wish_type="anniversary",
                template_variable_count=template_var_count
            )
            
            if result['success']:
                await db.contacts.update_one(
                    {"id": contact['id']},
                    {"$set": {
                        "lastAnniversaryWishSent": current_year,
                        "updatedAt": datetime.now(timezone.utc).isoformat()
                    }}
                )
                logger.info(f"Anniversary wish sent to {contact['name']} ({contact['phone']})")
            else:
                logger.error(f"Failed to send anniversary wish to {contact['name']}: {result.get('error')}")


async def process_auto_messages():
    """Main function to process all auto-messages (birthdays + anniversaries)"""
    try:
        await process_birthday_wishes()
        await process_anniversary_wishes()
    except Exception as e:
        logger.error(f"Error processing auto-messages: {e}")
