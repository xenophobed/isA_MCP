from typing import Dict, Optional
from app.models.knowledge.index import Index, IndexType, IndexStatus
from app.repositories.knowledge.index_repo import IndexRepository
from app.config.config_manager import config_manager

class IndexService:
    def __init__(
        self,
        repository: IndexRepository,
        config: Dict = None
    ):
        self.repository = repository
        self.logger = config_manager.get_logger(__name__)

    async def create_index(self, index_id: str, embedding_model: str) -> Index:
        """Create a new index in MongoDB."""
        try:
            # Create the index in MongoDB
            index = Index(
                index_id=index_id,
                name=f"index_{index_id}",
                type=IndexType.SEMANTIC,
                embedding_model=embedding_model,
                vector_store="qdrant",
                status=IndexStatus.CREATING
            )
            await self.repository.create_index(index)
            return index
        except Exception as e:
            self.logger.error(f"Failed to create index: {e}")
            raise

    async def update_status(self, index_id: str, status: IndexStatus, error_msg: Optional[str] = None) -> bool:
        """Update index status."""
        try:
            return await self.repository.update_status(index_id, status, error_msg)
        except Exception as e:
            self.logger.error(f"Failed to update index status: {e}")
            raise

   