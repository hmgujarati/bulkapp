"""Fetch templates from the user's BizChat account.

Exposes GET /api/templates which proxies BizChat's
`{apiBase}/{vendorUid}/contact/template-list` endpoint and returns a
normalized list so the frontend can auto-fill both template name AND
template language (eliminating the #1 source of 422 errors).
"""
from fastapi import APIRouter, HTTPException, Depends
import httpx
import logging
import os

from utils.auth import get_current_user
from utils.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["Templates"])

BIZCHAT_API_BASE = os.environ.get('BIZCHAT_API_BASE', 'https://bizchatapi.in/api')


def _normalize_template(raw: dict) -> dict:
    """Normalize a single template entry from BizChat's response into
    a predictable shape for the frontend. Different BizChat accounts may
    return slightly different keys; we defensively support the common ones.
    """
    name = raw.get('name') or raw.get('template_name') or raw.get('elementName') or ''
    language = (
        raw.get('language')
        or raw.get('template_language')
        or raw.get('language_code')
        or raw.get('languageCode')
        or 'en'
    )
    status = raw.get('status') or raw.get('review_status') or ''
    category = raw.get('category') or ''
    # Components (header / body / footer / buttons) — pass through if present
    components = raw.get('components') or raw.get('template_components') or []
    return {
        "name": name,
        "language": language,
        "status": status,
        "category": category,
        "components": components,
    }


def _extract_template_list(payload) -> list:
    """BizChat responses vary: some wrap the list, some don't. Try all common shapes.
    
    Known shape (bizchatapi.in):
      {"result": "success", "data": {"templateList": {"current_page": 1, "data": [...]}}}
    """
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    
    # Walk up to 3 levels looking for a list under common keys
    list_keys = ('data', 'templates', 'templateList', 'template_list', 'results', 'items')
    
    def walk(node, depth=0):
        if depth > 4 or not isinstance(node, dict):
            return None
        for k in list_keys:
            v = node.get(k)
            if isinstance(v, list):
                return v
            if isinstance(v, dict):
                found = walk(v, depth + 1)
                if found is not None:
                    return found
        return None
    
    return walk(payload) or []


@router.get("")
async def get_bizchat_templates(current_user = Depends(get_current_user)):
    """Fetch the authenticated user's approved WhatsApp templates from BizChat."""
    user = await db.users.find_one({"id": current_user.userId})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    token = user.get('bizChatToken')
    vendor_uid = user.get('bizChatVendorUID')
    
    if not token or not vendor_uid:
        raise HTTPException(
            status_code=400,
            detail="BizChat credentials not configured. Please set them in Settings."
        )
    
    url = f"{BIZCHAT_API_BASE}/{vendor_uid}/contact/template-list?token={token}"
    
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url)
        
        if response.status_code != 200:
            logger.warning(
                f"BizChat template-list returned {response.status_code}: "
                f"{response.text[:300]}"
            )
            raise HTTPException(
                status_code=502,
                detail=f"BizChat returned {response.status_code}. Please verify your API token and vendor UID."
            )
        
        try:
            payload = response.json()
        except Exception:
            logger.error(f"BizChat template-list returned non-JSON: {response.text[:300]}")
            raise HTTPException(
                status_code=502,
                detail="Invalid response from BizChat. Please contact your BizChat provider."
            )
        
        raw_list = _extract_template_list(payload)
        templates = [_normalize_template(t) for t in raw_list if isinstance(t, dict)]
        # Only return templates with a name
        templates = [t for t in templates if t['name']]
        
        logger.info(f"Fetched {len(templates)} templates from BizChat for user {current_user.userId}")
        return {"templates": templates}
    
    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="BizChat did not respond in time. Please try again."
        )
    except Exception as e:
        logger.exception(f"Error fetching BizChat templates: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch templates: {type(e).__name__}"
        )
