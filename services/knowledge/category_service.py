# app/services/category.py
from typing import List, Optional, Dict
from app.repositories.knowledge.category_repo import CategoryRepository
from app.models.knowledge.category import Category, CategoryCreate, CategoryUpdate
from .utils.path_utils import build_category_path, split_path
from uuid import uuid4
from app.config.config_manager import config_manager

class CategoryService:
    def __init__(self, repository: CategoryRepository):
        self.repository = repository
        self.logger = config_manager.get_logger(__name__)
        
    async def get_category_by_id(self, category_id: str) -> Optional[Category]:
        """Get category by ID"""
        try:
            return await self.repository.get_by_id(category_id)
        except Exception as e:
            self.logger.error(f"Failed to get category by id: {str(e)}")
            return None
            
    async def create_category(self, data: CategoryCreate) -> Optional[str]:
        """Create category"""
        try:
            # 1. Get parent category path
            parent_path = "/"
            if data.parent_id:
                parent = await self.repository.get_by_id(data.parent_id)
                if not parent:
                    raise ValueError(f"Parent category not found: {data.parent_id}")
                parent_path = parent.path
            
            # 2. Generate category ID and path
            category_id = f"cat_{uuid4().hex[:8]}"
            path = build_category_path(parent_path, data.name)
            
            # 3. Check if path exists
            existing = await self.repository.get_by_path(path)
            if existing:
                raise ValueError(f"Category path already exists: {path}")
            
            # 4. Create category
            category = Category(
                category_id=category_id,
                name=data.name,
                type=data.type,
                description=data.description,
                parent_id=data.parent_id,
                path=path,
                metadata=data.metadata or {}
            )
            
            self.logger.debug(f"Creating category: {category.dict()}")
            created = await self.repository.create_category(category)
            
            if not created:
                raise ValueError("Failed to create category")
                
            self.logger.info(f"Created category: {category_id}")
            return category_id
            
        except Exception as e:
            self.logger.error(f"Failed to create category: {str(e)}")
            return None

    async def update_category(
        self,
        category_id: str,
        data: CategoryUpdate
    ) -> bool:
        """Update category"""
        try:
            category = await self.repository.get_by_id(category_id)
            if not category:
                raise ValueError(f"Category not found: {category_id}")
            
            update_data = data.dict(exclude_unset=True)
            
            if "name" in update_data:
                parent_path = "/".join(category.path.split("/")[:-1])
                new_path = build_category_path(parent_path, data.name)
                
                existing = await self.repository.get_by_path(new_path)
                if existing and existing.category_id != category_id:
                    raise ValueError(f"Category path already exists: {new_path}")
                    
                update_data["path"] = new_path
            
            return await self.repository.update(category.id, {"$set": update_data})
            
        except Exception as e:
            self.logger.error(f"Failed to update category: {str(e)}")
            return False

    async def get_category_path(self, category_id: str) -> List[Category]:
        """Get category path"""
        try:
            path = []
            current = await self.get_category_by_id(category_id)
            while current:
                path.insert(0, current)
                if current.parent_id:
                    current = await self.get_category_by_id(current.parent_id)
                else:
                    break
            return path
        except Exception as e:
            self.logger.error(f"Failed to get category path: {str(e)}")
            return []

    async def get_children(self, parent_id: Optional[str] = None) -> List[Category]:
        """Get child categories"""
        try:
            return await self.repository.get_children(parent_id)
        except Exception as e:
            self.logger.error(f"Failed to get child categories: {str(e)}")
            return []

    async def delete_category(self, category_id: str) -> bool:
        """Delete category and its children"""
        try:
            # 1. Verify category exists
            category = await self.repository.get_by_id(category_id)
            if not category:
                raise ValueError(f"Category not found: {category_id}")
            
            # 2. Get all child categories
            children = await self.get_children(category_id)
            
            # 3. Delete all child categories first
            for child in children:
                await self.delete_category(child.category_id)
            
            # 4. Delete the category itself
            result = await self.repository.delete_category(category_id)
            if not result:
                raise ValueError("Failed to delete category")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete category: {str(e)}")
            raise