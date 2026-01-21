"""File upload routes"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pathlib import Path
import uuid
import logging

from utils.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["Upload"])

# Upload directory
ROOT_DIR = Path(__file__).parent.parent
UPLOAD_DIR = ROOT_DIR / "uploads"

# Ensure directories exist
UPLOAD_DIR.mkdir(exist_ok=True)
(UPLOAD_DIR / "images").mkdir(exist_ok=True)
(UPLOAD_DIR / "videos").mkdir(exist_ok=True)
(UPLOAD_DIR / "documents").mkdir(exist_ok=True)


@router.post("/media")
async def upload_media(
    file: UploadFile = File(...),
    media_type: str = "image",
    current_user = Depends(get_current_user)
):
    """Upload media file and return URL"""
    try:
        # Validate media type
        if media_type not in ["image", "video", "document"]:
            raise HTTPException(status_code=400, detail="Invalid media type")
        
        # Validate file type
        allowed_extensions = {
            "image": [".jpg", ".jpeg", ".png", ".gif", ".webp"],
            "video": [".mp4", ".mov", ".avi", ".mkv", ".webm"],
            "document": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".csv"]
        }
        
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in allowed_extensions[media_type]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions[media_type])}"
            )
        
        # File size limits
        size_limits = {
            "image": 5 * 1024 * 1024,
            "video": 16 * 1024 * 1024,
            "document": 10 * 1024 * 1024
        }
        
        # Read and validate file size
        file_content = await file.read()
        file_size = len(file_content)
        
        max_size = size_limits[media_type]
        if file_size > max_size:
            max_size_mb = max_size / (1024 * 1024)
            actual_size_mb = file_size / (1024 * 1024)
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size for {media_type}: {max_size_mb:.1f}MB. Your file: {actual_size_mb:.1f}MB"
            )
        
        # Save file
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = UPLOAD_DIR / f"{media_type}s" / unique_filename
        
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        file_url = f"/uploads/{media_type}s/{unique_filename}"
        
        return {
            "success": True,
            "filename": file.filename,
            "url": file_url,
            "type": media_type
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")
