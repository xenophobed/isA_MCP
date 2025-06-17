#!/usr/bin/env python
"""
Database initialization and management for MCP Server SQLite database
"""
import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def init_database(db_path: str = "memory.db"):
    """Initialize database with monitoring and authorization tables"""
    conn = sqlite3.connect(db_path)
    
    # Drop existing tables
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
    conn.close()
    logger.info("Database initialized with security and monitoring tables")

def add_sample_data(db_path: str = "memory.db"):
    """Add sample data to database"""
    conn = sqlite3.connect(db_path)
    try:
        now = datetime.now().isoformat()
        sample_memories = [
            ("user_name", "Assistant User", "personal", 5, "system"),
            ("api_guidelines", "Always use structured JSON responses", "technical", 5, "system"),
            ("security_policy", "All high-security operations require authorization", "security", 5, "system")
        ]
        
        for key, value, category, importance, created_by in sample_memories:
            conn.execute("""
                INSERT OR IGNORE INTO memories (key, value, category, importance, created_at, updated_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (key, value, category, importance, now, now, created_by))
        
        conn.commit()
        logger.info("Sample data initialized")
    finally:
        conn.close()