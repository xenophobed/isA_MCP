#!/usr/bin/env python
"""
Database Migration Manager
Handles database schema migrations and versioning
"""
import os
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

from core.logging import get_logger
from .connection_manager import get_database_manager

logger = get_logger(__name__)

class MigrationManager:
    """Manages database migrations"""
    
    def __init__(self):
        self.migration_dir = Path(__file__).parent / "migrations"
        self.migration_dir.mkdir(parents=True, exist_ok=True)
    
    async def get_current_version(self) -> int:
        """Get current database schema version"""
        try:
            db = await get_database_manager()
            
            # Check if migration_history table exists
            try:
                result = db.supabase.table('migration_history').select('version').order('version', desc=True).limit(1).execute()
                if result.data:
                    return result.data[0]['version']
                return 0
            except:
                # Migration table doesn't exist, create it
                await self._create_migration_table()
                return 0
        except Exception as e:
            logger.error(f"Error getting current version: {e}")
            return 0
    
    async def _create_migration_table(self):
        """Create migration history table"""
        try:
            db = await get_database_manager()
            
            create_sql = """
            CREATE TABLE IF NOT EXISTS migration_history (
                id SERIAL PRIMARY KEY,
                version INTEGER NOT NULL UNIQUE,
                name TEXT NOT NULL,
                applied_at TIMESTAMPTZ DEFAULT NOW(),
                checksum TEXT
            )
            """
            
            await db.execute_query(create_sql)
            logger.info("Migration history table created")
        except Exception as e:
            logger.error(f"Error creating migration table: {e}")
            raise
    
    async def get_pending_migrations(self) -> List[Dict[str, Any]]:
        """Get list of pending migrations"""
        current_version = await self.get_current_version()
        all_migrations = self._load_migration_files()
        
        pending = [
            migration for migration in all_migrations 
            if migration['version'] > current_version
        ]
        
        return sorted(pending, key=lambda x: x['version'])
    
    def _load_migration_files(self) -> List[Dict[str, Any]]:
        """Load migration files from migration directory"""
        migrations = []
        
        for migration_file in self.migration_dir.glob("*.sql"):
            try:
                # Parse filename: 001_create_memories_table.sql
                parts = migration_file.stem.split('_', 1)
                version = int(parts[0])
                name = parts[1] if len(parts) > 1 else migration_file.stem
                
                with open(migration_file, 'r') as f:
                    content = f.read()
                
                migrations.append({
                    'version': version,
                    'name': name,
                    'file': str(migration_file),
                    'content': content
                })
            except Exception as e:
                logger.warning(f"Error loading migration file {migration_file}: {e}")
        
        return migrations
    
    async def apply_migrations(self, target_version: Optional[int] = None) -> Dict[str, Any]:
        """Apply pending migrations up to target version"""
        try:
            pending_migrations = await self.get_pending_migrations()
            
            if target_version:
                pending_migrations = [
                    m for m in pending_migrations 
                    if m['version'] <= target_version
                ]
            
            if not pending_migrations:
                return {
                    'success': True,
                    'message': 'No pending migrations',
                    'applied_count': 0
                }
            
            applied_count = 0
            db = await get_database_manager()
            
            for migration in pending_migrations:
                try:
                    logger.info(f"Applying migration {migration['version']}: {migration['name']}")
                    
                    # Execute migration SQL
                    await db.execute_query(migration['content'])
                    
                    # Record in migration history
                    await self._record_migration(migration)
                    
                    applied_count += 1
                    logger.info(f"Migration {migration['version']} applied successfully")
                    
                except Exception as e:
                    logger.error(f"Migration {migration['version']} failed: {e}")
                    return {
                        'success': False,
                        'error': str(e),
                        'failed_migration': migration['version'],
                        'applied_count': applied_count
                    }
            
            return {
                'success': True,
                'message': f'Applied {applied_count} migrations',
                'applied_count': applied_count
            }
            
        except Exception as e:
            logger.error(f"Migration process failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'applied_count': 0
            }
    
    async def _record_migration(self, migration: Dict[str, Any]):
        """Record applied migration in history"""
        try:
            db = await get_database_manager()
            
            db.supabase.table('migration_history').insert({
                'version': migration['version'],
                'name': migration['name'],
                'applied_at': datetime.now().isoformat(),
                'checksum': self._calculate_checksum(migration['content'])
            }).execute()
            
        except Exception as e:
            logger.error(f"Error recording migration: {e}")
            raise
    
    def _calculate_checksum(self, content: str) -> str:
        """Calculate checksum for migration content"""
        import hashlib
        return hashlib.md5(content.encode()).hexdigest()
    
    async def rollback_migration(self, target_version: int) -> Dict[str, Any]:
        """Rollback to a specific version (if rollback scripts exist)"""
        try:
            current_version = await self.get_current_version()
            
            if target_version >= current_version:
                return {
                    'success': False,
                    'error': 'Target version must be lower than current version'
                }
            
            # Load rollback migrations (down migrations)
            rollback_migrations = self._load_rollback_migrations(target_version, current_version)
            
            if not rollback_migrations:
                return {
                    'success': False,
                    'error': 'No rollback migrations found'
                }
            
            db = await get_database_manager()
            rolled_back = 0
            
            for migration in rollback_migrations:
                try:
                    logger.info(f"Rolling back migration {migration['version']}")
                    
                    # Execute rollback SQL
                    await db.execute_query(migration['content'])
                    
                    # Remove from migration history
                    db.supabase.table('migration_history').delete().eq('version', migration['version']).execute()
                    
                    rolled_back += 1
                    
                except Exception as e:
                    logger.error(f"Rollback of migration {migration['version']} failed: {e}")
                    return {
                        'success': False,
                        'error': str(e),
                        'rolled_back_count': rolled_back
                    }
            
            return {
                'success': True,
                'message': f'Rolled back {rolled_back} migrations',
                'rolled_back_count': rolled_back
            }
            
        except Exception as e:
            logger.error(f"Rollback process failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'rolled_back_count': 0
            }
    
    def _load_rollback_migrations(self, target_version: int, current_version: int) -> List[Dict[str, Any]]:
        """Load rollback migration files"""
        rollbacks = []
        
        for version in range(current_version, target_version, -1):
            rollback_file = self.migration_dir / f"{version:03d}_rollback.sql"
            
            if rollback_file.exists():
                try:
                    with open(rollback_file, 'r') as f:
                        content = f.read()
                    
                    rollbacks.append({
                        'version': version,
                        'content': content
                    })
                except Exception as e:
                    logger.warning(f"Error loading rollback file {rollback_file}: {e}")
        
        return rollbacks
    
    def create_migration_file(self, name: str, content: str) -> str:
        """Create a new migration file"""
        try:
            # Get next version number
            migrations = self._load_migration_files()
            next_version = max([m['version'] for m in migrations], default=0) + 1
            
            # Create filename
            filename = f"{next_version:03d}_{name.lower().replace(' ', '_')}.sql"
            migration_file = self.migration_dir / filename
            
            # Write migration content
            with open(migration_file, 'w') as f:
                f.write(f"-- Migration: {name}\n")
                f.write(f"-- Version: {next_version}\n")
                f.write(f"-- Created: {datetime.now().isoformat()}\n\n")
                f.write(content)
            
            logger.info(f"Created migration file: {filename}")
            return str(migration_file)
            
        except Exception as e:
            logger.error(f"Error creating migration file: {e}")
            raise 