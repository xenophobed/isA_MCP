#!/usr/bin/env python3
"""
Document RAG Service

基于文档的问答服务，使用 ChromaDB 进行向量存储和检索。
"""

import uuid
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ...chroma_service import get_chroma_service
from ..adapters.file_adapters.document_adapter import DocumentAdapter

logger = logging.getLogger(__name__)

@dataclass
class RAGSession:
    """RAG 对话会话"""
    session_id: str
    collection_name: str
    documents: List[str] = field(default_factory=list)  # 文档路径列表
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

class DocumentRAGService:
    """
    文档 RAG 服务
    
    功能：
    - 文档加载和分块
    - 向量化存储
    - 语义检索
    - 问答生成
    """
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.sessions: Dict[str, RAGSession] = {}
        self.chroma_service = get_chroma_service()
    
    def create_session(self, session_name: Optional[str] = None) -> Dict[str, Any]:
        """创建新的 RAG 会话"""
        try:
            session_id = str(uuid.uuid4())
            
            # 在 ChromaDB 中创建集合
            collection_name = self.chroma_service.create_collection(
                name=f"doc_rag_{session_id}",
                metadata={
                    "session_id": session_id,
                    "session_name": session_name or f"Session_{session_id[:8]}",
                    "service_type": "document_rag"
                }
            )
            
            # 创建会话对象
            session = RAGSession(
                session_id=session_id,
                collection_name=collection_name
            )
            
            self.sessions[session_id] = session
            
            logger.info(f"DocumentRAG: Created session {session_id}")
            
            return {
                "status": "success",
                "session_id": session_id,
                "collection_name": collection_name
            }
            
        except Exception as e:
            logger.error(f"DocumentRAG: Failed to create session: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def add_document(self, session_id: str, file_path: str) -> Dict[str, Any]:
        """向会话添加文档"""
        try:
            session = self.sessions.get(session_id)
            if not session:
                return {"status": "failed", "error": "Session not found"}
            
            # 使用 DocumentAdapter 加载文档
            adapter = DocumentAdapter()
            success = adapter.connect({'file_path': file_path})
            
            if not success:
                return {"status": "failed", "error": "Failed to load document"}
            
            # 提取文档内容
            document_content = self._extract_document_content(adapter)
            
            # 分块处理
            chunks = self._chunk_document_content(document_content, file_path)
            
            adapter.disconnect()
            
            # 准备向量化数据
            chunk_texts = [chunk["content"] for chunk in chunks]
            chunk_ids = [chunk["id"] for chunk in chunks]
            chunk_metadatas = [chunk["metadata"] for chunk in chunks]
            
            # 添加到 ChromaDB
            result = self.chroma_service.add_documents(
                collection_name=session.collection_name,
                documents=chunk_texts,
                ids=chunk_ids,
                metadatas=chunk_metadatas
            )
            
            if result["status"] == "success":
                # 记录文档到会话
                session.documents.append(file_path)
                
                logger.info(f"DocumentRAG: Added document '{file_path}' to session {session_id}")
                
                return {
                    "status": "success",
                    "session_id": session_id,
                    "file_path": file_path,
                    "chunks_created": len(chunks),
                    "document_title": Path(file_path).stem
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"DocumentRAG: Failed to add document: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "session_id": session_id,
                "file_path": file_path
            }
    
    def query(self, session_id: str, question: str, top_k: int = 3) -> Dict[str, Any]:
        """查询文档并生成回答"""
        try:
            session = self.sessions.get(session_id)
            if not session:
                return {"status": "failed", "error": "Session not found"}
            
            # 在 ChromaDB 中查询相关文档块
            query_result = self.chroma_service.query_collection(
                collection_name=session.collection_name,
                query_texts=[question],
                n_results=top_k
            )
            
            if query_result["status"] != "success":
                return query_result
            
            # 处理查询结果
            results = query_result["results"]
            retrieved_chunks = []
            context_parts = []
            
            if results["documents"] and len(results["documents"]) > 0:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else 0
                    
                    chunk_info = {
                        "content": doc,
                        "metadata": metadata,
                        "similarity_score": 1 - distance if distance else 1.0,
                        "source_file": metadata.get("file_path", "Unknown"),
                        "page_number": metadata.get("page_number")
                    }
                    retrieved_chunks.append(chunk_info)
                    context_parts.append(doc)
            
            # 生成回答
            context = "\n\n".join(context_parts)
            answer = self._generate_answer(question, context, retrieved_chunks)
            
            # 记录对话历史
            conversation_entry = {
                "question": question,
                "answer": answer,
                "context_chunks": len(retrieved_chunks),
                "timestamp": datetime.now().isoformat()
            }
            session.conversation_history.append(conversation_entry)
            
            return {
                "status": "success",
                "session_id": session_id,
                "question": question,
                "answer": answer,
                "context": context,
                "retrieved_chunks": retrieved_chunks,
                "sources": list(set(chunk["source_file"] for chunk in retrieved_chunks))
            }
            
        except Exception as e:
            logger.error(f"DocumentRAG: Failed to query: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "session_id": session_id,
                "question": question
            }
    
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """获取会话信息"""
        try:
            session = self.sessions.get(session_id)
            if not session:
                return {"status": "failed", "error": "Session not found"}
            
            # 获取集合统计
            collections = self.chroma_service.list_collections()
            collection_info = next(
                (c for c in collections if c["name"] == session.collection_name), 
                {}
            )
            
            return {
                "status": "success",
                "session_id": session_id,
                "collection_name": session.collection_name,
                "documents_count": len(session.documents),
                "documents": session.documents,
                "conversation_count": len(session.conversation_history),
                "chunks_count": collection_info.get("document_count", 0),
                "created_at": session.created_at.isoformat(),
                "last_query": session.conversation_history[-1] if session.conversation_history else None
            }
            
        except Exception as e:
            logger.error(f"DocumentRAG: Failed to get session info: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "session_id": session_id
            }
    
    def delete_session(self, session_id: str) -> Dict[str, Any]:
        """删除会话"""
        try:
            session = self.sessions.get(session_id)
            if not session:
                return {"status": "failed", "error": "Session not found"}
            
            # 删除 ChromaDB 集合
            success = self.chroma_service.delete_collection(session.collection_name)
            
            if success:
                # 删除会话记录
                del self.sessions[session_id]
                logger.info(f"DocumentRAG: Deleted session {session_id}")
                
                return {
                    "status": "success",
                    "session_id": session_id,
                    "message": "Session deleted successfully"
                }
            else:
                return {
                    "status": "failed",
                    "error": "Failed to delete ChromaDB collection"
                }
                
        except Exception as e:
            logger.error(f"DocumentRAG: Failed to delete session: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "session_id": session_id
            }
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有会话"""
        sessions_info = []
        for session_id, session in self.sessions.items():
            sessions_info.append({
                "session_id": session_id,
                "collection_name": session.collection_name,
                "documents_count": len(session.documents),
                "conversation_count": len(session.conversation_history),
                "created_at": session.created_at.isoformat()
            })
        return sessions_info
    
    def _extract_document_content(self, adapter: DocumentAdapter) -> List[Dict[str, Any]]:
        """提取文档内容"""
        content_parts = []
        
        for page in adapter.pages:
            content_parts.append({
                "page_number": page.page_number,
                "content": page.content,
                "page_type": page.page_type,
                "tables": len(page.tables),
                "has_image": page.image_path is not None
            })
        
        return content_parts
    
    def _chunk_document_content(self, content_parts: List[Dict[str, Any]], file_path: str) -> List[Dict[str, Any]]:
        """将文档内容分块"""
        chunks = []
        chunk_index = 0
        
        for page_info in content_parts:
            page_content = page_info["content"]
            page_number = page_info["page_number"]
            
            # 按段落分割
            paragraphs = page_content.split('\n\n')
            current_chunk = ""
            
            for paragraph in paragraphs:
                # 检查是否需要开始新块
                potential_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph
                
                if len(potential_chunk) <= self.chunk_size:
                    current_chunk = potential_chunk
                else:
                    # 保存当前块
                    if current_chunk.strip():
                        chunks.append(self._create_chunk(
                            content=current_chunk.strip(),
                            chunk_index=chunk_index,
                            page_number=page_number,
                            file_path=file_path
                        ))
                        chunk_index += 1
                    
                    # 开始新块
                    current_chunk = paragraph
            
            # 保存页面的最后一块
            if current_chunk.strip():
                chunks.append(self._create_chunk(
                    content=current_chunk.strip(),
                    chunk_index=chunk_index,
                    page_number=page_number,
                    file_path=file_path
                ))
                chunk_index += 1
        
        return chunks
    
    def _create_chunk(self, content: str, chunk_index: int, page_number: int, file_path: str) -> Dict[str, Any]:
        """创建文档块"""
        return {
            "id": f"{Path(file_path).stem}_chunk_{chunk_index}",
            "content": content,
            "metadata": {
                "file_path": file_path,
                "file_name": Path(file_path).name,
                "page_number": page_number,
                "chunk_index": chunk_index,
                "content_length": len(content)
            }
        }
    
    def _generate_answer(self, question: str, context: str, retrieved_chunks: List[Dict]) -> str:
        """根据上下文生成回答"""
        if not context.strip():
            return "抱歉，我在文档中没有找到相关信息来回答这个问题。"
        
        # 简单的模板回答（实际使用中可以集成 LLM）
        question_lower = question.lower()
        
        # 获取来源信息
        sources = list(set(chunk["source_file"] for chunk in retrieved_chunks))
        pages = sorted(set(chunk["metadata"]["page_number"] for chunk in retrieved_chunks))
        
        source_info = f"（来源：{', '.join(Path(s).name for s in sources)}，第 {', '.join(map(str, pages))} 页）"
        
        if any(word in question_lower for word in ['什么', 'what', '定义', 'define']):
            return f"根据文档内容：{context[:400]}... {source_info}"
        elif any(word in question_lower for word in ['如何', 'how', '怎么', '方法']):
            return f"根据文档描述的方法：{context[:400]}... {source_info}"
        elif any(word in question_lower for word in ['为什么', 'why', '原因']):
            return f"文档中提到的原因：{context[:400]}... {source_info}"
        else:
            return f"根据文档内容：{context[:400]}... {source_info}"
    
    def get_stats(self) -> Dict[str, Any]:
        """获取服务统计"""
        total_documents = sum(len(session.documents) for session in self.sessions.values())
        total_conversations = sum(len(session.conversation_history) for session in self.sessions.values())
        
        return {
            "total_sessions": len(self.sessions),
            "total_documents": total_documents,
            "total_conversations": total_conversations,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "chroma_service_stats": self.chroma_service.get_stats()
        }

# 全局服务实例
_document_rag_service = None

def get_document_rag_service() -> DocumentRAGService:
    """获取全局文档 RAG 服务实例"""
    global _document_rag_service
    if _document_rag_service is None:
        _document_rag_service = DocumentRAGService()
    return _document_rag_service