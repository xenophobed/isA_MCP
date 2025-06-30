#!/usr/bin/env python3
"""
Document RAG tools
"""

import logging
from typing import Dict, Any, Optional

from ..services.document_rag import get_document_rag_service

logger = logging.getLogger(__name__)

def create_document_rag_session(session_name: Optional[str] = None) -> Dict[str, Any]:
    """
    创建文档 RAG 会话。
    
    Args:
        session_name: 可选的会话名称
        
    Returns:
        会话创建结果
    """
    try:
        rag_service = get_document_rag_service()
        result = rag_service.create_session(session_name)
        return result
        
    except Exception as e:
        logger.error(f"Failed to create RAG session: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }

def add_document_to_rag_session(session_id: str, file_path: str) -> Dict[str, Any]:
    """
    向 RAG 会话添加文档。
    
    Args:
        session_id: RAG 会话 ID
        file_path: 文档文件路径
        
    Returns:
        文档添加结果
    """
    try:
        rag_service = get_document_rag_service()
        result = rag_service.add_document(session_id, file_path)
        return result
        
    except Exception as e:
        logger.error(f"Failed to add document to RAG session: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "session_id": session_id,
            "file_path": file_path
        }

def query_document_rag(session_id: str, question: str, top_k: int = 3) -> Dict[str, Any]:
    """
    向文档 RAG 系统提问。
    
    Args:
        session_id: RAG 会话 ID
        question: 问题
        top_k: 检索的相关块数量
        
    Returns:
        问答结果
    """
    try:
        rag_service = get_document_rag_service()
        result = rag_service.query(session_id, question, top_k)
        return result
        
    except Exception as e:
        logger.error(f"Failed to query RAG session: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "session_id": session_id,
            "question": question
        }

def get_rag_session_info(session_id: str) -> Dict[str, Any]:
    """
    获取 RAG 会话信息。
    
    Args:
        session_id: RAG 会话 ID
        
    Returns:
        会话信息
    """
    try:
        rag_service = get_document_rag_service()
        result = rag_service.get_session_info(session_id)
        return result
        
    except Exception as e:
        logger.error(f"Failed to get RAG session info: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "session_id": session_id
        }

def delete_rag_session(session_id: str) -> Dict[str, Any]:
    """
    删除 RAG 会话。
    
    Args:
        session_id: 要删除的会话 ID
        
    Returns:
        删除结果
    """
    try:
        rag_service = get_document_rag_service()
        result = rag_service.delete_session(session_id)
        return result
        
    except Exception as e:
        logger.error(f"Failed to delete RAG session: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "session_id": session_id
        }

def list_rag_sessions() -> Dict[str, Any]:
    """
    列出所有 RAG 会话。
    
    Returns:
        会话列表
    """
    try:
        rag_service = get_document_rag_service()
        sessions = rag_service.list_sessions()
        
        return {
            "status": "success",
            "sessions": sessions,
            "total_sessions": len(sessions)
        }
        
    except Exception as e:
        logger.error(f"Failed to list RAG sessions: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }

def get_rag_service_stats() -> Dict[str, Any]:
    """
    获取 RAG 服务统计信息。
    
    Returns:
        服务统计
    """
    try:
        rag_service = get_document_rag_service()
        stats = rag_service.get_stats()
        
        return {
            "status": "success",
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get RAG service stats: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }

def quick_document_question(file_path: str, question: str) -> Dict[str, Any]:
    """
    快速文档问答 - 一键创建会话、添加文档并提问。
    
    Args:
        file_path: 文档文件路径
        question: 问题
        
    Returns:
        完整的问答结果
    """
    try:
        # 创建会话
        session_result = create_document_rag_session()
        if session_result.get("status") != "success":
            return session_result
        
        session_id = session_result["session_id"]
        
        # 添加文档
        doc_result = add_document_to_rag_session(session_id, file_path)
        if doc_result.get("status") != "success":
            # 清理会话
            delete_rag_session(session_id)
            return doc_result
        
        # 提问
        query_result = query_document_rag(session_id, question)
        
        # 添加会话信息到结果
        if query_result.get("status") == "success":
            query_result["session_info"] = {
                "session_id": session_id,
                "document_added": doc_result.get("document_title", file_path),
                "chunks_created": doc_result.get("chunks_created", 0),
                "note": "Session created temporarily for this question"
            }
        
        return query_result
        
    except Exception as e:
        logger.error(f"Failed quick document question: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "file_path": file_path,
            "question": question
        }