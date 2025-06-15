from typing import Dict, List, Any
from notion_client import Client
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class NotionExtractor:
    def __init__(self, notion_token: str):
        self.client = Client(auth=notion_token)
        
    async def extract_database(self, database_id: str) -> Dict[str, Any]:
        """
        从Notion数据库中提取基础信息
        返回：数据库结构和内容
        """
        try:
            # 1. 获取数据库结构信息
            database = self.client.databases.retrieve(database_id)
            
            # 2. 获取数据库内容
            pages = self.client.databases.query(
                database_id=database_id,
                page_size=100  # 获取足够的样本数据
            )
            
            # 3. 整理返回结果
            return {
                "database_info": {
                    "id": database_id,
                    "title": self._get_database_title(database),
                    "properties": database.get('properties', {}),
                    "created_time": database.get('created_time'),
                    "last_edited_time": database.get('last_edited_time')
                },
                "content": [
                    self._extract_page_content(page)
                    for page in pages.get('results', [])
                ]
            }
            
        except Exception as e:
            logger.error(f"Error extracting from Notion: {str(e)}")
            raise
            
    def _get_database_title(self, database: Dict) -> str:
        """提取数据库标题"""
        title = database.get('title', [])
        if title and len(title) > 0:
            return title[0].get('plain_text', '')
        return ''
        
    def _extract_page_content(self, page: Dict) -> Dict[str, Any]:
        """从页面中提取属性值"""
        content = {
            "id": page.get('id'),
            "created_time": page.get('created_time'),
            "last_edited_time": page.get('last_edited_time'),
            "properties": {}
        }
        
        # 处理每个属性
        for prop_name, prop_data in page.get('properties', {}).items():
            prop_type = prop_data.get('type')
            prop_value = None
            
            # 根据不同的属性类型提取值
            if prop_type == 'title':
                prop_value = self._get_text_content(prop_data.get('title', []))
            elif prop_type == 'rich_text':
                prop_value = self._get_text_content(prop_data.get('rich_text', []))
            elif prop_type == 'select':
                select_data = prop_data.get('select')
                prop_value = select_data.get('name') if select_data else None
            elif prop_type == 'multi_select':
                prop_value = [
                    option.get('name')
                    for option in prop_data.get('multi_select', [])
                ]
            elif prop_type == 'date':
                date_data = prop_data.get('date', {})
                prop_value = {
                    'start': date_data.get('start'),
                    'end': date_data.get('end')
                }
            elif prop_type == 'number':
                prop_value = prop_data.get('number')
            
            content['properties'][prop_name] = prop_value
            
        return content
        
    def _get_text_content(self, text_items: List[Dict]) -> str:
        """从文本类型的属性中提取纯文本内容"""
        if not text_items:
            return ''
        return ' '.join([
            item.get('plain_text', '')
            for item in text_items
        ])
