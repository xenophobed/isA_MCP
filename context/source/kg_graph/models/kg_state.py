# app/kg/models/kg_state.py
from typing import Dict, List, Optional
from pydantic import BaseModel

class KGState(BaseModel):
    """State model for knowledge graph operations"""
    session_id: str
    user_id: str
    current_context: Dict
    extracted_entities: Optional[List[Dict]] = None
    extracted_relations: Optional[List[Dict]] = None
    query_results: Optional[Dict] = None