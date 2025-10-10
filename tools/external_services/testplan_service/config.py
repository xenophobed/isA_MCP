#!/usr/bin/env python3
"""
Configuration for Test Plan Service
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

class TestPlanServiceConfig(BaseModel):
    """Configuration for Test Plan Service"""
    
    # Database paths
    duckdb_path: str = Field(
        default_factory=lambda: str(Path(__file__).parent / "database" / "testplan.duckdb"),
        description="Path to local DuckDB file for test plan service"
    )
    
    # Service settings
    max_parallel_workers: int = Field(default=4, description="Max Dask workers for document processing")
    chunk_size: int = Field(default=1000, description="Chunk size for batch processing")
    
    # 3GPP document settings
    supported_releases: list[str] = Field(
        default=["Rel-15", "Rel-16", "Rel-17", "Rel-18"],
        description="Supported 3GPP releases"
    )
    
    supported_ue_categories: list[str] = Field(
        default=["FDD", "TDD", "NB-IoT", "eMTC"],
        description="Supported UE categories"
    )
    
    # Test plan generation settings
    default_optimization_priority: str = Field(default="balanced", description="Default optimization priority")
    max_test_plan_size: int = Field(default=1000, description="Maximum test cases in a plan")
    
    @property
    def duckdb_absolute_path(self) -> str:
        """Get absolute path to DuckDB file"""
        return os.path.abspath(self.duckdb_path)

# Global config instance
config = TestPlanServiceConfig()
