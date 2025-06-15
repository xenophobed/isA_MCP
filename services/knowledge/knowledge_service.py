# app/services/knowledge.py
from typing import List, Optional, Dict
from app.repositories.knowledge.knowledge_repo import KnowledgeRepository
from app.models.knowledge.knowledge import Knowledge, KnowledgeCreate, KnowledgeUpdate
from app.services.knowledge.category_service import CategoryService
from app.services.knowledge.entry_service import EntryService
from app.models.knowledge.category import Category, CategoryCreate, CategoryUpdate
from uuid import uuid4
from app.config.config_manager import config_manager

class KnowledgeService():
    def __init__(
        self,
        repository: KnowledgeRepository,
        category_service: CategoryService,
        entry_service: EntryService
    ):
        self.repository = repository
        self.category_service = category_service
        self.entry_service = entry_service
        self.logger = config_manager.get_logger(__name__)
        
    async def get_category_by_id(self, category_id: str) -> Optional[Category]:
        """根据ID获取分类"""
        try:
            return await self.repository.get_by_id(category_id)
        except Exception as e:
            self.logger.error(f"Failed to get category by id {category_id}: {str(e)}")
            return None
        
    async def create_knowledge(
        self,
        data: KnowledgeCreate,
        creator_id: str
    ) -> Optional[Dict]:
        """创建知识库"""
        try:
            # 1. 验证分类是否存在
            category = await self.category_service.get_category_by_id(data.category_id)
            if not category:
                raise ValueError(f"Category not found: {data.category_id}")
            
            # 2. 生成知识库ID
            knowledge_id = f"kb_{uuid4().hex[:8]}"
            
            # 3. 创建知识库
            knowledge = Knowledge(
                knowledge_id=knowledge_id,
                category_id=data.category_id,
                title=data.title,
                description=data.description,
                tags=data.tags or [],
                is_public=data.is_public,
                creator_id=creator_id,
                contributors=[creator_id],
                metadata=data.metadata or {}
            )
            
            created = await self.repository.create_knowledge(knowledge)
            if not created:
                raise ValueError("Failed to create knowledge")
                
            # 返回完整的响应对象
            return {
                "knowledge_id": knowledge_id,
                "title": knowledge.title,
                "category_id": knowledge.category_id,
                "creator_id": knowledge.creator_id,
                "created_at": knowledge.created_at,
                "status": "created"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create knowledge: {str(e)}")
            raise
            
    async def get_knowledge_list(
        self,
        category_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        status: Optional[str] = None,
        creator_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[Knowledge]:
        """获取知识库列表"""
        try:
            # 构建查询条件
            query = {}
            if category_id:
                query["category_id"] = category_id
            if tags:
                query["tags"] = {"$all": tags}
            if status:
                query["status"] = status
            if creator_id:
                query["creator_id"] = creator_id
                
            return await self.repository.find_many(
                query,
                skip=skip,
                limit=limit,
                sort=[("updated_at", -1)]
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get knowledge list: {str(e)}")
            return []
            
    async def update_knowledge(
        self,
        knowledge_id: str,
        data: KnowledgeUpdate,
        editor_id: str
    ) -> bool:
        """更新知识库"""
        try:
            knowledge = await self.repository.find_one(
                {"knowledge_id": knowledge_id}
            )
            if not knowledge:
                raise ValueError(f"Knowledge not found: {knowledge_id}")
            
            # 构建更新数据
            update_data = data.dict(exclude_unset=True)
            
            # 添加编辑者到贡献者列表
            if editor_id not in knowledge.contributors:
                update_data["contributors"] = knowledge.contributors + [editor_id]
            
            # 执行更新
            return await self.repository.update(
                knowledge.id,
                {
                    "$set": update_data,
                    "$currentDate": {"updated_at": True}
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to update knowledge: {str(e)}")
            return False

    async def get_knowledge_details(
        self,
        knowledge_id: str,
        with_entries: bool = False
    ) -> Optional[Dict]:
        """获取知识库详情"""
        try:
            # 1. 获取知识库基本信息
            knowledge = await self.repository.find_one(
                {"knowledge_id": knowledge_id}
            )
            if not knowledge:
                return None
                
            result = knowledge.dict()
            
            # 2. 获取分类信息
            category = await self.category_service.get(knowledge.category_id)
            if category:
                result["category"] = {
                    "id": category.category_id,
                    "name": category.name,
                    "path": category.path
                }
            
            # 3. 获取条目列表
            if with_entries:
                entries = await self.entry_service.get_by_knowledge(knowledge_id)
                result["entries"] = [entry.dict() for entry in entries]
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get knowledge details: {str(e)}")
            return None

    async def delete_knowledge(self, knowledge_id: str) -> bool:
        """删除知识库"""
        try:
            # 1. Verify knowledge exists
            knowledge = await self.repository.find_one({"knowledge_id": knowledge_id})
            if not knowledge:
                raise ValueError(f"Knowledge not found: {knowledge_id}")
            
            # 2. Delete associated entries first
            await self.entry_service.delete_by_knowledge(knowledge_id)
            
            # 3. Delete the knowledge base
            result = await self.repository.delete_knowledge(knowledge_id)
            if not result:
                raise ValueError("Failed to delete knowledge")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete knowledge: {str(e)}")
            raise