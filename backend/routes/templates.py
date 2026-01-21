"""Template management routes"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone

from models.schemas import SavedTemplate, SavedTemplateCreate
from utils.auth import get_current_user
from utils.database import db

router = APIRouter(prefix="/saved-templates", tags=["Templates"])


@router.post("")
async def create_saved_template(template_data: SavedTemplateCreate, current_user = Depends(get_current_user)):
    """Create a new saved template"""
    # Check if name already exists for this user
    existing = await db.saved_templates.find_one({"userId": current_user.userId, "name": template_data.name})
    if existing:
        raise HTTPException(status_code=400, detail="Template name already exists")
    
    template = SavedTemplate(
        userId=current_user.userId,
        **template_data.model_dump()
    )
    
    template_dict = template.model_dump()
    template_dict['createdAt'] = template_dict['createdAt'].isoformat()
    template_dict['updatedAt'] = template_dict['updatedAt'].isoformat()
    
    await db.saved_templates.insert_one(template_dict)
    
    return {"message": "Template saved successfully", "templateId": template.id}


@router.get("")
async def get_saved_templates(current_user = Depends(get_current_user)):
    """Get all saved templates for the current user"""
    templates = await db.saved_templates.find(
        {"userId": current_user.userId},
        {"_id": 0}
    ).sort("createdAt", -1).to_list(100)
    
    return {"templates": templates}


@router.get("/{template_id}")
async def get_saved_template(template_id: str, current_user = Depends(get_current_user)):
    """Get a specific saved template"""
    template = await db.saved_templates.find_one(
        {"id": template_id, "userId": current_user.userId},
        {"_id": 0}
    )
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return template


@router.put("/{template_id}")
async def update_saved_template(
    template_id: str,
    template_data: SavedTemplateCreate,
    current_user = Depends(get_current_user)
):
    """Update a saved template"""
    # Check ownership
    template = await db.saved_templates.find_one({"id": template_id, "userId": current_user.userId})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Check if new name conflicts with another template
    if template_data.name != template['name']:
        existing = await db.saved_templates.find_one({
            "userId": current_user.userId,
            "name": template_data.name,
            "id": {"$ne": template_id}
        })
        if existing:
            raise HTTPException(status_code=400, detail="Template name already exists")
    
    update_dict = template_data.model_dump()
    update_dict['updatedAt'] = datetime.now(timezone.utc).isoformat()
    
    await db.saved_templates.update_one(
        {"id": template_id},
        {"$set": update_dict}
    )
    
    return {"message": "Template updated successfully"}


@router.delete("/{template_id}")
async def delete_saved_template(template_id: str, current_user = Depends(get_current_user)):
    """Delete a saved template"""
    result = await db.saved_templates.delete_one({"id": template_id, "userId": current_user.userId})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {"message": "Template deleted successfully"}
