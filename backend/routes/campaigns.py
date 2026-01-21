"""Campaign management routes"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from datetime import datetime, timezone

from models.schemas import Role, CampaignStatus
from utils.auth import get_current_user
from utils.database import db

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


@router.get("")
async def get_campaigns(current_user = Depends(get_current_user)):
    """Get all campaigns for the current user (or all if admin)"""
    query = {}
    if current_user.role != Role.ADMIN:
        query['userId'] = current_user.userId
    
    campaigns = await db.campaigns.find(query, {"_id": 0}).sort("createdAt", -1).to_list(100)
    return {"campaigns": campaigns}


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
