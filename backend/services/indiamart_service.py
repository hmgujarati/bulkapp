"""Indiamart lead service - handles auto-messaging for Indiamart leads"""
import logging
import httpx
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from utils.database import db

logger = logging.getLogger(__name__)

BIZCHAT_API_BASE = "https://bizchatapi.in/api"


async def send_lead_message(
    phone: str,
    template_name: str,
    template_language: str,
    fields: Dict[str, str],
    token: str,
    vendor_uid: str,
    header_image: Optional[str] = None,
    header_video: Optional[str] = None,
    header_document: Optional[str] = None
) -> Dict[str, Any]:
    """Send a WhatsApp template message to an Indiamart lead"""
    try:
        async with httpx.AsyncClient() as client:
            clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
            
            # Ensure phone has country code
            if not clean_phone.startswith('91') and len(clean_phone) == 10:
                clean_phone = '91' + clean_phone
            
            url = f"{BIZCHAT_API_BASE}/{vendor_uid}/contact/send-template-message?token={token}"
            
            payload = {
                "phone_number": clean_phone,
                "template_name": template_name,
                "template_language": template_language
            }
            
            # Add fields dynamically
            for key, value in fields.items():
                if value:
                    payload[key] = value
            
            # Add header media (only one type)
            if header_image:
                payload["header_image"] = header_image
            elif header_video:
                payload["header_video"] = header_video
            elif header_document:
                payload["header_document"] = header_document
            
            logger.info(f"Sending Indiamart lead message to {clean_phone}")
            logger.info(f"Template: {template_name}, Payload: {json.dumps(payload)}")
            
            response = await client.post(url, json=payload, timeout=30.0)
            response_text = response.text
            
            logger.info(f"BizChat Response: {response.status_code} - {response_text[:300]}")
            
            if response.status_code in [200, 201]:
                try:
                    data = response.json()
                    if data.get('result') == 'failed':
                        return {"success": False, "error": data.get('message', 'Unknown error')}
                    return {"success": True, "data": data}
                except:
                    return {"success": True, "data": {"raw": response_text}}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}: {response_text[:300]}"}
                
    except Exception as e:
        error_msg = f"Exception: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}


def build_message_fields(settings: dict, lead: dict) -> Dict[str, str]:
    """Build message fields by replacing placeholders with lead data"""
    replacements = {
        "{name}": lead.get('senderName', ''),
        "{product}": lead.get('productName', ''),
        "{message}": lead.get('queryMessage', ''),
        "{company}": lead.get('senderCompany', ''),
        "{city}": lead.get('senderCity', ''),
        "{email}": lead.get('senderEmail', ''),
    }
    
    fields = {}
    var_count = settings.get('templateVariableCount', 1)
    
    for i in range(1, min(var_count + 1, 6)):  # Support up to 5 fields
        field_key = f"messageField{i}"
        field_value = settings.get(field_key, '')
        
        if field_value:
            # Replace all placeholders
            for placeholder, value in replacements.items():
                field_value = field_value.replace(placeholder, value or '')
            
            fields[f"field_{i}"] = field_value
    
    return fields


async def process_new_lead(lead_id: str):
    """Process a new lead - send auto-reply message"""
    try:
        lead = await db.indiamart_leads.find_one({"id": lead_id})
        if not lead:
            logger.error(f"Lead {lead_id} not found")
            return
        
        # Get user's Indiamart settings
        settings = await db.indiamart_settings.find_one({"userId": lead['userId']})
        if not settings or not settings.get('autoReplyEnabled'):
            logger.info(f"Auto-reply disabled for user {lead['userId']}")
            return
        
        if not settings.get('templateName'):
            logger.error(f"No template configured for user {lead['userId']}")
            return
        
        # Get user's BizChat credentials
        user = await db.users.find_one({"id": lead['userId']})
        if not user or not user.get('bizChatToken') or not user.get('bizChatVendorUID'):
            logger.error(f"User {lead['userId']} missing BizChat credentials")
            await db.indiamart_leads.update_one(
                {"id": lead_id},
                {"$set": {"status": "message_failed", "lastMessageError": "BizChat credentials not configured"}}
            )
            return
        
        # Build message fields
        fields = build_message_fields(settings, lead)
        
        # Send the message
        result = await send_lead_message(
            phone=lead['senderMobile'],
            template_name=settings['templateName'],
            template_language=settings.get('templateLanguage', 'en_US'),
            fields=fields,
            token=user['bizChatToken'],
            vendor_uid=user['bizChatVendorUID'],
            header_image=settings.get('headerImage'),
            header_video=settings.get('headerVideo'),
            header_document=settings.get('headerDocument')
        )
        
        now = datetime.now(timezone.utc)
        
        if result['success']:
            # Calculate next message time if recurring is enabled
            next_message_at = None
            if settings.get('recurringEnabled') and lead.get('messagesSent', 0) < settings.get('recurringMaxCount', 3) - 1:
                interval_hours = settings.get('recurringIntervalHours', 24)
                next_message_at = (now + timedelta(hours=interval_hours)).isoformat()
            
            await db.indiamart_leads.update_one(
                {"id": lead_id},
                {
                    "$set": {
                        "status": "message_sent",
                        "lastMessageAt": now.isoformat(),
                        "lastMessageError": None,
                        "nextMessageAt": next_message_at,
                        "updatedAt": now.isoformat()
                    },
                    "$inc": {"messagesSent": 1}
                }
            )
            logger.info(f"Successfully sent message to lead {lead_id}")
        else:
            await db.indiamart_leads.update_one(
                {"id": lead_id},
                {
                    "$set": {
                        "status": "message_failed",
                        "lastMessageError": result.get('error', 'Unknown error'),
                        "updatedAt": now.isoformat()
                    }
                }
            )
            logger.error(f"Failed to send message to lead {lead_id}: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"Error processing lead {lead_id}: {e}")


async def process_recurring_messages():
    """Check for leads that need recurring messages"""
    try:
        now = datetime.now(timezone.utc)
        
        # Find leads with nextMessageAt <= now
        due_leads = await db.indiamart_leads.find({
            "nextMessageAt": {"$lte": now.isoformat()},
            "status": "message_sent"
        }).to_list(length=100)
        
        logger.info(f"Found {len(due_leads)} leads due for recurring messages")
        
        for lead in due_leads:
            # Get settings to check recurring config
            settings = await db.indiamart_settings.find_one({"userId": lead['userId']})
            if not settings or not settings.get('recurringEnabled'):
                # Clear nextMessageAt if recurring is disabled
                await db.indiamart_leads.update_one(
                    {"id": lead['id']},
                    {"$set": {"nextMessageAt": None}}
                )
                continue
            
            # Check if max count reached
            if lead.get('messagesSent', 0) >= settings.get('recurringMaxCount', 3):
                await db.indiamart_leads.update_one(
                    {"id": lead['id']},
                    {"$set": {"nextMessageAt": None}}
                )
                continue
            
            # Process the recurring message
            await process_new_lead(lead['id'])
            
    except Exception as e:
        logger.error(f"Error processing recurring messages: {e}")


async def start_indiamart_scheduler():
    """Start the background scheduler for Indiamart messages"""
    import asyncio
    
    logger.info("Indiamart message scheduler started")
    
    while True:
        try:
            await process_recurring_messages()
        except Exception as e:
            logger.error(f"Indiamart scheduler error: {e}")
        
        await asyncio.sleep(60)  # Check every minute
