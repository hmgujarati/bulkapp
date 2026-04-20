"""Chatbot routes - simplified: flows, settings, leads"""
from fastapi import APIRouter, HTTPException, Depends, Query, Request
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
    ChatbotFlow, FlowCreate, FlowUpdate, FlowQuestionItem,
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

    base_url = os.environ.get('APP_URL', '').rstrip('/')
    if not base_url:
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
    await db.chatbot_settings.update_one({"userId": current_user.userId}, {"$set": update_dict})
    return {"message": "Settings updated"}


# ============= FLOWS =============

@router.get("/flows")
async def get_flows(current_user=Depends(get_current_user)):
    flows = await db.chatbot_flows.find(
        {"userId": current_user.userId}, {"_id": 0}
    ).sort("createdAt", -1).to_list(500)
    return {"flows": flows}


@router.get("/flows/{flow_id}")
async def get_flow(flow_id: str, current_user=Depends(get_current_user)):
    flow = await db.chatbot_flows.find_one(
        {"id": flow_id, "userId": current_user.userId}, {"_id": 0}
    )
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    return flow


@router.post("/flows")
async def create_flow(data: FlowCreate, current_user=Depends(get_current_user)):
    # Build questions with IDs
    questions = []
    for q in data.questions:
        questions.append(FlowQuestionItem(
            questionText=q.questionText,
            questionType=q.questionType,
            options=q.options
        ).model_dump())

    flow = ChatbotFlow(userId=current_user.userId, **data.model_dump(exclude={'questions'}))
    flow_dict = flow.model_dump()
    flow_dict['questions'] = questions
    await db.chatbot_flows.insert_one(flow_dict)
    return {"message": "Flow created", "id": flow.id}


@router.put("/flows/{flow_id}")
async def update_flow(flow_id: str, data: FlowUpdate, current_user=Depends(get_current_user)):
    flow = await db.chatbot_flows.find_one({"id": flow_id, "userId": current_user.userId})
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    update_dict = {}
    for k, v in data.model_dump().items():
        if v is not None:
            if k == 'questions':
                # Rebuild questions with IDs
                questions = []
                for q in v:
                    questions.append(FlowQuestionItem(
                        questionText=q['questionText'] if isinstance(q, dict) else q.questionText,
                        questionType=q['questionType'] if isinstance(q, dict) else q.questionType,
                        options=q['options'] if isinstance(q, dict) else q.options
                    ).model_dump())
                update_dict['questions'] = questions
            else:
                update_dict[k] = v

    update_dict["updatedAt"] = datetime.now(timezone.utc).isoformat()
    await db.chatbot_flows.update_one({"id": flow_id}, {"$set": update_dict})
    return {"message": "Flow updated"}


@router.delete("/flows/{flow_id}")
async def delete_flow(flow_id: str, current_user=Depends(get_current_user)):
    result = await db.chatbot_flows.delete_one({"id": flow_id, "userId": current_user.userId})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Flow not found")
    return {"message": "Flow deleted"}


# ============= LEADS =============

@router.get("/leads")
async def get_leads(
    current_user=Depends(get_current_user),
    status: Optional[str] = Query(None),
    flow_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    query = {"userId": current_user.userId}
    if status:
        query["status"] = status
    if flow_id:
        query["flowId"] = flow_id
    if search:
        query["$or"] = [
            {"clientPhone": {"$regex": search, "$options": "i"}},
            {"clientName": {"$regex": search, "$options": "i"}},
            {"flowName": {"$regex": search, "$options": "i"}},
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
    flow_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None)
):
    query = {"userId": current_user.userId}
    if status:
        query["status"] = status
    if flow_id:
        query["flowId"] = flow_id
    if date_from or date_to:
        date_filter = {}
        if date_from:
            date_filter["$gte"] = date_from
        if date_to:
            date_filter["$lte"] = date_to
        if date_filter:
            query["createdAt"] = date_filter

    leads = await db.chatbot_leads.find(query, {"_id": 0}).sort("createdAt", -1).to_list(10000)

    output = io.StringIO()
    all_questions = set()
    for lead in leads:
        for a in lead.get('answers', []):
            all_questions.add(a.get('questionText', ''))

    question_headers = sorted(all_questions)
    headers = ["Phone", "Name", "Flow", "Status", "Date"] + question_headers + ["Notes"]

    writer = csv.writer(output)
    writer.writerow(headers)

    for lead in leads:
        answer_map = {a.get('questionText', ''): a.get('answer', '') for a in lead.get('answers', [])}
        row = [
            lead.get('clientPhone', ''),
            lead.get('clientName', ''),
            lead.get('flowName', ''),
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
    total_flows = await db.chatbot_flows.count_documents({"userId": current_user.userId})
    active_flows = await db.chatbot_flows.count_documents({"userId": current_user.userId, "isActive": True})
    total_leads = await db.chatbot_leads.count_documents({"userId": current_user.userId})
    active_convs = await db.chatbot_conversations.count_documents({
        "userId": current_user.userId,
        "status": {"$in": ["active", "followup_pending"]}
    })

    return {
        "totalFlows": total_flows,
        "activeFlows": active_flows,
        "totalLeads": total_leads,
        "activeConversations": active_convs
    }
