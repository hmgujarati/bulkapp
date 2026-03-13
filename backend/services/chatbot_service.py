"""Chatbot service - conversation engine, notifications, follow-ups"""
import logging
import httpx
import json
import os
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from utils.database import db
from models.chatbot_schemas import (
    ChatbotConversation, ConversationAnswer, ConversationStatus,
    ChatbotLead, ChatbotLeadStatus
)

logger = logging.getLogger(__name__)

BIZCHAT_API_BASE = os.environ.get('BIZCHAT_API_BASE', 'https://bizchatapi.in/api')


async def send_text_message(phone: str, message: str, token: str, vendor_uid: str) -> bool:
    """Send a plain text WhatsApp message"""
    try:
        clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
        if not clean_phone.startswith('91') and len(clean_phone) == 10:
            clean_phone = '91' + clean_phone

        async with httpx.AsyncClient() as client:
            url = f"{BIZCHAT_API_BASE}/{vendor_uid}/contact/send-message?token={token}"
            payload = {
                "phone_number": clean_phone,
                "message_body": message
            }
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
    """Send interactive button message (max 3 buttons)"""
    try:
        clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
        if not clean_phone.startswith('91') and len(clean_phone) == 10:
            clean_phone = '91' + clean_phone

        async with httpx.AsyncClient() as client:
            url = f"{BIZCHAT_API_BASE}/{vendor_uid}/contact/send-interactive-message?token={token}"
            payload = {
                "phone_number": clean_phone,
                "interactive_type": "button",
                "header_type": "text",
                "header_text": header_text or "",
                "body_text": body_text,
                "footer_text": footer_text or "",
                "buttons": buttons
            }
            response = await client.post(url, json=payload, timeout=30.0)
            logger.info(f"Interactive buttons to {clean_phone}: {response.status_code}")
            return response.status_code in [200, 201]
    except Exception as e:
        logger.error(f"Error sending interactive buttons: {e}")
        return False


async def send_interactive_list(
    phone: str, body_text: str, button_text: str,
    sections: Dict[str, Any], token: str, vendor_uid: str,
    header_text: Optional[str] = None, footer_text: Optional[str] = None
) -> bool:
    """Send interactive list message"""
    try:
        clean_phone = phone.replace('+', '').replace('-', '').replace(' ', '')
        if not clean_phone.startswith('91') and len(clean_phone) == 10:
            clean_phone = '91' + clean_phone

        async with httpx.AsyncClient() as client:
            url = f"{BIZCHAT_API_BASE}/{vendor_uid}/contact/send-interactive-message?token={token}"
            payload = {
                "phone_number": clean_phone,
                "interactive_type": "list",
                "header_type": "text",
                "header_text": header_text or "",
                "body_text": body_text,
                "footer_text": footer_text or "",
                "list_data": {
                    "button_text": button_text,
                    "sections": sections
                }
            }
            response = await client.post(url, json=payload, timeout=30.0)
            logger.info(f"Interactive list to {clean_phone}: {response.status_code}")
            return response.status_code in [200, 201]
    except Exception as e:
        logger.error(f"Error sending interactive list: {e}")
        return False


def build_category_list_sections(categories: List[dict]) -> Dict[str, Any]:
    """Build sections dict for interactive list from categories"""
    sections = {}
    # WhatsApp list supports max 10 rows per section, max 10 sections
    batch_size = 10
    for i in range(0, len(categories), batch_size):
        batch = categories[i:i + batch_size]
        section_key = f"section_{i // batch_size + 1}"
        section_title = "Our Categories" if i == 0 else f"More Categories ({i // batch_size + 1})"
        rows = {}
        for j, cat in enumerate(batch):
            row_key = f"row_{j + 1}"
            rows[row_key] = {
                "id": row_key,
                "row_id": cat['id'][:20],  # WhatsApp has 200 char limit on row_id
                "title": cat['name'][:24],  # WhatsApp 24 char limit on title
                "description": (cat.get('description') or '')[:72]  # 72 char limit
            }
        sections[section_key] = {
            "title": section_title[:24],
            "id": section_key,
            "rows": rows
        }
    return sections


def build_product_list_sections(products: List[dict]) -> Dict[str, Any]:
    """Build sections dict for interactive list from products"""
    sections = {}
    batch_size = 10
    for i in range(0, len(products), batch_size):
        batch = products[i:i + batch_size]
        section_key = f"section_{i // batch_size + 1}"
        section_title = "Products" if i == 0 else f"More Products ({i // batch_size + 1})"
        rows = {}
        for j, prod in enumerate(batch):
            row_key = f"row_{j + 1}"
            desc = prod.get('description') or ''
            if prod.get('price'):
                desc = f"Price: {prod['price']}" + (f" | {desc}" if desc else '')
            rows[row_key] = {
                "id": row_key,
                "row_id": prod['id'][:20],
                "title": prod['name'][:24],
                "description": desc[:72]
            }
        sections[section_key] = {
            "title": section_title[:24],
            "id": section_key,
            "rows": rows
        }
    return sections


def build_question_buttons(options: List[str]) -> Dict[str, str]:
    """Build buttons dict from question options (max 3)"""
    buttons = {}
    for i, opt in enumerate(options[:3], 1):
        buttons[str(i)] = opt[:20]  # WhatsApp 20 char limit on button text
    return buttons


def build_question_list_sections(options: List[str]) -> Dict[str, Any]:
    """Build list sections from question options (for >3 options)"""
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
    """Get user's BizChat credentials"""
    user = await db.users.find_one({"id": user_id})
    if not user or not user.get('bizChatToken') or not user.get('bizChatVendorUID'):
        return None, None
    return user['bizChatToken'], user['bizChatVendorUID']


async def find_active_conversation(user_id: str, client_phone: str) -> Optional[dict]:
    """Find an active conversation for a client phone number"""
    return await db.chatbot_conversations.find_one({
        "userId": user_id,
        "clientPhone": client_phone,
        "status": {"$in": [ConversationStatus.ACTIVE.value, ConversationStatus.FOLLOWUP_PENDING.value]}
    })


async def handle_chatbot_message(user_id: str, client_phone: str, message_text: str, client_name: Optional[str] = None) -> bool:
    """
    Main entry point for processing an incoming WhatsApp message through the chatbot.
    Returns True if the message was handled by the chatbot, False otherwise.
    """
    # Check if chatbot feature is enabled for user
    user = await db.users.find_one({"id": user_id})
    if not user:
        return False

    features = user.get('features', {})
    if not features.get('chatbot', False):
        return False

    # Get chatbot settings
    settings = await db.chatbot_settings.find_one({"userId": user_id})
    if not settings or not settings.get('isActive', False):
        return False

    token, vendor_uid = await get_user_credentials(user_id)
    if not token or not vendor_uid:
        return False

    # Find existing active conversation
    conversation = await find_active_conversation(user_id, client_phone)

    now = datetime.now(timezone.utc)

    if not conversation:
        # No active conversation - check if message matches a category trigger keyword
        if message_text.lower().strip() in ['stop', 'exit', 'quit', 'cancel', 'bye']:
            return False

        # Find category by trigger keyword match
        categories = await db.chatbot_categories.find({
            "userId": user_id, "isActive": True
        }).sort("sortOrder", 1).to_list(100)

        if not categories:
            return False

        msg_lower = message_text.lower().strip()
        matched_category = None

        for cat in categories:
            triggers = cat.get('triggerKeywords', [])
            for trigger in triggers:
                if trigger.lower().strip() == msg_lower:
                    matched_category = cat
                    break
                # Also allow partial/contains match
                if trigger.lower().strip() in msg_lower or msg_lower in trigger.lower().strip():
                    matched_category = cat
                    break
            if matched_category:
                break

        if not matched_category:
            # No trigger matched - don't handle this message, let reminder bot process it
            return False

        # Trigger matched! Start conversation directly with this category
        greeting = settings.get('greetingMessage', 'Hello! Welcome.')

        # Check product count for matched category
        product_count = await db.chatbot_products.count_documents({
            "userId": user_id, "categoryId": matched_category['id'], "isActive": True
        })

        if product_count == 0:
            # No products - create conversation and go straight to questions
            conv = ChatbotConversation(
                userId=user_id,
                clientPhone=client_phone,
                clientName=client_name,
                categoryId=matched_category['id'],
                categoryName=matched_category['name'],
                currentStep="question_0"
            )
            await db.chatbot_conversations.insert_one(conv.model_dump())
            await send_first_question(conv.model_dump(), matched_category['id'], token, vendor_uid, greeting_prefix=f"{greeting}\n\n")
        elif product_count <= 10:
            # Few products - show list
            products = await db.chatbot_products.find({
                "userId": user_id, "categoryId": matched_category['id'], "isActive": True
            }).to_list(10)

            conv = ChatbotConversation(
                userId=user_id,
                clientPhone=client_phone,
                clientName=client_name,
                categoryId=matched_category['id'],
                categoryName=matched_category['name'],
                currentStep="product_select"
            )
            await db.chatbot_conversations.insert_one(conv.model_dump())

            body_text = f"{greeting}\n\nYou're interested in *{matched_category['name']}*. Please select a product:"
            if len(products) <= 3:
                buttons = {}
                for i, prod in enumerate(products[:3], 1):
                    buttons[str(i)] = prod['name'][:20]
                await send_interactive_buttons(
                    client_phone, body_text, buttons, token, vendor_uid,
                    header_text=matched_category['name']
                )
            else:
                sections = build_product_list_sections(products)
                await send_interactive_list(
                    client_phone, body_text, "View Products", sections, token, vendor_uid,
                    header_text=matched_category['name']
                )
        else:
            # Many products - ask to search
            conv = ChatbotConversation(
                userId=user_id,
                clientPhone=client_phone,
                clientName=client_name,
                categoryId=matched_category['id'],
                categoryName=matched_category['name'],
                currentStep="product_search"
            )
            await db.chatbot_conversations.insert_one(conv.model_dump())
            await send_text_message(
                client_phone,
                f"{greeting}\n\n"
                f"You're interested in *{matched_category['name']}*. We have {product_count} products.\n\n"
                f"Type the first few letters of the product you're looking for, and I'll find it for you.",
                token, vendor_uid
            )

        return True

    # Existing conversation - process based on current step
    conv_id = conversation['id']

    # Update last message time
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
        await send_text_message(
            client_phone,
            "No problem! You can reach out anytime. Goodbye!",
            token, vendor_uid
        )
        return True

    current_step = conversation.get('currentStep', 'greeting')

    if current_step == "category_select":
        await process_category_selection(conversation, message_text, settings, token, vendor_uid)
    elif current_step == "product_search":
        await process_product_search(conversation, message_text, token, vendor_uid)
    elif current_step == "product_select":
        await process_product_selection(conversation, message_text, settings, token, vendor_uid)
    elif current_step.startswith("question_"):
        await process_question_answer(conversation, message_text, settings, token, vendor_uid)
    else:
        # Unknown step, restart
        await db.chatbot_conversations.update_one(
            {"id": conv_id},
            {"$set": {"status": ConversationStatus.ABANDONED.value}}
        )
        return False

    return True


async def process_category_selection(conversation: dict, message_text: str, settings: dict, token: str, vendor_uid: str):
    """Process category selection from the client"""
    user_id = conversation['userId']
    conv_id = conversation['id']
    client_phone = conversation['clientPhone']

    categories = await db.chatbot_categories.find({
        "userId": user_id, "isActive": True
    }).sort("sortOrder", 1).to_list(100)

    selected_category = None

    # Try to match by button number (1, 2, 3)
    msg_stripped = message_text.strip()
    if msg_stripped.isdigit():
        idx = int(msg_stripped) - 1
        if 0 <= idx < len(categories):
            selected_category = categories[idx]

    # Try to match by name (case-insensitive)
    if not selected_category:
        msg_lower = message_text.lower().strip()
        for cat in categories:
            if cat['name'].lower() == msg_lower or cat['name'].lower() in msg_lower:
                selected_category = cat
                break

    # Try partial match
    if not selected_category:
        msg_lower = message_text.lower().strip()
        for cat in categories:
            if msg_lower in cat['name'].lower():
                selected_category = cat
                break

    if not selected_category:
        # Didn't match any category, ask again
        body_text = "Sorry, I couldn't find that category. Please select from the options:"
        if len(categories) <= 3:
            buttons = {}
            for i, cat in enumerate(categories[:3], 1):
                buttons[str(i)] = cat['name'][:20]
            await send_interactive_buttons(
                client_phone, body_text, buttons, token, vendor_uid
            )
        else:
            sections = build_category_list_sections(categories)
            await send_interactive_list(
                client_phone, body_text, "View Categories", sections, token, vendor_uid
            )
        return

    # Category selected - check product count
    product_count = await db.chatbot_products.count_documents({
        "userId": user_id, "categoryId": selected_category['id'], "isActive": True
    })

    now = datetime.now(timezone.utc).isoformat()

    if product_count == 0:
        # No products, skip to questions
        await db.chatbot_conversations.update_one(
            {"id": conv_id},
            {"$set": {
                "categoryId": selected_category['id'],
                "categoryName": selected_category['name'],
                "currentStep": "question_0",
                "updatedAt": now
            }}
        )
        await send_first_question(conversation, selected_category['id'], token, vendor_uid)
    elif product_count <= 10:
        # Few products - show list directly
        products = await db.chatbot_products.find({
            "userId": user_id, "categoryId": selected_category['id'], "isActive": True
        }).to_list(10)

        await db.chatbot_conversations.update_one(
            {"id": conv_id},
            {"$set": {
                "categoryId": selected_category['id'],
                "categoryName": selected_category['name'],
                "currentStep": "product_select",
                "updatedAt": now
            }}
        )

        body_text = f"Great! Here are our products in *{selected_category['name']}*.\n\nPlease select one:"
        if len(products) <= 3:
            buttons = {}
            for i, prod in enumerate(products[:3], 1):
                buttons[str(i)] = prod['name'][:20]
            await send_interactive_buttons(
                client_phone, body_text, buttons, token, vendor_uid,
                header_text=selected_category['name']
            )
        else:
            sections = build_product_list_sections(products)
            await send_interactive_list(
                client_phone, body_text, "View Products", sections, token, vendor_uid,
                header_text=selected_category['name']
            )
    else:
        # Many products - ask to search
        await db.chatbot_conversations.update_one(
            {"id": conv_id},
            {"$set": {
                "categoryId": selected_category['id'],
                "categoryName": selected_category['name'],
                "currentStep": "product_search",
                "updatedAt": now
            }}
        )
        await send_text_message(
            client_phone,
            f"We have {product_count} products in *{selected_category['name']}*.\n\n"
            f"Type the first few letters of the product you're looking for, and I'll find it for you.",
            token, vendor_uid
        )


async def process_product_search(conversation: dict, message_text: str, token: str, vendor_uid: str):
    """Process product search query from client"""
    user_id = conversation['userId']
    conv_id = conversation['id']
    client_phone = conversation['clientPhone']
    category_id = conversation.get('categoryId')

    search_text = message_text.strip()

    # Search products by name (case-insensitive partial match)
    products = await db.chatbot_products.find({
        "userId": user_id,
        "categoryId": category_id,
        "isActive": True,
        "name": {"$regex": search_text, "$options": "i"}
    }).limit(10).to_list(10)

    if not products:
        await send_text_message(
            client_phone,
            f"No products found matching \"{search_text}\".\n\nPlease try again with different keywords, or type *list* to see all products.",
            token, vendor_uid
        )
        return

    now = datetime.now(timezone.utc).isoformat()
    await db.chatbot_conversations.update_one(
        {"id": conv_id},
        {"$set": {"currentStep": "product_select", "updatedAt": now}}
    )

    body_text = f"Here are products matching \"{search_text}\".\nPlease select one:"
    if len(products) <= 3:
        buttons = {}
        for i, prod in enumerate(products[:3], 1):
            buttons[str(i)] = prod['name'][:20]
        await send_interactive_buttons(
            client_phone, body_text, buttons, token, vendor_uid
        )
    else:
        sections = build_product_list_sections(products)
        await send_interactive_list(
            client_phone, body_text, "Select Product", sections, token, vendor_uid
        )

    # Store search results for matching in next step
    product_ids = [p['id'] for p in products]
    product_names = [p['name'] for p in products]
    await db.chatbot_conversations.update_one(
        {"id": conv_id},
        {"$set": {"_searchResultIds": product_ids, "_searchResultNames": product_names}}
    )


async def process_product_selection(conversation: dict, message_text: str, settings: dict, token: str, vendor_uid: str):
    """Process product selection from the client"""
    user_id = conversation['userId']
    conv_id = conversation['id']
    client_phone = conversation['clientPhone']
    category_id = conversation.get('categoryId')

    # Handle "list" command to show all products
    if message_text.lower().strip() == 'list':
        await db.chatbot_conversations.update_one(
            {"id": conv_id},
            {"$set": {"currentStep": "product_search"}}
        )
        # Show first 10 products
        products = await db.chatbot_products.find({
            "userId": user_id, "categoryId": category_id, "isActive": True
        }).limit(10).to_list(10)
        if products:
            sections = build_product_list_sections(products)
            await send_interactive_list(
                client_phone, "Here are our products:", "Select Product",
                sections, token, vendor_uid
            )
        return

    # Get candidate products - either from search results or category
    search_ids = conversation.get('_searchResultIds')
    search_names = conversation.get('_searchResultNames')

    selected_product = None
    msg_stripped = message_text.strip()

    if search_ids and search_names:
        # Match from search results
        if msg_stripped.isdigit():
            idx = int(msg_stripped) - 1
            if 0 <= idx < len(search_ids):
                selected_product = await db.chatbot_products.find_one({"id": search_ids[idx]})
        if not selected_product:
            msg_lower = message_text.lower().strip()
            for pid, pname in zip(search_ids, search_names):
                if pname.lower() == msg_lower or msg_lower in pname.lower():
                    selected_product = await db.chatbot_products.find_one({"id": pid})
                    break
    else:
        # Match from all category products
        products = await db.chatbot_products.find({
            "userId": user_id, "categoryId": category_id, "isActive": True
        }).to_list(100)

        if msg_stripped.isdigit():
            idx = int(msg_stripped) - 1
            if 0 <= idx < len(products):
                selected_product = products[idx]
        if not selected_product:
            msg_lower = message_text.lower().strip()
            for prod in products:
                if prod['name'].lower() == msg_lower or msg_lower in prod['name'].lower():
                    selected_product = prod
                    break

    if not selected_product:
        # Check if they're searching
        products = await db.chatbot_products.find({
            "userId": user_id, "categoryId": category_id, "isActive": True,
            "name": {"$regex": message_text.strip(), "$options": "i"}
        }).limit(10).to_list(10)

        if products:
            body_text = f"Did you mean one of these?"
            if len(products) <= 3:
                buttons = {}
                for i, prod in enumerate(products[:3], 1):
                    buttons[str(i)] = prod['name'][:20]
                await send_interactive_buttons(client_phone, body_text, buttons, token, vendor_uid)
            else:
                sections = build_product_list_sections(products)
                await send_interactive_list(
                    client_phone, body_text, "Select Product", sections, token, vendor_uid
                )
            product_ids = [p['id'] for p in products]
            product_names = [p['name'] for p in products]
            await db.chatbot_conversations.update_one(
                {"id": conv_id},
                {"$set": {"_searchResultIds": product_ids, "_searchResultNames": product_names}}
            )
        else:
            await send_text_message(
                client_phone,
                "Sorry, I couldn't find that product. Please try typing a few letters of the product name.",
                token, vendor_uid
            )
        return

    # Product selected - move to questions
    now = datetime.now(timezone.utc).isoformat()
    await db.chatbot_conversations.update_one(
        {"id": conv_id},
        {"$set": {
            "productId": selected_product['id'],
            "productName": selected_product['name'],
            "currentStep": "question_0",
            "updatedAt": now
        }}
    )
    await send_first_question(
        {**conversation, "categoryId": category_id},
        category_id, token, vendor_uid,
        product_name=selected_product['name']
    )


async def send_first_question(conversation: dict, category_id: str, token: str, vendor_uid: str, product_name: Optional[str] = None, greeting_prefix: str = ""):
    """Send the first qualifying question"""
    user_id = conversation['userId']
    client_phone = conversation['clientPhone']

    questions = await db.chatbot_flow_questions.find({
        "userId": user_id, "categoryId": category_id
    }).sort("sortOrder", 1).to_list(50)

    if not questions:
        # No questions configured, complete immediately
        conv_id = conversation['id']
        now = datetime.now(timezone.utc).isoformat()
        await db.chatbot_conversations.update_one(
            {"id": conv_id},
            {"$set": {"currentStep": "completed", "status": ConversationStatus.COMPLETED.value, "updatedAt": now}}
        )
        settings = await db.chatbot_settings.find_one({"userId": user_id})
        completion_msg = (settings or {}).get('completionMessage', 'Thank you! Our team will contact you shortly.')
        if product_name:
            completion_msg = f"Great choice - *{product_name}*!\n\n{completion_msg}"
        completion_msg = greeting_prefix + completion_msg
        await send_text_message(client_phone, completion_msg, token, vendor_uid)
        await create_lead_from_conversation(conv_id)
        return

    # Send first question
    question = questions[0]
    prefix = greeting_prefix
    if product_name:
        prefix += f"Great choice - *{product_name}*!\n\n"
    await send_question(client_phone, question, token, vendor_uid, prefix=prefix)


async def send_question(client_phone: str, question: dict, token: str, vendor_uid: str, prefix: str = ""):
    """Send a single question to the client"""
    q_text = prefix + question['questionText']
    q_type = question.get('questionType', 'text')
    options = question.get('options', [])

    if q_type == 'button' and options and len(options) <= 3:
        buttons = build_question_buttons(options)
        await send_interactive_buttons(client_phone, q_text, buttons, token, vendor_uid)
    elif q_type == 'list' and options and len(options) > 3:
        sections = build_question_list_sections(options)
        await send_interactive_list(
            client_phone, q_text, "Select Option", sections, token, vendor_uid
        )
    elif options and len(options) <= 3:
        buttons = build_question_buttons(options)
        await send_interactive_buttons(client_phone, q_text, buttons, token, vendor_uid)
    elif options and len(options) > 3:
        sections = build_question_list_sections(options)
        await send_interactive_list(
            client_phone, q_text, "Select Option", sections, token, vendor_uid
        )
    else:
        await send_text_message(client_phone, q_text, token, vendor_uid)


async def process_question_answer(conversation: dict, message_text: str, settings: dict, token: str, vendor_uid: str):
    """Process answer to a qualifying question"""
    user_id = conversation['userId']
    conv_id = conversation['id']
    client_phone = conversation['clientPhone']
    category_id = conversation.get('categoryId')
    current_step = conversation.get('currentStep', 'question_0')

    # Extract question index
    try:
        q_idx = int(current_step.split('_')[1])
    except (ValueError, IndexError):
        q_idx = 0

    # Get all questions for this category
    questions = await db.chatbot_flow_questions.find({
        "userId": user_id, "categoryId": category_id
    }).sort("sortOrder", 1).to_list(50)

    if q_idx >= len(questions):
        # All questions answered, complete
        await complete_conversation(conv_id, settings, token, vendor_uid, client_phone, user_id)
        return

    current_question = questions[q_idx]

    # Resolve the answer text (match button/list options if applicable)
    answer_text = message_text.strip()
    options = current_question.get('options', [])
    if options and answer_text.isdigit():
        idx = int(answer_text) - 1
        if 0 <= idx < len(options):
            answer_text = options[idx]

    # Store answer
    answer = ConversationAnswer(
        questionId=current_question['id'],
        questionText=current_question['questionText'],
        answer=answer_text
    )

    now = datetime.now(timezone.utc).isoformat()
    next_q_idx = q_idx + 1

    if next_q_idx >= len(questions):
        # All questions answered
        await db.chatbot_conversations.update_one(
            {"id": conv_id},
            {
                "$push": {"answers": answer.model_dump()},
                "$set": {
                    "currentStep": "completed",
                    "status": ConversationStatus.COMPLETED.value,
                    "updatedAt": now
                }
            }
        )
        await complete_conversation(conv_id, settings, token, vendor_uid, client_phone, user_id)
    else:
        # Move to next question
        await db.chatbot_conversations.update_one(
            {"id": conv_id},
            {
                "$push": {"answers": answer.model_dump()},
                "$set": {"currentStep": f"question_{next_q_idx}", "updatedAt": now}
            }
        )
        next_question = questions[next_q_idx]
        await send_question(client_phone, next_question, token, vendor_uid)


async def complete_conversation(conv_id: str, settings: dict, token: str, vendor_uid: str, client_phone: str, user_id: str):
    """Complete a conversation - create lead and send notifications"""
    completion_msg = (settings or {}).get('completionMessage', 'Thank you! Our team will contact you shortly.')
    await send_text_message(client_phone, completion_msg, token, vendor_uid)

    # Create lead
    await create_lead_from_conversation(conv_id)


async def create_lead_from_conversation(conv_id: str):
    """Create a lead record from a completed conversation"""
    conversation = await db.chatbot_conversations.find_one({"id": conv_id})
    if not conversation:
        return

    lead = ChatbotLead(
        userId=conversation['userId'],
        conversationId=conv_id,
        clientPhone=conversation['clientPhone'],
        clientName=conversation.get('clientName'),
        categoryId=conversation.get('categoryId'),
        categoryName=conversation.get('categoryName'),
        productId=conversation.get('productId'),
        productName=conversation.get('productName'),
        answers=conversation.get('answers', [])
    )
    await db.chatbot_leads.insert_one(lead.model_dump())
    logger.info(f"Lead created from conversation {conv_id}: {lead.id}")

    # Send notifications
    asyncio.create_task(send_lead_notifications(lead.model_dump()))


async def send_lead_notifications(lead: dict):
    """Send WhatsApp notification about new lead"""
    try:
        user_id = lead['userId']
        settings = await db.chatbot_settings.find_one({"userId": user_id})
        if not settings:
            return

        token, vendor_uid = await get_user_credentials(user_id)
        if not token or not vendor_uid:
            return

        # Build notification message
        notification = build_lead_notification(lead)

        # Notify main number (always)
        if settings.get('notifyMainNumber') and settings.get('mainNotifyPhone'):
            await send_text_message(settings['mainNotifyPhone'], notification, token, vendor_uid)
            await db.chatbot_leads.update_one(
                {"id": lead['id']},
                {"$set": {"notificationSent": True}}
            )

        # Notify category employee
        if lead.get('categoryId'):
            category = await db.chatbot_categories.find_one({"id": lead['categoryId']})
            if category and category.get('employeePhone'):
                await send_text_message(category['employeePhone'], notification, token, vendor_uid)
                await db.chatbot_leads.update_one(
                    {"id": lead['id']},
                    {"$set": {"employeeNotified": True}}
                )

    except Exception as e:
        logger.error(f"Error sending lead notification: {e}")


def build_lead_notification(lead: dict) -> str:
    """Build notification message text from lead data"""
    lines = [
        "--- *New Lead Received* ---",
        "",
        f"Phone: {lead.get('clientPhone', 'Unknown')}",
    ]

    if lead.get('clientName'):
        lines.append(f"Name: {lead['clientName']}")

    if lead.get('categoryName'):
        lines.append(f"Category: {lead['categoryName']}")

    if lead.get('productName'):
        lines.append(f"Product: {lead['productName']}")

    answers = lead.get('answers', [])
    if answers:
        lines.append("")
        lines.append("*Conversation:*")
        for a in answers:
            lines.append(f"Q: {a.get('questionText', '')}")
            lines.append(f"A: {a.get('answer', '')}")
            lines.append("")

    lines.append("---")
    return "\n".join(lines)


async def process_chatbot_followups():
    """Background job: send follow-up messages to abandoned conversations"""
    try:
        now = datetime.now(timezone.utc)

        # Find conversations that need follow-up
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
                # Max follow-ups reached, abandon
                await db.chatbot_conversations.update_one(
                    {"id": conv['id']},
                    {"$set": {
                        "status": ConversationStatus.ABANDONED.value,
                        "nextFollowUpAt": None,
                        "updatedAt": now.isoformat()
                    }}
                )
                # Save partial lead
                await create_lead_from_conversation(conv['id'])
                continue

            token, vendor_uid = await get_user_credentials(user_id)
            if not token or not vendor_uid:
                continue

            follow_up_msg = settings.get('followUpMessage', 'Hi! Would you like to continue?')
            await send_text_message(conv['clientPhone'], follow_up_msg, token, vendor_uid)

            # Schedule next follow-up
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

        # Also schedule follow-ups for conversations that haven't been contacted yet
        delay_threshold = now - timedelta(minutes=5)  # Default 5 min for initial check
        idle_convs = await db.chatbot_conversations.find({
            "status": ConversationStatus.ACTIVE.value,
            "nextFollowUpAt": None,
            "lastMessageAt": {"$lte": delay_threshold.isoformat()},
            "currentStep": {"$ne": "completed"}
        }).to_list(100)

        for conv in idle_convs:
            user_id = conv['userId']
            settings = await db.chatbot_settings.find_one({"userId": user_id})
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
    """Start the background scheduler for chatbot follow-ups"""
    logger.info("Chatbot follow-up scheduler started")
    while True:
        try:
            await process_chatbot_followups()
        except Exception as e:
            logger.error(f"Chatbot scheduler error: {e}")
        await asyncio.sleep(60)  # Check every minute
