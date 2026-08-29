"""Chatbot service - simplified conversation engine"""
import logging
import httpx
import asyncio
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List
from utils.database import db
from models.chatbot_schemas import (
    ChatbotConversation, ConversationAnswer, ConversationStatus,
    ChatbotLead, ChatbotLeadStatus, FlowQuestionItem
)

logger = logging.getLogger(__name__)

BIZCHAT_API_BASE = os.environ.get('BIZCHAT_API_BASE', 'https://bizchatapi.in/api')


# ===== WhatsApp Message Senders =====

async def send_text_message(phone: str, message: str, token: str, vendor_uid: str) -> bool:
    try:
        clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
        if not clean_phone.startswith('91') and len(clean_phone) == 10:
            clean_phone = '91' + clean_phone
        async with httpx.AsyncClient() as client:
            url = f"{BIZCHAT_API_BASE}/{vendor_uid}/contact/send-message?token={token}"
            payload = {"phone_number": clean_phone, "message_body": message}
            response = await client.post(url, json=payload, timeout=30.0)
            logger.info(f"Text message to {clean_phone}: {response.status_code}")
            return response.status_code in [200, 201]
    except Exception as e:
        logger.error(f"Error sending text message: {e}")
        return False


async def send_interactive_buttons(
    phone: str, body_text: str, buttons: Dict[str, str],
    token: str, vendor_uid: str,
    header_text: Optional[str] = None, footer_text: Optional[str] = None
) -> bool:
    try:
        clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
        if not clean_phone.startswith('91') and len(clean_phone) == 10:
            clean_phone = '91' + clean_phone
        async with httpx.AsyncClient() as client:
            url = f"{BIZCHAT_API_BASE}/{vendor_uid}/contact/send-interactive-message?token={token}"
            payload = {
                "phone_number": clean_phone,
                "interactive_type": "button",
                "body_text": body_text,
                "buttons": buttons
            }
            if header_text:
                payload["header_type"] = "text"
                payload["header_text"] = header_text
            if footer_text:
                payload["footer_text"] = footer_text
            response = await client.post(url, json=payload, timeout=30.0)
            if response.status_code in [200, 201]:
                return True
            logger.warning(f"Interactive buttons failed ({response.status_code}): {response.text[:300]}")
            # Fallback to text
            options_text = "\n".join([f"{k}. {v}" for k, v in buttons.items()])
            fallback = f"{body_text}\n\n{options_text}\n\n_Reply with the number of your choice_"
            return await send_text_message(clean_phone, fallback, token, vendor_uid)
    except Exception as e:
        logger.error(f"Error sending interactive buttons: {e}")
        try:
            options_text = "\n".join([f"{k}. {v}" for k, v in buttons.items()])
            fallback = f"{body_text}\n\n{options_text}\n\n_Reply with the number of your choice_"
            return await send_text_message(phone, fallback, token, vendor_uid)
        except Exception:
            return False


async def send_interactive_list(
    phone: str, body_text: str, button_text: str,
    sections: Dict, token: str, vendor_uid: str,
    header_text: Optional[str] = None, footer_text: Optional[str] = None
) -> bool:
    try:
        clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
        if not clean_phone.startswith('91') and len(clean_phone) == 10:
            clean_phone = '91' + clean_phone
        async with httpx.AsyncClient() as client:
            url = f"{BIZCHAT_API_BASE}/{vendor_uid}/contact/send-interactive-message?token={token}"
            payload = {
                "phone_number": clean_phone,
                "interactive_type": "list",
                "body_text": body_text,
                "list_data": {"button_text": button_text, "sections": sections}
            }
            if header_text:
                payload["header_type"] = "text"
                payload["header_text"] = header_text
            if footer_text:
                payload["footer_text"] = footer_text
            response = await client.post(url, json=payload, timeout=30.0)
            if response.status_code in [200, 201]:
                return True
            logger.warning(f"Interactive list failed ({response.status_code}): {response.text[:300]}")
            # Fallback to text
            items = []
            idx = 1
            for sec_key, sec in sections.items():
                for row_key, row in sec.get('rows', {}).items():
                    title = row.get('title', '')
                    desc = row.get('description', '')
                    line = f"{idx}. {title}"
                    if desc:
                        line += f" - {desc}"
                    items.append(line)
                    idx += 1
            fallback = f"{body_text}\n\n" + "\n".join(items) + "\n\n_Reply with the number of your choice_"
            return await send_text_message(clean_phone, fallback, token, vendor_uid)
    except Exception as e:
        logger.error(f"Error sending interactive list: {e}")
        return False


# ===== Helper builders =====

def build_question_buttons(options: List[str]) -> Dict[str, str]:
    buttons = {}
    for i, opt in enumerate(options[:3], 1):
        buttons[str(i)] = opt[:20]
    return buttons


def build_question_list_sections(options: List[str]) -> Dict:
    sections = {
        "section_1": {
            "title": "Options",
            "id": "section_1",
            "rows": {}
        }
    }
    for i, opt in enumerate(options[:10], 1):
        sections["section_1"]["rows"][f"row_{i}"] = {
            "id": f"row_{i}",
            "row_id": str(i),
            "title": opt[:24],
            "description": ""
        }
    return sections


async def get_user_credentials(user_id: str):
    user = await db.users.find_one({"id": user_id})
    if not user or not user.get('bizChatToken') or not user.get('bizChatVendorUID'):
        return None, None
    return user['bizChatToken'], user['bizChatVendorUID']


# ===== Core Chatbot Logic =====

async def handle_chatbot_message(user_id: str, client_phone: str, message_text: str, client_name: Optional[str] = None) -> bool:
    """Main entry point for incoming WhatsApp messages through the chatbot.
    Returns True if handled, False to pass to next handler."""

    user = await db.users.find_one({"id": user_id})
    if not user:
        return False

    features = user.get('features', {})
    if not features.get('chatbot', False):
        return False

    settings = await db.chatbot_settings.find_one({"userId": user_id})
    if not settings or not settings.get('isActive', False):
        return False

    token, vendor_uid = await get_user_credentials(user_id)
    if not token or not vendor_uid:
        return False

    # Check for active conversation
    conversation = await db.chatbot_conversations.find_one({
        "userId": user_id,
        "clientPhone": client_phone,
        "status": {"$in": [ConversationStatus.ACTIVE.value, ConversationStatus.FOLLOWUP_PENDING.value]}
    })

    now = datetime.now(timezone.utc)

    if not conversation:
        # No active conversation — check trigger keywords
        if message_text.lower().strip() in ['stop', 'exit', 'quit', 'cancel', 'bye']:
            return False

        # Find matching flow by trigger keyword
        flows = await db.chatbot_flows.find({"userId": user_id, "isActive": True}).to_list(100)
        if not flows:
            return False

        msg_lower = message_text.lower().strip()
        matched_flow = None
        for flow in flows:
            for trigger in flow.get('triggerKeywords', []):
                trigger_lower = trigger.lower().strip()
                if trigger_lower == msg_lower or trigger_lower in msg_lower or msg_lower in trigger_lower:
                    matched_flow = flow
                    break
            if matched_flow:
                break

        if not matched_flow:
            return False

        # Start new conversation
        questions = matched_flow.get('questions', [])
        greeting = matched_flow.get('greetingMessage')

        conv = ChatbotConversation(
            userId=user_id,
            flowId=matched_flow['id'],
            flowName=matched_flow['name'],
            clientPhone=client_phone,
            clientName=client_name,
            currentStep=0
        )
        await db.chatbot_conversations.insert_one(conv.model_dump())

        if not questions:
            # No questions — just send greeting/completion and create lead
            msg = greeting or matched_flow.get('completionMessage', 'Thank you!')
            await send_text_message(client_phone, msg, token, vendor_uid)
            await db.chatbot_conversations.update_one(
                {"id": conv.id},
                {"$set": {"status": ConversationStatus.COMPLETED.value, "currentStep": 0}}
            )
            await create_lead_from_conversation(conv.id)
            return True

        # Send greeting (if set) + first question
        prefix = f"{greeting}\n\n" if greeting else ""
        await send_question(client_phone, questions[0], token, vendor_uid, prefix=prefix)
        return True

    # Existing conversation — process answer
    conv_id = conversation['id']
    await db.chatbot_conversations.update_one(
        {"id": conv_id},
        {"$set": {"lastMessageAt": now.isoformat(), "updatedAt": now.isoformat()}}
    )

    # Handle stop/exit
    if message_text.lower().strip() in ['stop', 'exit', 'quit', 'cancel', 'bye']:
        await db.chatbot_conversations.update_one(
            {"id": conv_id},
            {"$set": {"status": ConversationStatus.ABANDONED.value, "updatedAt": now.isoformat()}}
        )
        await send_text_message(client_phone, "No problem! You can reach out anytime. Goodbye!", token, vendor_uid)
        return True

    # Get the flow
    flow = await db.chatbot_flows.find_one({"id": conversation['flowId']})
    if not flow:
        await db.chatbot_conversations.update_one(
            {"id": conv_id}, {"$set": {"status": ConversationStatus.ABANDONED.value}}
        )
        return False

    questions = flow.get('questions', [])
    current_step = conversation.get('currentStep', 0)

    if current_step >= len(questions):
        # Already done, shouldn't happen
        await complete_conversation(conv_id, flow, token, vendor_uid, client_phone, user_id, settings)
        return True

    # Record the answer
    current_q = questions[current_step]
    answer_text = message_text.strip()
    options = current_q.get('options', [])
    if options and answer_text.isdigit():
        idx = int(answer_text) - 1
        if 0 <= idx < len(options):
            answer_text = options[idx]

    answer = ConversationAnswer(
        questionId=current_q.get('id', str(current_step)),
        questionText=current_q['questionText'],
        answer=answer_text
    )

    next_step = current_step + 1

    if next_step >= len(questions):
        # All questions answered
        await db.chatbot_conversations.update_one(
            {"id": conv_id},
            {
                "$push": {"answers": answer.model_dump()},
                "$set": {
                    "currentStep": next_step,
                    "status": ConversationStatus.COMPLETED.value,
                    "updatedAt": now.isoformat()
                }
            }
        )
        await complete_conversation(conv_id, flow, token, vendor_uid, client_phone, user_id, settings)
    else:
        # Send next question
        await db.chatbot_conversations.update_one(
            {"id": conv_id},
            {
                "$push": {"answers": answer.model_dump()},
                "$set": {"currentStep": next_step, "updatedAt": now.isoformat()}
            }
        )
        await send_question(client_phone, questions[next_step], token, vendor_uid)

    return True


async def send_question(client_phone: str, question: dict, token: str, vendor_uid: str, prefix: str = ""):
    q_text = prefix + question['questionText']
    q_type = question.get('questionType', 'text')
    options = question.get('options', [])

    if options and len(options) <= 3:
        buttons = build_question_buttons(options)
        await send_interactive_buttons(client_phone, q_text, buttons, token, vendor_uid)
    elif options and len(options) > 3:
        sections = build_question_list_sections(options)
        await send_interactive_list(client_phone, q_text, "Select Option", sections, token, vendor_uid)
    else:
        await send_text_message(client_phone, q_text, token, vendor_uid)


async def complete_conversation(conv_id: str, flow: dict, token: str, vendor_uid: str, client_phone: str, user_id: str, settings: dict):
    completion_msg = flow.get('completionMessage', 'Thank you! Our team will contact you shortly.')
    await send_text_message(client_phone, completion_msg, token, vendor_uid)
    await create_lead_from_conversation(conv_id)


async def create_lead_from_conversation(conv_id: str):
    conversation = await db.chatbot_conversations.find_one({"id": conv_id})
    if not conversation:
        return

    lead = ChatbotLead(
        userId=conversation['userId'],
        conversationId=conv_id,
        flowId=conversation.get('flowId', ''),
        flowName=conversation.get('flowName', ''),
        clientPhone=conversation['clientPhone'],
        clientName=conversation.get('clientName'),
        answers=conversation.get('answers', [])
    )
    await db.chatbot_leads.insert_one(lead.model_dump())
    logger.info(f"Lead created from conversation {conv_id}: {lead.id}")

    asyncio.create_task(send_lead_notifications(lead.model_dump()))


async def send_lead_notifications(lead: dict):
    try:
        user_id = lead['userId']
        settings = await db.chatbot_settings.find_one({"userId": user_id})
        token, vendor_uid = await get_user_credentials(user_id)
        if not token or not vendor_uid:
            return

        notification = build_lead_notification(lead)

        # Check flow-level notify phone first
        flow = await db.chatbot_flows.find_one({"id": lead.get('flowId')})
        notify_phone = None
        if flow and flow.get('notifyPhone'):
            notify_phone = flow['notifyPhone']
        elif settings and settings.get('defaultNotifyPhone'):
            notify_phone = settings['defaultNotifyPhone']

        if notify_phone:
            await send_text_message(notify_phone, notification, token, vendor_uid)
            await db.chatbot_leads.update_one(
                {"id": lead['id']},
                {"$set": {"notificationSent": True}}
            )

    except Exception as e:
        logger.error(f"Error sending lead notification: {e}")


def build_lead_notification(lead: dict) -> str:
    lines = [
        "--- *New Lead Received* ---",
        "",
        f"Phone: {lead.get('clientPhone', 'Unknown')}",
    ]
    if lead.get('clientName'):
        lines.append(f"Name: {lead['clientName']}")
    if lead.get('flowName'):
        lines.append(f"Flow: {lead['flowName']}")

    answers = lead.get('answers', [])
    if answers:
        lines.append("")
        lines.append("*Responses:*")
        for a in answers:
            lines.append(f"Q: {a.get('questionText', '')}")
            lines.append(f"A: {a.get('answer', '')}")
            lines.append("")

    lines.append("---")
    return "\n".join(lines)


# ===== Follow-up Scheduler =====

async def process_chatbot_followups():
    try:
        now = datetime.now(timezone.utc)

        stale_convs = await db.chatbot_conversations.find({
            "status": {"$in": [ConversationStatus.ACTIVE.value, ConversationStatus.FOLLOWUP_PENDING.value]},
            "nextFollowUpAt": {"$lte": now.isoformat()}
        }).to_list(100)

        for conv in stale_convs:
            user_id = conv['userId']
            settings = await db.chatbot_settings.find_one({"userId": user_id})
            if not settings:
                continue

            max_followups = settings.get('maxFollowUps', 2)
            current_followups = conv.get('followUpCount', 0)

            if current_followups >= max_followups:
                await db.chatbot_conversations.update_one(
                    {"id": conv['id']},
                    {"$set": {
                        "status": ConversationStatus.ABANDONED.value,
                        "nextFollowUpAt": None,
                        "updatedAt": now.isoformat()
                    }}
                )
                await create_lead_from_conversation(conv['id'])
                continue

            token, vendor_uid = await get_user_credentials(user_id)
            if not token or not vendor_uid:
                continue

            follow_up_msg = settings.get('followUpMessage', 'Hi! Would you like to continue?')
            await send_text_message(conv['clientPhone'], follow_up_msg, token, vendor_uid)

            delay_minutes = settings.get('followUpDelayMinutes', 15)
            next_followup = (now + timedelta(minutes=delay_minutes)).isoformat()

            await db.chatbot_conversations.update_one(
                {"id": conv['id']},
                {"$set": {
                    "followUpCount": current_followups + 1,
                    "status": ConversationStatus.FOLLOWUP_PENDING.value,
                    "nextFollowUpAt": next_followup,
                    "lastMessageAt": now.isoformat(),
                    "updatedAt": now.isoformat()
                }}
            )

        # Schedule follow-ups for idle active conversations
        delay_threshold = now - timedelta(minutes=5)
        idle_convs = await db.chatbot_conversations.find({
            "status": ConversationStatus.ACTIVE.value,
            "nextFollowUpAt": None,
            "lastMessageAt": {"$lte": delay_threshold.isoformat()},
        }).to_list(100)

        for conv in idle_convs:
            settings = await db.chatbot_settings.find_one({"userId": conv['userId']})
            if not settings:
                continue
            delay_minutes = settings.get('followUpDelayMinutes', 15)
            last_msg = datetime.fromisoformat(conv['lastMessageAt'].replace('Z', '+00:00'))
            next_followup = (last_msg + timedelta(minutes=delay_minutes)).isoformat()
            await db.chatbot_conversations.update_one(
                {"id": conv['id']},
                {"$set": {"nextFollowUpAt": next_followup}}
            )

    except Exception as e:
        logger.error(f"Error in chatbot follow-ups: {e}")


async def start_chatbot_scheduler():
    logger.info("Chatbot follow-up scheduler started")
    while True:
        try:
            await process_chatbot_followups()
        except Exception as e:
            logger.error(f"Chatbot scheduler error: {e}")
        await asyncio.sleep(60)
