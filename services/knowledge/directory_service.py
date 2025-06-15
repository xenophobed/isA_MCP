# app/services/knowledge/directory_service.py

from typing import Optional, List, Dict
from app.models.knowledge.directory import Directory, DirectoryCreate, DirectoryUpdate
from app.repositories.knowledge.directory_repo import DirectoryRepository
from datetime import datetime
from uuid import uuid4
from app.config.config_manager import config_manager

class DirectoryService:
    def __init__(self, repository: DirectoryRepository):
        self.repository = repository
        self.logger = config_manager.get_logger(__name__)

    async def create_directory(self, data: DirectoryCreate) -> Optional[str]:
        """Create directory"""
        try:
            directory_id = f"dir_{uuid4().hex[:8]}"
            directory = Directory(
                directory_id=directory_id,
                knowledge_id=data.knowledge_id,
                name=data.name,
                parent_directory_id=data.parent_directory_id,
                description=data.description,
                metadata=data.metadata or {},
                tags=data.tags or [],
                status="active",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            success = await self.repository.create_directory(directory)
            if success:
                self.logger.info(f"Created directory: {directory_id}")
                return directory_id
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to create directory: {str(e)}")
            return None

    async def get_directory(self, directory_id: str) -> Optional[Directory]:
        """Get directory by ID"""
        try:
            self.logger.debug(f"Getting directory: {directory_id}")
            return await self.repository.get_by_id(directory_id)
        except Exception as e:
            self.logger.error(f"Failed to get directory: {str(e)}")
            return None

    async def list_directories(
        self,
        knowledge_id: Optional[str] = None,
        parent_directory_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Directory]:
        """List directories"""
        try:
            return await self.repository.list_directories(
                knowledge_id=knowledge_id,
                parent_directory_id=parent_directory_id,
                status=status
            )
        except Exception as e:
            self.logger.error(f"Failed to list directories: {str(e)}")
            return []

    async def update_directory(self, directory_id: str, data: DirectoryUpdate) -> bool:
        """Update directory"""
        try:
            update_data = data.dict(exclude_unset=True)
            update_data["updated_at"] = datetime.utcnow()
            return await self.repository.update_directory(directory_id, update_data)
        except Exception as e:
            self.logger.error(f"Failed to update directory: {str(e)}")
            return False

    async def delete_directory(self, directory_id: str) -> bool:
        """Delete directory"""
        try:
            return await self.repository.delete_directory(directory_id)
        except Exception as e:
            self.logger.error(f"Failed to delete directory: {str(e)}")
            return False

    async def get_directory_hierarchy(self, directory_id: str) -> Optional[Directory]:
        # Optional: Implement logic to retrieve directory with nested subdirectories
        return await self.repository.get_by_id(directory_id)

    async def add_entry_to_directory(self, directory_id: str, entry_id: str) -> bool:
        self.logger.debug(f"Adding entry {entry_id} to directory {directory_id}")
        return await self.repository.add_entry(directory_id, entry_id)

    async def remove_entry_from_directory(self, directory_id: str, entry_id: str) -> bool:
        self.logger.debug(f"Removing entry {entry_id} from directory {directory_id}")
        return await self.repository.remove_entry(directory_id, entry_id)

    async def get_directory_entries(self, directory_id: str) -> List[str]:
        self.logger.debug(f"Getting entries for directory {directory_id}")
        return await self.repository.get_entries(directory_id)