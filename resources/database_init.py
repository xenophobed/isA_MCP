#!/usr/bin/env python
"""
Database Initialization for MCP Server
Handles database setup and sample data loading
"""
import sqlite3
from datetime import datetime

from core.logging import get_logger

logger = get_logger(__name__)

def init_database():
    """Initialize database with monitoring and authorization tables"""
    conn = sqlite3.connect("memory.db")
    
    try:
        # Drop existing tables for clean initialization
        tables_to_drop = ["memories", "weather_cache", "prompt_usage", "authorization_requests", "audit_log"]
        for table in tables_to_drop:
            conn.execute(f"DROP TABLE IF EXISTS {table}")
        
        # Create core tables
        conn.execute("""
        CREATE TABLE memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL UNIQUE,
            value TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'general',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            importance INTEGER DEFAULT 1,
            created_by TEXT DEFAULT 'system'
        )
        """)
        
        conn.execute("""
        CREATE TABLE weather_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT NOT NULL,
            weather_data TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)
        
        conn.execute("""
        CREATE TABLE prompt_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt_name TEXT NOT NULL,
            arguments TEXT NOT NULL,
            used_at TEXT NOT NULL,
            context TEXT,
            user_id TEXT DEFAULT 'default'
        )
        """)
        
        # Authorization table
        conn.execute("""
        CREATE TABLE authorization_requests (
            id TEXT PRIMARY KEY,
            tool_name TEXT NOT NULL,
            arguments TEXT NOT NULL,
            user_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            security_level TEXT NOT NULL,
            reason TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            status TEXT NOT NULL,
            approved_by TEXT
        )
        """)
        
        # Audit log table
        conn.execute("""
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            user_id TEXT NOT NULL,
            success BOOLEAN NOT NULL,
            execution_time REAL NOT NULL,
            security_level TEXT NOT NULL,
            details TEXT
        )
        """)
        
        conn.commit()
        logger.info("Database tables created successfully")
        
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise
    finally:
        conn.close()

def load_sample_data():
    """Load sample data into the database"""
    conn = sqlite3.connect("memory.db")
    
    try:
        now = datetime.now().isoformat()
        
        # Sample memories
        sample_memories = [
            ("user_name", "Assistant User", "personal", 5, "system"),
            ("api_guidelines", "Always use structured JSON responses", "technical", 5, "system"),
            ("security_policy", "All high-security operations require authorization", "security", 5, "system"),
            ("weather_preference", "User prefers detailed weather information", "preference", 3, "system"),
            ("memory_categories", "Use categories: personal, technical, security, preference, general", "technical", 4, "system")
        ]
        
        for key, value, category, importance, created_by in sample_memories:
            conn.execute("""
                INSERT OR IGNORE INTO memories (key, value, category, importance, created_at, updated_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (key, value, category, importance, now, now, created_by))
        
        conn.commit()
        logger.info(f"Sample data loaded: {len(sample_memories)} memory entries")
        
    except Exception as e:
        logger.error(f"Error loading sample data: {e}")
        raise
    finally:
        conn.close()

def initialize_database():
    """Complete database initialization process"""
    logger.info("Starting database initialization...")
    init_database()
    load_sample_data()
    logger.info("Database initialization completed successfully") 