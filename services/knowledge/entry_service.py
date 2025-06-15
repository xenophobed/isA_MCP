# app/services/entry.py
from typing import List, Optional, Dict, BinaryIO
from app.repositories.knowledge.entry_repo import EntryRepository
from app.models.knowledge.entry import Entry, EntryCreate, ProcessingStatus
from app.services.knowledge.kb_file_service import KnowledgeFileService
from app.services.knowledge.processor_service import ProcessorService
from app.services.knowledge.index_service import IndexService
from uuid import uuid4
from fastapi import UploadFile
from datetime import datetime
from app.config.config_manager import config_manager

class EntryService:
    def __init__(
        self,
        repository: EntryRepository,
        file_service: KnowledgeFileService,
        processor_service: ProcessorService,
        index_service: IndexService
    ):
        self.repository = repository
        self.file_service = file_service
        self.processor_service = processor_service
        self.index_service = index_service
        self.logger = config_manager.get_logger(__name__)

    async def create_entry(
        self,
        knowledge_id: str,
        data: EntryCreate,
        file: Optional[UploadFile] = None
    ) -> Optional[str]:
        """Create knowledge entry"""
        try:
            # Handle file upload
            file_id = None
            if file:
                # Calculate file metadata
                file_metadata = {
                    "original_name": file.filename,
                    "content_type": file.content_type,
                    "checksum": await self._calculate_checksum(file),
                    "size": 0  
                }
                
                file_result = await self.file_service.save_file(
                    file=file,
                    prefix=f"knowledge_{knowledge_id}",
                    metadata=file_metadata
                )
                if not file_result:
                    raise ValueError("Failed to save file")
                file_id = file_result.file_id

            # Create entry
            entry = Entry(
                entry_id=f"entry_{uuid4().hex[:8]}",
                knowledge_id=knowledge_id,
                title=data.title,
                type=data.type,
                content=data.content,
                file_id=file_id or data.file_id,
                url=data.url,
                status=ProcessingStatus.PENDING,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            entry_id = await self.repository.create_entry(entry)
            if not entry_id:
                if file_id:
                    await self.file_service.delete_file(file_id)
                raise ValueError("Failed to create entry")

            # Process entry asynchronously
            await self._process_entry(entry)
            return entry_id

        except Exception as e:
            self.logger.error(f"Failed to create entry: {str(e)}")
            return None

    async def _calculate_checksum(self, file: UploadFile) -> str:
        """Calculate file checksum"""
        import hashlib
        try:
            md5 = hashlib.md5()
            await file.seek(0)
            while chunk := await file.read(8192):
                md5.update(chunk)
            await file.seek(0)
            return md5.hexdigest()
        except Exception as e:
            self.logger.error(f"Failed to calculate checksum: {str(e)}")
            raise

    async def _process_entry(self, entry: Entry):
        """Data Processing and Embedding"""
        try:
            # 1. Extract text content
            content = await self.file_service.extract_text(entry.file_id)
            if not content:
                raise ValueError(f"Failed to extract text from file: {entry.file_id}")
            
            self.logger.info(f"Content length: {len(content)} characters")
            
            # 2. Process content using ProcessorService
            chunk_vectors, doc_semantics = await self.processor_service.process_content(
                content=content,
                metadata={
                    "file_id": entry.file_id,
                    "knowledge_id": entry.knowledge_id,
                    "entry_id": entry.entry_id
                }
            )
            
            if not chunk_vectors:
                raise ValueError("Failed to process content")

            # 3. Add to index
            success = await self.index_service.add_chunks(
                knowledge_id=entry.knowledge_id,
                entry_id=entry.entry_id,
                chunks=chunk_vectors
            )
            
            if not success:
                raise ValueError("Failed to add to index")

            # 4. Update entry information
            await self.repository.update(
                entry.entry_id,
                {
                    "status": ProcessingStatus.COMPLETED,
                    "chunk_count": len(chunk_vectors),
                    "embedding_model": self.processor_service.embedding_model,
                    "last_processed": datetime.utcnow()
                }
            )

        except Exception as e:
            self.logger.error(f"Failed to process entry: {str(e)}")
            # Update entry with error status
            try:
                await self.repository.update(
                    entry.entry_id,
                    {
                        "status": ProcessingStatus.FAILED,
                        "error_message": str(e),
                        "last_processed": datetime.utcnow()
                    }
                )
            except Exception as update_error:
                self.logger.error(f"Failed to update entry status: {str(update_error)}")

    async def get_entry_details(
        self,
        entry_id: str,
        with_chunks: bool = False
    ) -> Optional[Dict]:
        """获取条目详情"""
        try:
            # 1. 获取基本信息
            entry = await self.repository.find_one({"entry_id": entry_id})
            if not entry:
                return None

            result = entry.dict()

            # 2. 获取文件信息
            if entry.file_id:
                file_info = await self.file_service.get_file_info(entry.file_id)
                if file_info:
                    result["file"] = file_info

            # 3. 获取分块信息
            if with_chunks:
                chunks = await self.processor_service.get_entry_chunks(
                    entry_id,
                    with_vectors=False
                )
                result["chunks"] = chunks

            return result

        except Exception as e:
            self.logger.error(f"Failed to get entry details: {str(e)}")
            return None

    async def delete_entry(self, entry_id: str) -> bool:
        """Delete an entry and its associated chunks"""
        try:
            # 1. Verify entry exists
            entry = await self.repository.get_by_id(entry_id)
            if not entry:
                raise ValueError(f"Entry not found: {entry_id}")
            
            # 2. Delete associated chunks first
            await self.chunk_repository.delete_by_entry(entry_id)
            
            # 3. Delete associated file if exists
            if entry.file_id:
                await self.file_service.delete_file(entry.file_id)
            
            # 4. Delete the entry itself
            result = await self.repository.delete_entry(entry_id)
            if not result:
                raise ValueError("Failed to delete entry")
            
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to delete entry: {str(e)}")
            raise

    async def get_entries(
        self,
        knowledge_id: str,
        type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[Dict]:
        """Get entries with filters"""
        try:
            # Build query
            query = {"knowledge_id": knowledge_id}
            if type:
                query["type"] = type
            if status:
                query["status"] = status
            
            # Get entries
            entries = await self.repository.find_many(
                query,
                skip=skip,
                limit=limit,
                sort=[("created_at", -1)]
            )
            
            # Convert to dict and add additional info
            results = []
            for entry in entries:
                entry_dict = entry.dict()
                # Add file info if exists
                if entry.file_id:
                    file_info = await self.file_service.get_file_info(entry.file_id)
                    if file_info:
                        entry_dict["file"] = file_info
                results.append(entry_dict)
            
            return results
        
        except Exception as e:
            self.logger.error(f"Failed to get entries: {str(e)}")
            return []
        
    async def get_default_knowledge_id(self) -> str:
        """Get default knowledge base ID"""
        try:
            # Get MongoDB client
            db = await config_manager.get_db('mongodb')
            
            # Query for default knowledge base
            default_knowledge = await db.knowledge.find_one({"is_default": True})
            if not default_knowledge:
                raise ValueError("No default knowledge base found")
            return default_knowledge["knowledge_id"]
            
        except Exception as e:
            self.logger.error(f"Failed to get default knowledge ID: {str(e)}")
            raise
        
