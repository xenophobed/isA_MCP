#!/usr/bin/env python
"""
Database Initialization for MCP Server
Handles database setup and sample data loading
"""
from datetime import datetime

from core.logging import get_logger
from core.supabase_client import get_supabase_client

logger = get_logger(__name__)

def init_database():
    """Initialize Supabase database (tables should already exist)"""
    try:
        supabase = get_supabase_client()
        logger.info("Supabase database connection verified")
        
        # Verify that required tables exist
        required_tables = ['memories', 'weather_cache', 'authorization_requests', 'audit_log']
        for table in required_tables:
            try:
                result = supabase.client.table(table).select('*').limit(1).execute()
                logger.info(f"✓ Table {table} exists")
            except Exception as e:
                logger.warning(f"⚠ Table {table} may not exist: {e}")
        
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

async def load_sample_data():
    """Load sample data into Supabase database"""
    try:
        supabase = get_supabase_client()
        
        # Sample memories (only add if they don't exist)
        sample_memories = [
            ("user_name", "Assistant User", "personal", 5, "system"),
            ("api_guidelines", "Always use structured JSON responses", "technical", 5, "system"),
            ("security_policy", "All high-security operations require authorization", "security", 5, "system"),
            ("weather_preference", "User prefers detailed weather information", "preference", 3, "system"),
            ("memory_categories", "Use categories: personal, technical, security, preference, general", "technical", 4, "system")
        ]
        
        loaded_count = 0
        for key, value, category, importance, created_by in sample_memories:
            # Check if memory already exists
            existing = await supabase.get_memory(key)
            if not existing:
                success = await supabase.set_memory(key, value, category, importance, created_by)
                if success:
                    loaded_count += 1
        
        logger.info(f"Sample data loaded: {loaded_count} new memory entries")
        
    except Exception as e:
        logger.error(f"Error loading sample data: {e}")
        raise

async def initialize_database():
    """Complete database initialization process"""
    logger.info("Starting Supabase database initialization...")
    init_database()
    await load_sample_data()
    logger.info("Database initialization completed successfully") 