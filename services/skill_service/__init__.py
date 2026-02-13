"""
Skill Service - Business logic layer for skill classification and management.

Provides:
- SkillRepository: Data access for skill tables
- SkillService: Business logic for classification, embeddings, and management
"""

from .skill_repository import SkillRepository
from .skill_service import SkillService

__all__ = ["SkillRepository", "SkillService"]
