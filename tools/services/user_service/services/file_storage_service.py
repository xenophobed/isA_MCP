"""
MinIO File Storage Service

基于MinIO的文件存储服务，与S3兼容
提供文件上传、下载、删除等功能
"""

import os
import uuid
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from urllib.parse import quote

from minio import Minio
from minio.error import S3Error
from fastapi import UploadFile

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_config
from tools.services.user_service.services.base import ServiceResult, ServiceStatus

logger = logging.getLogger(__name__)


class FileStorageService:
    """MinIO文件存储服务"""
    
    def __init__(self):
        self.config = get_config()
        
        # MinIO配置 - 与S3兼容
        self.minio_client = Minio(
            endpoint=self.config.minio_endpoint,
            access_key=self.config.minio_access_key,
            secret_key=self.config.minio_secret_key,
            secure=self.config.minio_secure
        )
        
        self.bucket_name = self.config.minio_bucket_name
        
        # 支持的文件类型
        self.allowed_types = [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'application/pdf',
            'text/plain', 'text/csv',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/json'
        ]
        
        # 最大文件大小 (50MB)
        self.max_file_size = 50 * 1024 * 1024
        
        # 确保bucket存在
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """确保MinIO bucket存在"""
        try:
            if not self.minio_client.bucket_exists(self.bucket_name):
                self.minio_client.make_bucket(self.bucket_name)
                logger.info(f"Created MinIO bucket: {self.bucket_name}")
            else:
                logger.info(f"MinIO bucket already exists: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Error ensuring bucket exists: {e}")
            raise
    
    def _get_object_name(self, user_id: str, filename: str) -> str:
        """生成对象存储路径"""
        now = datetime.utcnow()
        year = now.strftime("%Y")
        month = now.strftime("%m")
        
        # 清理用户ID中的特殊字符
        safe_user_id = user_id.replace("|", "_").replace("/", "_")
        
        # 生成唯一文件名
        file_ext = Path(filename).suffix
        unique_filename = f"{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{file_ext}"
        
        return f"users/{safe_user_id}/files/{year}/{month}/{unique_filename}"
    
    def _validate_file(self, file: UploadFile, file_content: bytes) -> ServiceResult:
        """验证上传文件"""
        # 检查文件大小
        file_size = len(file_content)
        if file_size > self.max_file_size:
            return ServiceResult.validation_error(
                f"File too large. Maximum size: {self.max_file_size / (1024*1024):.1f}MB"
            )
        
        # 检查文件类型
        content_type = file.content_type
        if content_type not in self.allowed_types:
            return ServiceResult.validation_error(
                f"File type not allowed: {content_type}. Allowed types: {', '.join(self.allowed_types)}"
            )
        
        return ServiceResult.success(message="File validation passed")
    
    async def upload_file(self, user_id: str, file: UploadFile) -> ServiceResult:
        """
        上传文件到MinIO
        
        Args:
            user_id: 用户ID
            file: 上传的文件
            
        Returns:
            ServiceResult: 包含文件信息的结果
        """
        try:
            # 读取文件内容
            file_content = await file.read()
            
            # 验证文件
            validation_result = self._validate_file(file, file_content)
            if not validation_result.is_success:
                return validation_result
            
            # 生成对象名称
            object_name = self._get_object_name(user_id, file.filename)
            
            # 上传到MinIO
            from io import BytesIO
            file_stream = BytesIO(file_content)
            
            self.minio_client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=file_stream,
                length=len(file_content),
                content_type=file.content_type
            )
            
            # 生成预签名下载URL (1小时有效期)
            download_url = self.minio_client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=timedelta(hours=1)
            )
            
            # 创建响应数据
            file_id = str(uuid.uuid4())
            upload_time = datetime.utcnow()
            
            result_data = {
                "file_id": file_id,
                "file_path": object_name,
                "download_url": download_url,
                "file_size": len(file_content),
                "content_type": file.content_type,
                "uploaded_at": upload_time.isoformat()
            }
            
            return ServiceResult.success(
                data=result_data,
                message="File uploaded successfully"
            )
            
        except S3Error as e:
            logger.error(f"MinIO error uploading file: {e}")
            return ServiceResult.error(f"Storage error: {str(e)}")
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            return ServiceResult.error(f"Failed to upload file: {str(e)}")
    
    def list_user_files(self, user_id: str, prefix: str = "", limit: int = 100) -> ServiceResult:
        """
        列出用户文件
        
        Args:
            user_id: 用户ID
            prefix: 文件名前缀过滤
            limit: 返回文件数量限制
            
        Returns:
            ServiceResult: 包含文件列表的结果
        """
        try:
            # 清理用户ID
            safe_user_id = user_id.replace("|", "_").replace("/", "_")
            user_prefix = f"users/{safe_user_id}/files/"
            
            # 如果有额外前缀，添加到用户前缀后
            if prefix:
                search_prefix = f"{user_prefix}{prefix}"
            else:
                search_prefix = user_prefix
            
            # 列出对象
            objects = self.minio_client.list_objects(
                bucket_name=self.bucket_name,
                prefix=search_prefix,
                recursive=True
            )
            
            files = []
            count = 0
            
            for obj in objects:
                if count >= limit:
                    break
                
                # 生成预签名下载URL
                try:
                    download_url = self.minio_client.presigned_get_object(
                        bucket_name=self.bucket_name,
                        object_name=obj.object_name,
                        expires=timedelta(hours=1)
                    )
                except S3Error:
                    download_url = None
                
                # 推断content_type
                content_type, _ = mimetypes.guess_type(obj.object_name)
                
                file_info = {
                    "file_path": obj.object_name,
                    "file_size": obj.size,
                    "content_type": content_type or "application/octet-stream",
                    "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                    "etag": obj.etag,
                    "download_url": download_url
                }
                
                files.append(file_info)
                count += 1
            
            return ServiceResult.success(
                data=files,
                message=f"Retrieved {len(files)} files"
            )
            
        except S3Error as e:
            logger.error(f"MinIO error listing files: {e}")
            return ServiceResult.error(f"Storage error: {str(e)}")
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            return ServiceResult.error(f"Failed to list files: {str(e)}")
    
    def get_file_info(self, user_id: str, file_path: str) -> ServiceResult:
        """
        获取文件信息
        
        Args:
            user_id: 用户ID
            file_path: 文件路径
            
        Returns:
            ServiceResult: 包含文件信息的结果
        """
        try:
            # 验证文件属于该用户
            safe_user_id = user_id.replace("|", "_").replace("/", "_")
            if not file_path.startswith(f"users/{safe_user_id}/"):
                return ServiceResult.permission_denied(
                    "Access denied: File does not belong to user"
                )
            
            # 获取对象统计信息
            try:
                stat = self.minio_client.stat_object(
                    bucket_name=self.bucket_name,
                    object_name=file_path
                )
            except S3Error as e:
                if e.code == "NoSuchKey":
                    return ServiceResult.not_found("File not found")
                raise
            
            # 生成预签名下载URL
            download_url = self.minio_client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=file_path,
                expires=timedelta(hours=1)
            )
            
            # 推断content_type
            content_type, _ = mimetypes.guess_type(file_path)
            
            file_info = {
                "file_path": file_path,
                "file_size": stat.size,
                "content_type": content_type or stat.content_type or "application/octet-stream",
                "last_modified": stat.last_modified.isoformat() if stat.last_modified else None,
                "etag": stat.etag,
                "download_url": download_url
            }
            
            return ServiceResult.success(
                data=file_info,
                message="File info retrieved successfully"
            )
            
        except S3Error as e:
            logger.error(f"MinIO error getting file info: {e}")
            return ServiceResult.error(f"Storage error: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting file info: {str(e)}")
            return ServiceResult.error(f"Failed to get file info: {str(e)}")
    
    def delete_file(self, user_id: str, file_path: str) -> ServiceResult:
        """
        删除文件
        
        Args:
            user_id: 用户ID
            file_path: 文件路径
            
        Returns:
            ServiceResult: 删除结果
        """
        try:
            # 验证文件属于该用户
            safe_user_id = user_id.replace("|", "_").replace("/", "_")
            if not file_path.startswith(f"users/{safe_user_id}/"):
                return ServiceResult.permission_denied(
                    "Access denied: File does not belong to user"
                )
            
            # 检查文件是否存在
            try:
                self.minio_client.stat_object(
                    bucket_name=self.bucket_name,
                    object_name=file_path
                )
            except S3Error as e:
                if e.code == "NoSuchKey":
                    return ServiceResult.not_found("File not found")
                raise
            
            # 删除文件
            self.minio_client.remove_object(
                bucket_name=self.bucket_name,
                object_name=file_path
            )
            
            return ServiceResult.success(
                data={"file_path": file_path, "deleted": True},
                message="File deleted successfully"
            )
            
        except S3Error as e:
            logger.error(f"MinIO error deleting file: {e}")
            return ServiceResult.error(f"Storage error: {str(e)}")
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            return ServiceResult.error(f"Failed to delete file: {str(e)}")
    
    def get_download_url(self, user_id: str, file_path: str, expires_hours: int = 1) -> ServiceResult:
        """
        获取文件下载URL
        
        Args:
            user_id: 用户ID
            file_path: 文件路径
            expires_hours: URL过期时间(小时)
            
        Returns:
            ServiceResult: 包含下载URL的结果
        """
        try:
            # 验证文件属于该用户
            safe_user_id = user_id.replace("|", "_").replace("/", "_")
            if not file_path.startswith(f"users/{safe_user_id}/"):
                return ServiceResult.permission_denied(
                    "Access denied: File does not belong to user"
                )
            
            # 检查文件是否存在
            try:
                self.minio_client.stat_object(
                    bucket_name=self.bucket_name,
                    object_name=file_path
                )
            except S3Error as e:
                if e.code == "NoSuchKey":
                    return ServiceResult.not_found("File not found")
                raise
            
            # 生成预签名下载URL
            download_url = self.minio_client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=file_path,
                expires=timedelta(hours=expires_hours)
            )
            
            return ServiceResult.success(
                data={
                    "download_url": download_url,
                    "expires_in": expires_hours * 3600,  # 秒
                    "file_path": file_path
                },
                message="Download URL generated successfully"
            )
            
        except S3Error as e:
            logger.error(f"MinIO error getting download URL: {e}")
            return ServiceResult.error(f"Storage error: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting download URL: {str(e)}")
            return ServiceResult.error(f"Failed to get download URL: {str(e)}")