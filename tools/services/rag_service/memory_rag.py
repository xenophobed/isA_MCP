#!/usr/bin/env python3
"""
Memory-based RAG service using ChromaDB
"""

import uuid
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class RAGDocument:
    """Document stored in RAG system."""
    doc_id: str
    file_path: str
    title: str
    content: str
    chunks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class RAGChunk:
    """Text chunk with metadata."""
    chunk_id: str
    content: str
    doc_id: str
    page_number: Optional[int] = None
    chunk_index: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RAGSession:
    """RAG conversation session."""
    session_id: str
    collection_name: str
    documents: List[RAGDocument] = field(default_factory=list)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

class MemoryRAGService:
    """
    Simple in-memory RAG service using ChromaDB.
    
    Features:
    - Document chunking and vectorization
    - Semantic search
    - Question answering with context
    - Session management
    """
    
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2", chunk_size: int = 500):
        if not CHROMADB_AVAILABLE:
            raise ImportError("ChromaDB is required. Install with: pip install chromadb")
        
        self.chunk_size = chunk_size
        self.sessions: Dict[str, RAGSession] = {}
        
        # Initialize ChromaDB client (in-memory)
        self.chroma_client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=None  # In-memory only
        ))
        
        # Initialize embedding model
        self.embedding_model_name = embedding_model
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer(embedding_model)
                self.use_sentence_transformers = True
                logger.info(f"Using SentenceTransformers model: {embedding_model}")
            except Exception as e:
                logger.warning(f"Failed to load SentenceTransformers model: {e}")
                self.use_sentence_transformers = False
        else:
            self.use_sentence_transformers = False
            logger.warning("SentenceTransformers not available, using ChromaDB default embeddings")
    
    def create_session(self, session_name: Optional[str] = None) -> RAGSession:
        """Create a new RAG session."""
        session_id = str(uuid.uuid4())
        collection_name = f"rag_session_{session_id}"
        
        # Create ChromaDB collection
        collection = self.chroma_client.create_collection(
            name=collection_name,
            metadata={"session_id": session_id, "created_at": datetime.now().isoformat()}
        )
        
        session = RAGSession(
            session_id=session_id,
            collection_name=collection_name
        )
        
        self.sessions[session_id] = session
        
        logger.info(f"Created RAG session: {session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[RAGSession]:
        """Get existing session."""
        return self.sessions.get(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its data."""
        try:
            session = self.sessions.get(session_id)
            if session:
                # Delete ChromaDB collection
                self.chroma_client.delete_collection(session.collection_name)
                # Remove from sessions
                del self.sessions[session_id]
                logger.info(f"Deleted RAG session: {session_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    def add_document_text(self, session_id: str, text: str, title: str = "Document", 
                         metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add text document to RAG session."""
        try:
            session = self.get_session(session_id)
            if not session:
                return {"error": "Session not found", "status": "failed"}
            
            # Create document
            doc_id = str(uuid.uuid4())
            doc = RAGDocument(
                doc_id=doc_id,
                file_path="",
                title=title,
                content=text,
                metadata=metadata or {}
            )
            
            # Chunk the text
            chunks = self._chunk_text(text)
            doc.chunks = [chunk.content for chunk in chunks]
            
            # Add to ChromaDB
            collection = self.chroma_client.get_collection(session.collection_name)
            
            chunk_ids = []
            chunk_contents = []
            chunk_metadatas = []
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc_id}_chunk_{i}"
                chunk_ids.append(chunk_id)
                chunk_contents.append(chunk.content)
                chunk_metadata = {
                    "doc_id": doc_id,
                    "title": title,
                    "chunk_index": i,
                    "page_number": chunk.page_number
                }
                if metadata:
                    chunk_metadata.update(metadata)
                chunk_metadatas.append(chunk_metadata)
            
            # Generate embeddings and add to collection
            if self.use_sentence_transformers:
                embeddings = self.embedding_model.encode(chunk_contents).tolist()
                collection.add(
                    ids=chunk_ids,
                    documents=chunk_contents,
                    metadatas=chunk_metadatas,
                    embeddings=embeddings
                )
            else:
                collection.add(
                    ids=chunk_ids,
                    documents=chunk_contents,
                    metadatas=chunk_metadatas
                )
            
            # Add to session
            session.documents.append(doc)
            
            logger.info(f"Added document '{title}' with {len(chunks)} chunks to session {session_id}")
            
            return {
                "status": "success",
                "doc_id": doc_id,
                "title": title,
                "chunks_created": len(chunks),
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Failed to add document to session {session_id}: {e}")
            return {"error": str(e), "status": "failed"}
    
    def add_document_from_file(self, session_id: str, file_path: str) -> Dict[str, Any]:
        """Add document from file to RAG session."""
        try:
            # Use our document adapter to extract text
            from ..data_analytics_service.adapters.file_adapters.document_adapter import DocumentAdapter
            
            adapter = DocumentAdapter()
            success = adapter.connect({'file_path': file_path})
            
            if not success:
                return {"error": "Failed to load document", "status": "failed"}
            
            # Extract text content from all pages
            full_text = ""
            page_contents = []
            
            for page in adapter.pages:
                page_contents.append({
                    "page_number": page.page_number,
                    "content": page.content,
                    "page_type": page.page_type
                })
                full_text += f"\n\nPage {page.page_number}:\n{page.content}"
            
            adapter.disconnect()
            
            # Get document title from filename
            from pathlib import Path
            title = Path(file_path).stem
            
            # Add document with page metadata
            result = self.add_document_text(
                session_id=session_id,
                text=full_text.strip(),
                title=title,
                metadata={
                    "file_path": file_path,
                    "total_pages": len(page_contents),
                    "page_contents": page_contents
                }
            )
            
            if result.get("status") == "success":
                result["file_path"] = file_path
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to add document from file {file_path}: {e}")
            return {"error": str(e), "status": "failed"}
    
    def query(self, session_id: str, question: str, top_k: int = 3) -> Dict[str, Any]:
        """Query the RAG system with a question."""
        try:
            session = self.get_session(session_id)
            if not session:
                return {"error": "Session not found", "status": "failed"}
            
            collection = self.chroma_client.get_collection(session.collection_name)
            
            # Search for relevant chunks
            if self.use_sentence_transformers:
                query_embedding = self.embedding_model.encode([question]).tolist()
                results = collection.query(
                    query_embeddings=query_embedding,
                    n_results=top_k,
                    include=["documents", "metadatas", "distances"]
                )
            else:
                results = collection.query(
                    query_texts=[question],
                    n_results=top_k,
                    include=["documents", "metadatas", "distances"]
                )
            
            # Format results
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
                        "source": metadata.get("title", "Unknown")
                    }
                    retrieved_chunks.append(chunk_info)
                    context_parts.append(doc)
            
            # Generate answer using the context
            context = "\n\n".join(context_parts)
            answer = self._generate_answer(question, context)
            
            # Add to conversation history
            conversation_entry = {
                "question": question,
                "answer": answer,
                "context_chunks": len(retrieved_chunks),
                "timestamp": datetime.now().isoformat()
            }
            session.conversation_history.append(conversation_entry)
            
            return {
                "status": "success",
                "question": question,
                "answer": answer,
                "context": context,
                "retrieved_chunks": retrieved_chunks,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Failed to query session {session_id}: {e}")
            return {"error": str(e), "status": "failed"}
    
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get information about a session."""
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found", "status": "failed"}
        
        try:
            collection = self.chroma_client.get_collection(session.collection_name)
            collection_count = collection.count()
        except:
            collection_count = 0
        
        return {
            "status": "success",
            "session_id": session_id,
            "collection_name": session.collection_name,
            "documents_count": len(session.documents),
            "chunks_count": collection_count,
            "conversation_history_count": len(session.conversation_history),
            "created_at": session.created_at.isoformat(),
            "documents": [
                {
                    "doc_id": doc.doc_id,
                    "title": doc.title,
                    "chunks_count": len(doc.chunks),
                    "file_path": doc.file_path
                }
                for doc in session.documents
            ]
        }
    
    def _chunk_text(self, text: str, page_number: Optional[int] = None) -> List[RAGChunk]:
        """Split text into chunks for embedding."""
        chunks = []
        
        # Simple chunking by sentences/paragraphs
        paragraphs = text.split('\n\n')
        current_chunk = ""
        chunk_index = 0
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed chunk size, start new chunk
            if len(current_chunk) + len(paragraph) > self.chunk_size and current_chunk:
                chunks.append(RAGChunk(
                    chunk_id=str(uuid.uuid4()),
                    content=current_chunk.strip(),
                    doc_id="",  # Will be set when adding to document
                    page_number=page_number,
                    chunk_index=chunk_index
                ))
                current_chunk = paragraph
                chunk_index += 1
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(RAGChunk(
                chunk_id=str(uuid.uuid4()),
                content=current_chunk.strip(),
                doc_id="",
                page_number=page_number,
                chunk_index=chunk_index
            ))
        
        return chunks
    
    def _generate_answer(self, question: str, context: str) -> str:
        """Generate answer based on question and context."""
        # Simple template-based answer generation
        # In a real implementation, you'd use an LLM here
        
        if not context.strip():
            return "I don't have enough information to answer this question based on the provided documents."
        
        # Basic keyword matching for simple responses
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['what', 'define', 'explain']):
            return f"Based on the provided context: {context[:300]}..."
        elif any(word in question_lower for word in ['how', 'process', 'method']):
            return f"According to the document, here's the relevant information: {context[:300]}..."
        elif any(word in question_lower for word in ['when', 'time', 'date']):
            return f"From the document content: {context[:300]}..."
        else:
            return f"Here's what I found in the documents: {context[:300]}..."
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions."""
        return [
            {
                "session_id": session.session_id,
                "collection_name": session.collection_name,
                "documents_count": len(session.documents),
                "conversation_count": len(session.conversation_history),
                "created_at": session.created_at.isoformat()
            }
            for session in self.sessions.values()
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        total_documents = sum(len(session.documents) for session in self.sessions.values())
        total_conversations = sum(len(session.conversation_history) for session in self.sessions.values())
        
        return {
            "total_sessions": len(self.sessions),
            "total_documents": total_documents,
            "total_conversations": total_conversations,
            "embedding_model": self.embedding_model_name,
            "chunk_size": self.chunk_size,
            "chromadb_available": CHROMADB_AVAILABLE,
            "sentence_transformers_available": SENTENCE_TRANSFORMERS_AVAILABLE
        }