"""File upload routes — object storage when configured, local disk otherwise."""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Response
from pathlib import Path
from datetime import datetime, timezone
import asyncio
import os
import uuid
import logging

from utils.auth import get_current_user
from utils.database import db
from utils.object_storage import put_object, get_object, APP_NAME

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["Upload"])

# Local fallback (self-hosted servers with persistent disk and no EMERGENT_LLM_KEY)
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"


def _object_storage_available() -> bool:
    return bool((os.environ.get("EMERGENT_LLM_KEY") or "").strip())

MIME_TYPES = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".gif": "image/gif", ".webp": "image/webp", ".mp4": "video/mp4",
    ".mov": "video/quicktime", ".avi": "video/x-msvideo", ".mkv": "video/x-matroska",
    ".webm": "video/webm", ".pdf": "application/pdf", ".txt": "text/plain",
    ".csv": "text/csv", ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


@router.post("/media")
async def upload_media(
    file: UploadFile = File(...),
    media_type: str = "image",
    current_user = Depends(get_current_user)
):
    """Upload media to object storage and return a public URL usable by WhatsApp"""
    try:
        if media_type not in ["image", "video", "document"]:
            raise HTTPException(status_code=400, detail="Invalid media type")

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

        size_limits = {
            "image": 5 * 1024 * 1024,
            "video": 16 * 1024 * 1024,
            "document": 10 * 1024 * 1024
        }

        file_content = await file.read()
        file_size = len(file_content)
        max_size = size_limits[media_type]
        if file_size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size for {media_type}: {max_size / (1024 * 1024):.1f}MB. "
                       f"Your file: {file_size / (1024 * 1024):.1f}MB"
            )

        client_type = (file.content_type or "").strip().lower()
        if not client_type or client_type == "application/octet-stream":
            client_type = MIME_TYPES.get(file_ext, "application/octet-stream")
        content_type = client_type
        file_id = f"{uuid.uuid4()}{file_ext}"

        def _save_local():
            local_dir = UPLOAD_DIR / f"{media_type}s"
            local_dir.mkdir(parents=True, exist_ok=True)
            (local_dir / file_id).write_bytes(file_content)
            return {
                "success": True,
                "filename": file.filename,
                "url": f"/api/uploads/{media_type}s/{file_id}",
                "type": media_type
            }

        if not _object_storage_available():
            # Self-hosted fallback: persistent local disk
            logger.info(f"Object storage not configured, saving {media_type} locally: {file_id}")
            return _save_local()

        storage_path = f"{APP_NAME}/uploads/{current_user.userId}/{file_id}"

        try:
            result = await asyncio.to_thread(put_object, storage_path, file_content, content_type)
        except Exception as e:
            logger.error(f"Object storage upload failed ({e}), falling back to local disk")
            return _save_local()

        await db.media_files.insert_one({
            "id": file_id,
            "userId": current_user.userId,
            "storagePath": result["path"],
            "originalFilename": file.filename,
            "contentType": content_type,
            "size": file_size,
            "mediaType": media_type,
            "isDeleted": False,
            "createdAt": datetime.now(timezone.utc).isoformat()
        })

        return {
            "success": True,
            "filename": file.filename,
            "url": f"/api/upload/media/{file_id}",
            "type": media_type
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.get("/media/{file_id}")
async def serve_media(file_id: str):
    """Public media URL — WhatsApp/BizChat servers fetch templates media from here"""
    record = await db.media_files.find_one({"id": file_id, "isDeleted": False})
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    try:
        data, content_type = await asyncio.to_thread(get_object, record["storagePath"])
    except Exception as e:
        logger.error(f"Error fetching media {file_id}: {str(e)}")
        raise HTTPException(status_code=404, detail="File not found")
    return Response(
        content=data,
        media_type=record.get("contentType") or content_type,
        headers={"Cache-Control": "public, max-age=86400"}
    )
