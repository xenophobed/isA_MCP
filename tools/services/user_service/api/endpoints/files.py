"""
File Management Endpoints

File-related functionality extracted from api_server.py
Handles file upload, download, listing, and deletion
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/users/{user_id}/files", tags=["Files"])


@router.post("/upload", response_model=Dict[str, Any])
async def upload_file(
    user_id: str,
    file: UploadFile = File(...),
    current_user=None,
    file_storage_service=None
):
    """Upload file - Original: api_server.py lines 1781-1826"""
    try:
        if not current_user or not file_storage_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        if current_user["sub"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to upload files for this user")
            
        result = await file_storage_service.upload_file(user_id, file)
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "success": True,
            "file_info": result.data,
            "message": result.message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.get("", response_model=Dict[str, Any])
async def list_user_files(
    user_id: str,
    prefix: str = "",
    limit: int = 100,
    current_user=None,
    file_storage_service=None
):
    """List user files - Original: api_server.py lines 1827-1873"""
    try:
        if not current_user or not file_storage_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        if current_user["sub"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to view files for this user")
            
        result = file_storage_service.list_user_files(user_id, prefix, limit)
        
        if not result.is_success:
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "files": result.data,
            "count": len(result.data),
            "user_id": user_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.get("/info", response_model=Dict[str, Any])
async def get_file_info(
    user_id: str,
    file_path: str,
    current_user=None,
    file_storage_service=None
):
    """Get file info - Original: api_server.py lines 1874-1924"""
    try:
        if not current_user or not file_storage_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        if current_user["sub"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to access files for this user")
            
        result = file_storage_service.get_file_info(user_id, file_path)
        
        if not result.is_success:
            if "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "file_info": result.data,
            "message": result.message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get file info: {str(e)}")


@router.delete("", response_model=Dict[str, Any])
async def delete_file(
    user_id: str,
    file_path: str,
    current_user=None,
    file_storage_service=None
):
    """Delete file - Original: api_server.py lines 1925-1975"""
    try:
        if not current_user or not file_storage_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        if current_user["sub"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete files for this user")
            
        result = file_storage_service.delete_file(user_id, file_path)
        
        if not result.is_success:
            if "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            raise HTTPException(status_code=400, detail=result.message)
            
        return {
            "success": True,
            "deleted_file": result.data,
            "message": result.message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@router.get("/download")
async def get_download_url(
    user_id: str,
    file_path: str,
    expires_hours: int = 1,
    current_user=None,
    file_storage_service=None
):
    """Get file download URL - Original: api_server.py lines 1976-2026"""
    try:
        if not current_user or not file_storage_service:
            raise HTTPException(status_code=500, detail="Dependencies not properly injected")
            
        if current_user["sub"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to download files for this user")
            
        result = file_storage_service.get_download_url(user_id, file_path, expires_hours)
        
        if not result.is_success:
            if "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            raise HTTPException(status_code=400, detail=result.message)
            
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=result.data["download_url"], status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting download URL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get download URL: {str(e)}")