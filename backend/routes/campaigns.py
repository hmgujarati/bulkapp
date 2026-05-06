"""Campaign management routes"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from datetime import datetime, timezone

from models.schemas import Role, CampaignStatus
from utils.auth import get_current_user
from utils.database import db

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


@router.get("")
async def get_campaigns(current_user = Depends(get_current_user)):
    """Get all campaigns for the current user (or all if admin).
    
    PERFORMANCE: This endpoint MUST NOT return the `recipients` array — it can be
    huge (8000+ entries per campaign) and the list view doesn't display them.
    For full recipient details, use GET /campaigns/{campaign_id}.
    """
    query = {}
    if current_user.role != Role.ADMIN:
        query['userId'] = current_user.userId
    
    # Lightweight projection: only fields the list/history page actually displays
    projection = {
        "_id": 0,
        "id": 1,
        "userId": 1,
        "name": 1,
        "status": 1,
        "templateName": 1,
        "templateLanguage": 1,
        "totalCount": 1,
        "sentCount": 1,
        "failedCount": 1,
        "deliveredCount": 1,
        "readCount": 1,
        "pendingCount": 1,
        "createdAt": 1,
        "completedAt": 1,
        "scheduledAt": 1,
        "lastHeartbeatAt": 1,
        "error": 1,
    }
    
    campaigns = await db.campaigns.find(query, projection).sort("createdAt", -1).to_list(100)
    return {"campaigns": campaigns}


@router.get("/summary")
async def get_dashboard_summary(current_user = Depends(get_current_user)):
    """Compact dashboard summary: 5 most recent campaigns + lifetime aggregate stats.
    
    Returns ~1 KB. Optimized for the User Dashboard which previously fetched
    up to 100 full campaigns just to display 5.
    """
    user_filter = {} if current_user.role == Role.ADMIN else {"userId": current_user.userId}
    
    # Lifetime aggregate stats (across ALL campaigns of this user)
    pipeline = [
        {"$match": user_filter},
        {"$group": {
            "_id": None,
            "totalCampaigns": {"$sum": 1},
            "totalSent": {"$sum": "$sentCount"},
            "totalFailed": {"$sum": "$failedCount"},
            "totalDelivered": {"$sum": "$deliveredCount"},
            "totalRead": {"$sum": "$readCount"},
            "totalRecipients": {"$sum": "$totalCount"},
        }},
        {"$project": {"_id": 0}},
    ]
    stats_cursor = db.campaigns.aggregate(pipeline)
    stats = await stats_cursor.to_list(1)
    stats = stats[0] if stats else {
        "totalCampaigns": 0, "totalSent": 0, "totalFailed": 0,
        "totalDelivered": 0, "totalRead": 0, "totalRecipients": 0,
    }
    
    # 5 most recent campaigns (lightweight projection)
    recent_projection = {
        "_id": 0, "id": 1, "name": 1, "status": 1, "templateName": 1,
        "totalCount": 1, "sentCount": 1, "failedCount": 1, "deliveredCount": 1,
        "readCount": 1, "pendingCount": 1, "createdAt": 1, "completedAt": 1,
    }
    recent = await db.campaigns.find(user_filter, recent_projection).sort("createdAt", -1).to_list(5)
    
    return {"stats": stats, "recentCampaigns": recent}


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: str, current_user = Depends(get_current_user)):
    """Get a specific campaign"""
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Check access
    if current_user.role != Role.ADMIN and campaign['userId'] != current_user.userId:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return campaign


@router.get("/{campaign_id}/stats")
async def get_campaign_stats(campaign_id: str, current_user = Depends(get_current_user)):
    """Get campaign statistics"""
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Check access
    if current_user.role != Role.ADMIN and campaign['userId'] != current_user.userId:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "campaignId": campaign_id,
        "name": campaign['name'],
        "totalCount": campaign['totalCount'],
        "sentCount": campaign['sentCount'],
        "failedCount": campaign['failedCount'],
        "pendingCount": campaign['pendingCount'],
        "status": campaign['status']
    }


@router.post("/{campaign_id}/pause")
async def pause_campaign(campaign_id: str, current_user = Depends(get_current_user)):
    """Pause a running campaign"""
    campaign = await db.campaigns.find_one({"id": campaign_id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Check access
    if current_user.role != Role.ADMIN and campaign['userId'] != current_user.userId:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if campaign['status'] != CampaignStatus.PROCESSING.value:
        raise HTTPException(status_code=400, detail="Only processing campaigns can be paused")
    
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {"status": CampaignStatus.PAUSED.value}}
    )
    
    return {"message": "Campaign paused successfully"}


@router.post("/{campaign_id}/cancel")
async def cancel_campaign(campaign_id: str, current_user = Depends(get_current_user)):
    """Cancel a campaign"""
    campaign = await db.campaigns.find_one({"id": campaign_id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Check access
    if current_user.role != Role.ADMIN and campaign['userId'] != current_user.userId:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if campaign['status'] in [CampaignStatus.COMPLETED.value, CampaignStatus.CANCELLED.value]:
        raise HTTPException(status_code=400, detail="Campaign already completed or cancelled")
    
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {"status": CampaignStatus.CANCELLED.value}}
    )
    
    return {"message": "Campaign cancelled successfully"}


@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: str, current_user = Depends(get_current_user)):
    """Delete a campaign"""
    campaign = await db.campaigns.find_one({"id": campaign_id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Check access
    if current_user.role != Role.ADMIN and campaign['userId'] != current_user.userId:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Delete campaign (does NOT affect daily usage count)
    await db.campaigns.delete_one({"id": campaign_id})
    
    return {"message": "Campaign deleted successfully"}
