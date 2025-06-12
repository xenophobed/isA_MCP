from datetime import datetime, timedelta, timezone
import uuid
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
import asyncio
from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError
from bson.objectid import ObjectId
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from langgraph.checkpoint.base import CheckpointTuple
import os
from app.config.config_manager import config_manager


# Import LangChain message types
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    ToolMessage,
    SystemMessage,
    BaseMessage
)

class MessageModel(BaseModel):
    """Model for a message in the chat history"""
    role: str  # "human", "ai", "tool", or "system"
    content: str
    id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    additional_kwargs: Optional[Dict[str, Any]] = None

class SessionModel(BaseModel):
    """Model for a session in the database"""
    thread_id: str
    checkpoint_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    messages: List[MessageModel]
    state: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class SessionMemoryService:
    """Service for managing session-level short-term memory using MongoDB"""
    
    def __init__(
        self,
        mongo_uri: str = None,
        db_name: str = "haley_ai",
        collection_name: str = "session_memory",
        max_session_age_days: int = 30
    ):
        """Initialize the session memory service
        
        Args:
            mongo_uri: MongoDB connection URI
            db_name: Database name
            collection_name: Collection name for session data
            max_session_age_days: Maximum age of sessions before cleanup
        """
        self._mongo_uri = mongo_uri
        self._db_name = db_name
        self._collection_name = collection_name
        self._max_session_age_days = max_session_age_days
        self._client = None
        self._db = None
        self._collection = None
        self._checkpointers = {}  # Store checkpointers by graph_id
        
    async def initialize(self, mongo_uri: str = None):
        """Initialize the MongoDB connection
        
        Args:
            mongo_uri: Optional MongoDB URI to override the one provided in __init__
        """
        if mongo_uri:
            self._mongo_uri = mongo_uri
            
        if not self._mongo_uri:
            # First try to get MongoDB config from environment variables
            mongo_host = os.environ.get("MONGODB_HOST", "localhost")
            mongo_port = os.environ.get("MONGODB_PORT", "27017")
            mongo_user = os.environ.get("MONGODB_USER")
            mongo_password = os.environ.get("MONGODB_PASSWORD")
            mongo_db = os.environ.get("MONGODB_DB_NAME", "haley_ai")
            
            # Build connection URI from environment variables
            if mongo_user and mongo_password:
                self._mongo_uri = f"mongodb://{mongo_user}:{mongo_password}@{mongo_host}:{mongo_port}/{mongo_db}"
            else:
                self._mongo_uri = f"mongodb://{mongo_host}:{mongo_port}/{mongo_db}"
            
            # If no environment variables, try config_manager
            if not mongo_host or not mongo_port:
                mongo_config = config_manager.get_config("mongodb")
                if mongo_config:
                    self._db_name = os.environ.get("MONGODB_MEM_DB_NAME", "haley_ai")
                    self._mongo_uri = mongo_config.connection_url
                else:
                    raise ValueError("MongoDB URI is required")
            
        try:
            self._client = AsyncMongoClient(self._mongo_uri)
            self._db = self._client[self._db_name]
            self._collection = self._db[self._collection_name]
            
            # Create indexes for efficient querying
            await self._collection.create_index("thread_id")
            await self._collection.create_index("timestamp")
            await self._collection.create_index("checkpoint_id")
            
            return True
        except PyMongoError as e:
            print(f"Error initializing MongoDB connection: {e}")
            return False
    
    def create_checkpointer(self, graph_id: str = "default") -> AsyncMongoDBSaver:
        """Create a MongoDB checkpointer for a LangGraph
        
        Args:
            graph_id: Identifier for the graph (used to store multiple checkpointers)
            
        Returns:
            AsyncMongoDBSaver: A checkpointer that can be used with LangGraph
        """
        if self._client is None:
            raise RuntimeError("Session memory service not initialized")
            
        # LangGraph's AsyncMongoDBSaver uses specific collection names
        # We need to use these names to ensure compatibility
        checkpointer = AsyncMongoDBSaver(
            self._client,
            db_name=self._db_name,
            checkpoint_collection_name="checkpoints_aio",
            writes_collection_name="checkpoint_writes_aio"
        )
        
        # Store the checkpointer for later use
        self._checkpointers[graph_id] = checkpointer
        
        return checkpointer
    
    async def get_session_history(
        self, 
        thread_id: str,
        limit: int = 100,
        skip: int = 0,
        as_langchain_messages: bool = True
    ) -> List[Union[Dict, BaseMessage]]:
        """Get the message history for a session
        
        Args:
            thread_id: The thread ID to retrieve history for
            limit: Maximum number of messages to return
            skip: Number of messages to skip (for pagination)
            as_langchain_messages: If True, returns LangChain message objects
            
        Returns:
            List of message objects (either dicts or LangChain messages)
        """
        if self._client is None:
            raise RuntimeError("Session memory service not initialized")
            
        # Access the checkpoints_aio collection directly
        checkpoints_collection = self._db["checkpoints_aio"]
            
        # Find the latest checkpoint for this thread_id
        # The thread_id is stored directly in the document
        checkpoint_doc = await checkpoints_collection.find_one(
            {"thread_id": thread_id},
            sort=[("checkpoint_id", -1)]  # Sort by checkpoint_id instead of timestamp
        )
        
        if not checkpoint_doc:
            return []
            
        # Use the checkpointer to retrieve and deserialize the checkpoint
        config = {"configurable": {"thread_id": thread_id}}
        graph_id = checkpoint_doc.get("graph_id", "default")
        checkpointer = self._checkpointers.get(graph_id)
        
        if checkpointer is None:
            # Create a temporary checkpointer if needed
            checkpointer = self.create_checkpointer(graph_id)
            
        # Get the checkpoint tuple
        checkpoint_tuple = await checkpointer.aget_tuple(config)
        
        if not checkpoint_tuple or not checkpoint_tuple.checkpoint:
            return []
            
        # Extract messages from the checkpoint's channel_values
        messages = checkpoint_tuple.checkpoint.get("channel_values", {}).get("messages", [])
        
        # Apply pagination if needed
        if skip or limit:
            messages = messages[skip:skip+limit]
            
        # Convert to LangChain message objects if requested
        if as_langchain_messages and not all(isinstance(msg, BaseMessage) for msg in messages):
            return self._convert_to_langchain_messages(messages)
        
        return messages
    
    def _convert_to_langchain_messages(self, messages: List[Dict]) -> List[BaseMessage]:
        """Convert internal message format to LangChain message objects
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            List of LangChain message objects
        """
        result = []
        
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            msg_id = msg.get("id")
            additional_kwargs = msg.get("additional_kwargs", {})
            
            # Add tool calls to additional_kwargs if present
            if msg.get("tool_calls"):
                additional_kwargs["tool_calls"] = msg.get("tool_calls")
            
            # Create the appropriate message type based on role
            if role == "human":
                message = HumanMessage(
                    content=content,
                    additional_kwargs=additional_kwargs,
                    id=msg_id
                )
            elif role == "ai":
                message = AIMessage(
                    content=content,
                    additional_kwargs=additional_kwargs,
                    id=msg_id
                )
            elif role == "tool":
                message = ToolMessage(
                    content=content,
                    tool_call_id=msg.get("tool_call_id", ""),
                    name=additional_kwargs.get("name", ""),
                    id=msg_id
                )
            elif role == "system":
                message = SystemMessage(
                    content=content,
                    additional_kwargs=additional_kwargs,
                    id=msg_id
                )
            else:
                # Default to a base message if role is unknown
                message = BaseMessage(
                    content=content,
                    additional_kwargs=additional_kwargs,
                    id=msg_id
                )
                
            result.append(message)
            
        return result
    
    async def get_checkpoint(self, thread_id: str) -> Optional[CheckpointTuple]:
        """Get the raw checkpoint for a thread
        
        Args:
            thread_id: The thread ID to retrieve
            
        Returns:
            CheckpointTuple or None if not found
        """
        if self._client is None:
            raise RuntimeError("Session memory service not initialized")
            
        # Access the checkpoints_aio collection directly
        checkpoints_collection = self._db["checkpoints_aio"]
            
        # Find the latest checkpoint for this thread_id
        checkpoint_doc = await checkpoints_collection.find_one(
            {"thread_id": thread_id},
            sort=[("checkpoint_id", -1)]
        )
        
        if not checkpoint_doc:
            return None
            
        # Convert to CheckpointTuple format
        config = {"configurable": {"thread_id": thread_id}}
        
        # The checkpointer will handle the actual retrieval
        graph_id = checkpoint_doc.get("graph_id", "default")
        checkpointer = self._checkpointers.get(graph_id)
        
        if checkpointer is None:
            checkpointer = self.create_checkpointer(graph_id)
            
        # Get the checkpoint tuple
        checkpoint_tuple = await checkpointer.aget_tuple(config)
        
        # Ensure checkpoint has all required fields
        if checkpoint_tuple and checkpoint_tuple.checkpoint:
            checkpoint = checkpoint_tuple.checkpoint
            if "channel_versions" not in checkpoint:
                checkpoint["channel_versions"] = {}
            if "pending_sends" not in checkpoint:
                checkpoint["pending_sends"] = []
            if "pending_receives" not in checkpoint:
                checkpoint["pending_receives"] = []
            if "pending_tasks" not in checkpoint:
                checkpoint["pending_tasks"] = []
            if "versions_seen" not in checkpoint:
                checkpoint["versions_seen"] = {}
            if "task_counter" not in checkpoint:
                checkpoint["task_counter"] = 0
                
        # Ensure metadata has required fields
        if checkpoint_tuple and checkpoint_tuple.metadata:
            metadata = checkpoint_tuple.metadata
            if "step" not in metadata:
                metadata["step"] = 0
            if "timestamp" not in metadata:
                metadata["timestamp"] = datetime.now(timezone.utc).isoformat()
            if "graph_id" not in metadata:
                metadata["graph_id"] = graph_id
            
        return checkpoint_tuple
    
    async def list_sessions(
        self,
        limit: int = 100,
        skip: int = 0,
        sort_by: str = "checkpoint_id",  # Changed from timestamp to checkpoint_id
        sort_order: int = -1  # -1 for descending, 1 for ascending
    ) -> List[Dict]:
        """List available sessions
        
        Args:
            limit: Maximum number of sessions to return
            skip: Number of sessions to skip (for pagination)
            sort_by: Field to sort by
            sort_order: Sort direction (1 for ascending, -1 for descending)
            
        Returns:
            List of session metadata
        """
        if self._client is None:
            raise RuntimeError("Session memory service not initialized")
            
        # Access the checkpoints_aio collection directly
        checkpoints_collection = self._db["checkpoints_aio"]
            
        # Get distinct thread_ids with their latest checkpoint
        # The thread_id is stored directly in the document
        pipeline = [
            {"$sort": {sort_by: sort_order}},
            {"$group": {
                "_id": "$thread_id",  # Group by thread_id directly
                "checkpoint_id": {"$first": "$checkpoint_id"},
                "timestamp": {"$first": "$timestamp"},
                "metadata": {"$first": "$metadata"}
            }},
            {"$sort": {sort_by: sort_order}},
            {"$skip": skip},
            {"$limit": limit}
        ]
        
        cursor = await checkpoints_collection.aggregate(pipeline)
        sessions = await cursor.to_list(length=limit)
        
        # Enhance sessions with message count
        for session in sessions:
            thread_id = session.get("_id")
            if thread_id:
                # Get the message count for this thread
                try:
                    messages = await self.get_langchain_messages(thread_id)
                    session["message_count"] = len(messages)
                except Exception:
                    # If there's an error, just set the count to 0
                    session["message_count"] = 0
            else:
                session["message_count"] = 0
        
        return sessions
    
    async def delete_session(self, thread_id: str) -> bool:
        """Delete a session and all its checkpoints
        
        Args:
            thread_id: The thread ID to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self._client is None:
            raise RuntimeError("Session memory service not initialized")
            
        try:
            # Access the checkpoints_aio and checkpoint_writes_aio collections directly
            checkpoints_collection = self._db["checkpoints_aio"]
            writes_collection = self._db["checkpoint_writes_aio"]
            
            # The thread_id is stored directly in the document
            checkpoints_result = await checkpoints_collection.delete_many({"thread_id": thread_id})
            writes_result = await writes_collection.delete_many({"thread_id": thread_id})
            
            return checkpoints_result.deleted_count > 0 or writes_result.deleted_count > 0
        except PyMongoError as e:
            print(f"Error deleting session {thread_id}: {e}")
            return False
    
    async def cleanup_old_sessions(self, days: int = None) -> int:
        """Clean up sessions older than the specified number of days
        
        Args:
            days: Number of days to keep (defaults to max_session_age_days)
            
        Returns:
            int: Number of sessions cleaned up
        """
        if self._collection is None:
            raise RuntimeError("Session memory service not initialized")
            
        if days is None:
            days = self._max_session_age_days
            
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        try:
            result = await self._collection.delete_many({"timestamp": {"$lt": cutoff_date}})
            return result.deleted_count
        except PyMongoError as e:
            print(f"Error cleaning up old sessions: {e}")
            return 0
    
    async def convert_checkpoint_to_messages(
        self, 
        checkpoint: CheckpointTuple
    ) -> List[MessageModel]:
        """Convert a LangGraph checkpoint to our message format
        
        Args:
            checkpoint: The checkpoint tuple from LangGraph
            
        Returns:
            List of MessageModel objects
        """
        if not checkpoint or not checkpoint.checkpoint:
            return []
            
        # Extract messages from the checkpoint
        raw_messages = checkpoint.checkpoint.get("channel_values", {}).get("messages", [])
        
        # Convert to our message format
        messages = []
        for msg in raw_messages:
            # Determine the role based on message type
            if hasattr(msg, "type") and msg.type == "tool":
                role = "tool"
            elif hasattr(msg, "type") and msg.type == "human":
                role = "human"
            elif hasattr(msg, "type") and msg.type == "system":
                role = "system"
            else:
                role = "ai"
                
            # Extract content and metadata
            content = msg.content if hasattr(msg, "content") else ""
            msg_id = msg.id if hasattr(msg, "id") else str(uuid.uuid4())
            metadata = msg.response_metadata if hasattr(msg, "response_metadata") else {}
            additional_kwargs = msg.additional_kwargs if hasattr(msg, "additional_kwargs") else {}
            
            # Extract tool calls if present
            tool_calls = None
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                tool_calls = [
                    {
                        "name": tc.get("name"),
                        "args": tc.get("args"),
                        "id": tc.get("id")
                    }
                    for tc in msg.tool_calls
                ]
                
            # Extract tool_call_id if present
            tool_call_id = msg.tool_call_id if hasattr(msg, "tool_call_id") else None
            
            message = MessageModel(
                role=role,
                content=content,
                id=msg_id,
                metadata=metadata,
                tool_calls=tool_calls,
                tool_call_id=tool_call_id,
                additional_kwargs=additional_kwargs
            )
            messages.append(message)
            
        return messages
    
    async def get_langchain_messages(self, thread_id: str) -> List[BaseMessage]:
        """Get the message history for a session as LangChain message objects
        
        This is a convenience method that directly returns LangChain message objects
        
        Args:
            thread_id: The thread ID to retrieve history for
            
        Returns:
            List of LangChain message objects
        """
        return await self.get_session_history(
            thread_id=thread_id,
            as_langchain_messages=True
        )
    
    async def cleanup(self):
        """Close connections and perform cleanup"""
        if self._client is not None:
            await self._client.close()
            self._client = None
            self._db = None
            self._collection = None