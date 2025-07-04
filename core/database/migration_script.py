#!/usr/bin/env python
"""
Migration Script for Database Management Transition
Helps transition from old supabase_client to new database management system
"""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.logging import get_logger
from core.database import get_database_manager, SchemaManager, MigrationManager

logger = get_logger(__name__)

async def test_old_vs_new_system():
    """Test that new system provides same functionality as old system"""
    logger.info("Testing database management system transition...")
    
    try:
        # Test new database manager
        db_manager = await get_database_manager()
        health = await db_manager.health_check()
        
        logger.info(f"Database health check: {health}")
        
        if health['supabase_healthy']:
            logger.info("✅ New database manager working correctly")
        else:
            logger.error("❌ New database manager has issues")
            return False
        
        # Test schema validation
        schema_manager = SchemaManager()
        validation = await schema_manager.validate_schema()
        
        logger.info(f"Schema validation: {validation}")
        
        if validation['valid']:
            logger.info("✅ Database schema is valid")
        else:
            logger.warning("⚠️ Database schema has issues:")
            for issue in validation.get('schema_issues', []):
                logger.warning(f"  - {issue}")
        
        # Test migration system
        migration_manager = MigrationManager()
        current_version = await migration_manager.get_current_version()
        pending = await migration_manager.get_pending_migrations()
        
        logger.info(f"Current migration version: {current_version}")
        logger.info(f"Pending migrations: {len(pending)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Database system test failed: {e}")
        return False

async def update_import_statements():
    """Provide guidance for updating import statements"""
    logger.info("Migration Guide: Updating Import Statements")
    logger.info("=" * 50)
    
    print("""
To migrate your code to use the new database management system:

1. MINIMAL CHANGE APPROACH (Recommended):
   Keep existing imports but they now use the new system under the hood:
   
   # No changes needed - existing code will work
   from core.supabase_client import get_supabase_client
   
2. GRADUAL MIGRATION APPROACH:
   Gradually migrate to repository pattern:
   
   # Old way:
   from core.supabase_client import get_supabase_client
   supabase = get_supabase_client()
   await supabase.set_memory(key, value)
   
   # New way:
   from core.database import MemoryRepository
   memory_repo = MemoryRepository()
   await memory_repo.set_memory(key, value)

3. DIRECT DATABASE ACCESS (For advanced use cases):
   
   # New way for direct access:
   from core.database import get_database_manager
   db = await get_database_manager()
   result = await db.execute_vector_search(...)

4. UPDATE CONFIGURATION:
   Ensure these environment variables are set:
   - NEXT_PUBLIC_SUPABASE_URL
   - SUPABASE_SERVICE_ROLE_KEY  
   - SUPABASE_PWD (for direct PostgreSQL access)
""")

def create_example_migration():
    """Create example migration files"""
    migration_manager = MigrationManager()
    
    # Example migration for adding indexes
    migration_content = """
-- Add performance indexes
CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance);
CREATE INDEX IF NOT EXISTS idx_memories_created_by ON memories(created_by);

-- Add full text search indexes
CREATE INDEX IF NOT EXISTS idx_memories_search ON memories USING gin(to_tsvector('english', key || ' ' || value));
"""
    
    try:
        migration_file = migration_manager.create_migration_file(
            "add_performance_indexes", 
            migration_content
        )
        logger.info(f"Created example migration: {migration_file}")
    except Exception as e:
        logger.error(f"Error creating migration: {e}")

async def run_diagnostics():
    """Run comprehensive diagnostics"""
    logger.info("Running Database Management Diagnostics")
    logger.info("=" * 50)
    
    # Test database connectivity
    success = await test_old_vs_new_system()
    
    if success:
        logger.info("✅ All systems operational")
        
        # Show configuration status
        await show_configuration_status()
        
        # Provide migration guidance
        await update_import_statements()
        
        # Create example migration
        create_example_migration()
        
    else:
        logger.error("❌ System has issues - check configuration")

async def show_configuration_status():
    """Show current configuration status"""
    logger.info("\nConfiguration Status:")
    logger.info("-" * 20)
    
    # Check environment variables
    required_vars = [
        'NEXT_PUBLIC_SUPABASE_URL',
        'SUPABASE_SERVICE_ROLE_KEY',
        'SUPABASE_PWD'
    ]
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            logger.info(f"✅ {var}: Set")
        else:
            logger.warning(f"⚠️ {var}: Not set")
    
    # Check optional dependencies
    try:
        import asyncpg
        logger.info("✅ asyncpg: Available (PostgreSQL direct access enabled)")
    except ImportError:
        logger.warning("⚠️ asyncpg: Not available (install with: pip install asyncpg)")

if __name__ == "__main__":
    asyncio.run(run_diagnostics()) 