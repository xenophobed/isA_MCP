# app/services/file.py
from typing import Optional, Dict, List, BinaryIO
from fastapi import UploadFile
from app.models.knowledge.file import FileMetadata, FileStatus, FileType
from app.repositories.knowledge.kb_file_repo import KnowledgeFileRepository
import aiofiles
import os
import hashlib
import magic
import fitz
import docx
import chardet
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from app.config.config_manager import config_manager
from io import BytesIO

class KnowledgeFileService:
    def __init__(
        self,
        repository: KnowledgeFileRepository,
        config: Dict = None
    ):
        self.repository = repository
        self.logger = config_manager.get_logger(__name__)
        self.minio_client = None
        self.config = config or config_manager.get_config('minio').get_storage_settings()
        
    async def _get_minio_client(self):
        """Get or create MinIO client"""
        if not self.minio_client:
            self.minio_client = await config_manager.get_storage_client()
        return self.minio_client

    async def save_file(
        self,
        file: UploadFile,
        prefix: str = "",
        category: str = "document",
        metadata: Dict = None
    ) -> Optional[FileMetadata]:
        """Save uploaded file to MinIO"""
        try:
            # Get MinIO client
            minio_client = await self._get_minio_client()
            
            # Generate file ID and path
            file_id = f"{prefix}_{uuid4().hex[:8]}" if prefix else f"file_{uuid4().hex[:8]}"
            extension = os.path.splitext(file.filename)[1].lower()
            storage_path = f"{category}/{file_id}{extension}"

            # Read file content
            content = await file.read()
            content_type = magic.from_buffer(content, mime=True)
            
            # Calculate checksum
            md5 = hashlib.md5()
            md5.update(content)
            checksum = md5.hexdigest()
            
            # Upload to MinIO
            content_stream = BytesIO(content)
            minio_client.put_object(
                bucket_name=self.config['bucket_name'],
                object_name=storage_path,
                data=content_stream,
                length=len(content),
                content_type=content_type
            )

            # Create file metadata with all required fields
            file_metadata = FileMetadata(
                file_id=file_id,
                filename=file.filename,
                original_name=file.filename,
                storage_path=storage_path,
                size=len(content),
                mime_type=content_type,
                checksum=checksum,
                metadata=metadata or {},
                status=FileStatus.ACTIVE,
                type=FileType.DOCUMENT,
                category="document",
                storage_type="minio",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

            # Add logging to help debug
            self.logger.debug(f"Saving file metadata: {file_metadata.dict(exclude_none=True)}")

            # Save metadata to repository
            try:
                success = await self.repository.save(file_metadata)
                if not success:
                    # Delete from MinIO if metadata save fails
                    minio_client.remove_object(
                        bucket_name=self.config['bucket_name'],
                        object_name=storage_path
                    )
                    raise ValueError("Failed to save file metadata")
                return file_metadata

            except Exception as e:
                self.logger.error(f"Failed to save file metadata: {str(e)}")
                # Clean up MinIO file
                try:
                    minio_client.remove_object(
                        bucket_name=self.config['bucket_name'],
                        object_name=storage_path
                    )
                except Exception as cleanup_error:
                    self.logger.error(f"Failed to clean up MinIO file: {str(cleanup_error)}")
                return None

        except Exception as e:
            self.logger.error(f"Failed to save file: {str(e)}")
            return None

    async def delete_file(self, file_id: str) -> bool:
        """Delete file from MinIO"""
        try:
            # Get file metadata
            file_metadata = await self.repository.find_one({"file_id": file_id})
            if not file_metadata:
                return False

            # Get MinIO client
            minio_client = await self._get_minio_client()

            # Delete from MinIO
            minio_client.remove_object(
                bucket_name=self.config['bucket_name'],
                object_name=file_metadata.storage_path
            )

            # Update metadata status
            await self.repository.update(
                file_id,
                {"status": FileStatus.DELETED}
            )

            return True

        except Exception as e:
            self.logger.error(f"Failed to delete file: {str(e)}")
            return False

    async def get_file_info(self, file_id: str) -> Optional[Dict]:
        """Get file information"""
        try:
            file_metadata = await self.repository.find_one({"file_id": file_id})
            if not file_metadata:
                return None

            # Get MinIO client
            minio_client = await self._get_minio_client()

            # Get object stats from MinIO
            stats = minio_client.stat_object(
                bucket_name=self.config['bucket_name'],
                object_name=file_metadata.storage_path
            )

            return {
                "file_id": file_metadata.file_id,
                "filename": file_metadata.filename,
                "size": stats.size,
                "mime_type": file_metadata.mime_type,
                "status": file_metadata.status,
                "created_at": stats.last_modified
            }

        except Exception as e:
            self.logger.error(f"Failed to get file info: {str(e)}")
            return None

    async def extract_text(self, file_id: str) -> Optional[str]:
        """Extract text from file"""
        try:
            file_metadata = await self.repository.find_one({"file_id": file_id})
            if not file_metadata:
                return None

            # Get MinIO client
            minio_client = await self._get_minio_client()

            # Get file content from MinIO
            response = minio_client.get_object(
                bucket_name=self.config['bucket_name'],
                object_name=file_metadata.storage_path
            )
            content = response.read()
            response.close()

            # Extract text based on file type
            mime_type = file_metadata.mime_type
            if mime_type == 'application/pdf':
                return self._extract_text_from_pdf(content)
            elif mime_type in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                return self._extract_text_from_docx(content)
            elif mime_type.startswith('text/'):
                encoding = chardet.detect(content)['encoding'] or 'utf-8'
                return content.decode(encoding)
            else:
                raise ValueError(f"Unsupported file type: {mime_type}")

        except Exception as e:
            self.logger.error(f"Failed to extract text: {str(e)}")
            return None

    def _extract_text_from_pdf(self, content: bytes) -> str:
        """Extract text from PDF content"""
        text = []
        with fitz.open(stream=content, filetype="pdf") as doc:
            for page in doc:
                text.append(page.get_text())
        return "\n".join(text)

    def _extract_text_from_docx(self, content: bytes) -> str:
        """Extract text from DOCX content"""
        doc = docx.Document(BytesIO(content))
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])