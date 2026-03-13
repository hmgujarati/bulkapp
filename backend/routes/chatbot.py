"""Chatbot routes - configuration, categories, products, flows, leads"""
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Request
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone
from typing import Optional, List
import logging
import csv
import io
import os
import uuid

from utils.database import db
from utils.auth import get_current_user
from models.chatbot_schemas import (
    ChatbotCategory, CategoryCreate, CategoryUpdate,
    ChatbotProduct, ProductCreate, ProductUpdate,
    FlowQuestion, FlowQuestionCreate, FlowQuestionUpdate,
    ChatbotSettings, ChatbotSettingsUpdate,
    ChatbotLeadStatus, LeadStatusUpdate
)

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])
logger = logging.getLogger(__name__)


# ============= SETTINGS =============

@router.get("/settings")
async def get_chatbot_settings(request: Request, current_user=Depends(get_current_user)):
    settings = await db.chatbot_settings.find_one({"userId": current_user.userId}, {"_id": 0})
    if not settings:
        default = ChatbotSettings(userId=current_user.userId)
        await db.chatbot_settings.insert_one(default.model_dump())
        settings = default.model_dump()

    # Generate webhook URL for this user
    base_url = os.environ.get('APP_URL', '').rstrip('/')
    if not base_url:
        # Fallback to request URL but use the forwarded host if behind proxy
        forwarded_host = request.headers.get('x-forwarded-host') or request.headers.get('host')
        forwarded_proto = request.headers.get('x-forwarded-proto', 'https')
        if forwarded_host:
            base_url = f"{forwarded_proto}://{forwarded_host}"
        else:
            base_url = str(request.base_url).rstrip('/')
    settings["webhookUrl"] = f"{base_url}/api/webhook/{current_user.userId}"

    return settings


@router.put("/settings")
async def update_chatbot_settings(data: ChatbotSettingsUpdate, current_user=Depends(get_current_user)):
    settings = await db.chatbot_settings.find_one({"userId": current_user.userId})
    if not settings:
        default = ChatbotSettings(userId=current_user.userId)
        await db.chatbot_settings.insert_one(default.model_dump())

    update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
    update_dict["updatedAt"] = datetime.now(timezone.utc).isoformat()

    await db.chatbot_settings.update_one(
        {"userId": current_user.userId},
        {"$set": update_dict}
    )
    return {"message": "Settings updated"}


# ============= CATEGORIES =============

@router.get("/categories")
async def get_categories(current_user=Depends(get_current_user)):
    categories = await db.chatbot_categories.find(
        {"userId": current_user.userId}, {"_id": 0}
    ).sort("sortOrder", 1).to_list(500)

    # Attach product count for each category
    for cat in categories:
        cat["productCount"] = await db.chatbot_products.count_documents({
            "userId": current_user.userId, "categoryId": cat["id"], "isActive": True
        })
        cat["questionCount"] = await db.chatbot_flow_questions.count_documents({
            "userId": current_user.userId, "categoryId": cat["id"]
        })

    return {"categories": categories}


@router.post("/categories")
async def create_category(data: CategoryCreate, current_user=Depends(get_current_user)):
    cat = ChatbotCategory(userId=current_user.userId, **data.model_dump())
    await db.chatbot_categories.insert_one(cat.model_dump())
    return {"message": "Category created", "id": cat.id}


@router.put("/categories/{category_id}")
async def update_category(category_id: str, data: CategoryUpdate, current_user=Depends(get_current_user)):
    cat = await db.chatbot_categories.find_one({"id": category_id, "userId": current_user.userId})
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
    update_dict["updatedAt"] = datetime.now(timezone.utc).isoformat()
    await db.chatbot_categories.update_one({"id": category_id}, {"$set": update_dict})
    return {"message": "Category updated"}


@router.delete("/categories/{category_id}")
async def delete_category(category_id: str, current_user=Depends(get_current_user)):
    result = await db.chatbot_categories.delete_one({"id": category_id, "userId": current_user.userId})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")

    # Also delete products and flow questions in this category
    await db.chatbot_products.delete_many({"userId": current_user.userId, "categoryId": category_id})
    await db.chatbot_flow_questions.delete_many({"userId": current_user.userId, "categoryId": category_id})
    return {"message": "Category and related items deleted"}


# ============= PRODUCTS =============

@router.get("/products")
async def get_products(
    current_user=Depends(get_current_user),
    category_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200)
):
    query = {"userId": current_user.userId}
    if category_id:
        query["categoryId"] = category_id
    if search:
        query["name"] = {"$regex": search, "$options": "i"}

    skip = (page - 1) * limit
    products = await db.chatbot_products.find(query, {"_id": 0}).sort("name", 1).skip(skip).limit(limit).to_list(limit)
    total = await db.chatbot_products.count_documents(query)

    return {"products": products, "total": total, "page": page, "totalPages": (total + limit - 1) // limit}


@router.post("/products")
async def create_product(data: ProductCreate, current_user=Depends(get_current_user)):
    # Verify category exists
    cat = await db.chatbot_categories.find_one({"id": data.categoryId, "userId": current_user.userId})
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    prod = ChatbotProduct(userId=current_user.userId, **data.model_dump())
    await db.chatbot_products.insert_one(prod.model_dump())
    return {"message": "Product created", "id": prod.id}


@router.put("/products/{product_id}")
async def update_product(product_id: str, data: ProductUpdate, current_user=Depends(get_current_user)):
    prod = await db.chatbot_products.find_one({"id": product_id, "userId": current_user.userId})
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")

    update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
    update_dict["updatedAt"] = datetime.now(timezone.utc).isoformat()
    await db.chatbot_products.update_one({"id": product_id}, {"$set": update_dict})
    return {"message": "Product updated"}


@router.delete("/products/{product_id}")
async def delete_product(product_id: str, current_user=Depends(get_current_user)):
    result = await db.chatbot_products.delete_one({"id": product_id, "userId": current_user.userId})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted"}


@router.post("/products/bulk-upload")
async def bulk_upload_products(file: UploadFile = File(...), current_user=Depends(get_current_user)):
    """Upload products via CSV. Columns: Category, Product Name, Description, Price"""
    if not file.filename.endswith(('.csv', '.txt')):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    content = await file.read()
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        text = content.decode('utf-8-sig')

    reader = csv.DictReader(io.StringIO(text))
    created_count = 0
    errors = []

    # Cache categories by name
    category_cache = {}

    for row_num, row in enumerate(reader, 2):
        cat_name = (row.get('Category') or row.get('category') or '').strip()
        prod_name = (row.get('Product Name') or row.get('product_name') or row.get('name') or '').strip()

        if not cat_name or not prod_name:
            errors.append(f"Row {row_num}: Missing Category or Product Name")
            continue

        # Get or create category
        if cat_name not in category_cache:
            existing_cat = await db.chatbot_categories.find_one({
                "userId": current_user.userId,
                "name": {"$regex": f"^{cat_name}$", "$options": "i"}
            })
            if existing_cat:
                category_cache[cat_name] = existing_cat['id']
            else:
                new_cat = ChatbotCategory(userId=current_user.userId, name=cat_name)
                await db.chatbot_categories.insert_one(new_cat.model_dump())
                category_cache[cat_name] = new_cat.id

        category_id = category_cache[cat_name]
        description = (row.get('Description') or row.get('description') or '').strip() or None
        price = (row.get('Price') or row.get('price') or '').strip() or None

        prod = ChatbotProduct(
            userId=current_user.userId,
            categoryId=category_id,
            name=prod_name,
            description=description,
            price=price
        )
        await db.chatbot_products.insert_one(prod.model_dump())
        created_count += 1

    return {
        "message": f"Uploaded {created_count} products",
        "created": created_count,
        "errors": errors[:20]  # Return max 20 errors
    }


@router.delete("/products/bulk-delete")
async def bulk_delete_products(
    category_id: Optional[str] = Query(None),
    current_user=Depends(get_current_user)
):
    """Delete all products (optionally filtered by category)"""
    query = {"userId": current_user.userId}
    if category_id:
        query["categoryId"] = category_id

    result = await db.chatbot_products.delete_many(query)
    return {"message": f"Deleted {result.deleted_count} products"}


# ============= FLOW QUESTIONS =============

@router.get("/questions/{category_id}")
async def get_questions(category_id: str, current_user=Depends(get_current_user)):
    questions = await db.chatbot_flow_questions.find(
        {"userId": current_user.userId, "categoryId": category_id}, {"_id": 0}
    ).sort("sortOrder", 1).to_list(50)
    return {"questions": questions}


@router.post("/questions")
async def create_question(data: FlowQuestionCreate, current_user=Depends(get_current_user)):
    # Verify category
    cat = await db.chatbot_categories.find_one({"id": data.categoryId, "userId": current_user.userId})
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    q = FlowQuestion(userId=current_user.userId, **data.model_dump())
    await db.chatbot_flow_questions.insert_one(q.model_dump())
    return {"message": "Question created", "id": q.id}


@router.put("/questions/{question_id}")
async def update_question(question_id: str, data: FlowQuestionUpdate, current_user=Depends(get_current_user)):
    q = await db.chatbot_flow_questions.find_one({"id": question_id, "userId": current_user.userId})
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
    await db.chatbot_flow_questions.update_one({"id": question_id}, {"$set": update_dict})
    return {"message": "Question updated"}


@router.delete("/questions/{question_id}")
async def delete_question(question_id: str, current_user=Depends(get_current_user)):
    result = await db.chatbot_flow_questions.delete_one({"id": question_id, "userId": current_user.userId})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Question not found")
    return {"message": "Question deleted"}


@router.put("/questions/reorder/{category_id}")
async def reorder_questions(category_id: str, question_ids: List[str], current_user=Depends(get_current_user)):
    """Reorder questions by providing ordered list of question IDs"""
    for i, qid in enumerate(question_ids):
        await db.chatbot_flow_questions.update_one(
            {"id": qid, "userId": current_user.userId, "categoryId": category_id},
            {"$set": {"sortOrder": i}}
        )
    return {"message": "Questions reordered"}


# ============= LEADS =============

@router.get("/leads")
async def get_leads(
    current_user=Depends(get_current_user),
    status: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    query = {"userId": current_user.userId}
    if status:
        query["status"] = status
    if category_id:
        query["categoryId"] = category_id
    if search:
        query["$or"] = [
            {"clientPhone": {"$regex": search, "$options": "i"}},
            {"clientName": {"$regex": search, "$options": "i"}},
            {"productName": {"$regex": search, "$options": "i"}},
        ]

    skip = (page - 1) * limit
    leads = await db.chatbot_leads.find(query, {"_id": 0}).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.chatbot_leads.count_documents(query)

    stats = {
        "total": await db.chatbot_leads.count_documents({"userId": current_user.userId}),
        "new": await db.chatbot_leads.count_documents({"userId": current_user.userId, "status": "new"}),
        "qualified": await db.chatbot_leads.count_documents({"userId": current_user.userId, "status": "qualified"}),
        "contacted": await db.chatbot_leads.count_documents({"userId": current_user.userId, "status": "contacted"}),
    }

    return {
        "leads": leads,
        "total": total,
        "page": page,
        "totalPages": (total + limit - 1) // limit,
        "stats": stats
    }


@router.put("/leads/{lead_id}")
async def update_lead(lead_id: str, data: LeadStatusUpdate, current_user=Depends(get_current_user)):
    lead = await db.chatbot_leads.find_one({"id": lead_id, "userId": current_user.userId})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
    update_dict["updatedAt"] = datetime.now(timezone.utc).isoformat()
    await db.chatbot_leads.update_one({"id": lead_id}, {"$set": update_dict})
    return {"message": "Lead updated"}


@router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str, current_user=Depends(get_current_user)):
    result = await db.chatbot_leads.delete_one({"id": lead_id, "userId": current_user.userId})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"message": "Lead deleted"}


@router.get("/leads/export")
async def export_leads(
    current_user=Depends(get_current_user),
    status: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None)
):
    """Export leads as CSV (Excel-compatible)"""
    query = {"userId": current_user.userId}
    if status:
        query["status"] = status
    if category_id:
        query["categoryId"] = category_id
    if date_from or date_to:
        date_filter = {}
        if date_from:
            date_filter["$gte"] = date_from
        if date_to:
            date_filter["$lte"] = date_to
        if date_filter:
            query["createdAt"] = date_filter

    leads = await db.chatbot_leads.find(query, {"_id": 0}).sort("createdAt", -1).to_list(10000)

    # Build CSV
    output = io.StringIO()
    # Collect all unique question texts for headers
    all_questions = set()
    for lead in leads:
        for a in lead.get('answers', []):
            all_questions.add(a.get('questionText', ''))

    question_headers = sorted(all_questions)
    headers = ["Phone", "Name", "Category", "Product", "Status", "Date"] + question_headers + ["Notes"]

    writer = csv.writer(output)
    writer.writerow(headers)

    for lead in leads:
        answer_map = {a.get('questionText', ''): a.get('answer', '') for a in lead.get('answers', [])}
        row = [
            lead.get('clientPhone', ''),
            lead.get('clientName', ''),
            lead.get('categoryName', ''),
            lead.get('productName', ''),
            lead.get('status', ''),
            lead.get('createdAt', '')[:19],
        ]
        for q in question_headers:
            row.append(answer_map.get(q, ''))
        row.append(lead.get('notes', ''))
        writer.writerow(row)

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename=chatbot_leads.csv'}
    )


# ============= STATS =============

@router.get("/stats")
async def get_chatbot_stats(current_user=Depends(get_current_user)):
    categories = await db.chatbot_categories.count_documents({"userId": current_user.userId})
    products = await db.chatbot_products.count_documents({"userId": current_user.userId})
    total_leads = await db.chatbot_leads.count_documents({"userId": current_user.userId})
    active_convs = await db.chatbot_conversations.count_documents({
        "userId": current_user.userId,
        "status": {"$in": ["active", "followup_pending"]}
    })

    return {
        "categories": categories,
        "products": products,
        "totalLeads": total_leads,
        "activeConversations": active_convs
    }
