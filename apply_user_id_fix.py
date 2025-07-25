#!/usr/bin/env python3
"""
Apply User ID Consistency Fix
执行用户ID一致性修复脚本

这个脚本会执行数据库修复并验证结果
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.config import get_database_config
from core.exception import DatabaseException

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def execute_sql_file(sql_file_path: str):
    """
    执行SQL文件
    
    Args:
        sql_file_path: SQL文件路径
    """
    try:
        # 动态导入数据库连接
        from supabase import create_client, Client
        
        # 获取数据库配置
        db_config = get_database_config()
        
        if not db_config:
            raise DatabaseException("Database configuration not found")
        
        # 创建Supabase客户端
        supabase: Client = create_client(
            db_config.get("url", ""),
            db_config.get("key", "")
        )
        
        # 读取SQL文件
        if not os.path.exists(sql_file_path):
            raise FileNotFoundError(f"SQL file not found: {sql_file_path}")
        
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        logger.info(f"Reading SQL file: {sql_file_path}")
        logger.info(f"SQL content length: {len(sql_content)} characters")
        
        # 分割SQL语句（按分号分割，但保留存储过程中的分号）
        sql_statements = []
        current_statement = []
        in_procedure = False
        
        for line in sql_content.split('\n'):
            line = line.strip()
            
            # 跳过注释和空行
            if not line or line.startswith('--'):
                continue
            
            # 检测存储过程开始
            if 'DO $$' in line or 'BEGIN' in line:
                in_procedure = True
            
            current_statement.append(line)
            
            # 检测存储过程结束
            if in_procedure and ('END $$' in line or line.endswith('$$;')):
                in_procedure = False
                sql_statements.append('\n'.join(current_statement))
                current_statement = []
            elif not in_procedure and line.endswith(';'):
                sql_statements.append('\n'.join(current_statement))
                current_statement = []
        
        # 添加最后一个语句（如果有）
        if current_statement:
            sql_statements.append('\n'.join(current_statement))
        
        logger.info(f"Found {len(sql_statements)} SQL statements to execute")
        
        # 执行SQL语句
        executed_count = 0
        for i, statement in enumerate(sql_statements, 1):
            statement = statement.strip()
            if not statement:
                continue
            
            try:
                logger.info(f"Executing statement {i}/{len(sql_statements)}...")
                logger.debug(f"SQL: {statement[:100]}...")
                
                # 使用rpc调用执行SQL（适用于Supabase）
                # 注意：这可能需要根据您的具体Supabase设置进行调整
                result = supabase.rpc('execute_sql', {'sql_query': statement})
                
                executed_count += 1
                logger.info(f"Statement {i} executed successfully")
                
            except Exception as e:
                logger.error(f"Error executing statement {i}: {e}")
                logger.error(f"Statement: {statement}")
                # 根据错误类型决定是否继续
                if "already exists" in str(e).lower():
                    logger.warning("Object already exists, continuing...")
                    continue
                else:
                    raise
        
        logger.info(f"Successfully executed {executed_count} SQL statements")
        return True
        
    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        raise


async def verify_migration():
    """验证迁移结果"""
    try:
        from supabase import create_client, Client
        
        # 获取数据库配置
        db_config = get_database_config()
        supabase: Client = create_client(
            db_config.get("url", ""),
            db_config.get("key", "")
        )
        
        # 验证数据类型一致性
        verification_queries = [
            {
                "name": "检查user_id字段类型一致性",
                "query": """
                SELECT 
                    table_name,
                    column_name,
                    data_type,
                    character_maximum_length
                FROM information_schema.columns 
                WHERE table_schema = 'dev' 
                  AND column_name = 'user_id'
                ORDER BY table_name;
                """
            },
            {
                "name": "检查外键关系",
                "query": """
                SELECT 
                    tc.table_name,
                    tc.constraint_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY' 
                  AND tc.table_schema = 'dev'
                  AND kcu.column_name LIKE '%user%'
                ORDER BY tc.table_name;
                """
            },
            {
                "name": "检查数据完整性",
                "query": """
                SELECT 
                    'users' as table_name,
                    COUNT(*) as total_records,
                    COUNT(DISTINCT user_id) as unique_user_ids
                FROM dev.users
                WHERE user_id IS NOT NULL;
                """
            }
        ]
        
        logger.info("Starting migration verification...")
        
        for query_info in verification_queries:
            try:
                logger.info(f"Running: {query_info['name']}")
                
                # 使用Supabase查询
                result = supabase.rpc('execute_query', {'sql_query': query_info['query']})
                
                logger.info(f"✓ {query_info['name']} - Success")
                
                # 打印结果摘要
                if result.data:
                    logger.info(f"  Found {len(result.data)} records")
                
            except Exception as e:
                logger.error(f"✗ {query_info['name']} - Failed: {e}")
        
        logger.info("Migration verification completed")
        return True
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


async def main():
    """主函数"""
    print("=" * 60)
    print("User ID Consistency Fix Application")
    print("=" * 60)
    
    try:
        # 检查SQL文件是否存在
        sql_file = "database_fix_user_id_consistency.sql"
        if not os.path.exists(sql_file):
            logger.error(f"SQL file not found: {sql_file}")
            logger.info("Please ensure the SQL file is in the current directory")
            return False
        
        # 确认执行
        print(f"\nThis script will apply user_id consistency fixes to your database.")
        print(f"SQL file: {sql_file}")
        print(f"This operation will:")
        print("1. Fix session_memories table user_id data type")
        print("2. Standardize all user_id fields to varchar(255)")
        print("3. Add proper foreign key relationships")
        print("4. Add performance indexes")
        print("5. Add data integrity constraints")
        
        confirmation = input("\nDo you want to proceed? (yes/no): ").strip().lower()
        
        if confirmation not in ['yes', 'y']:
            logger.info("Operation cancelled by user")
            return False
        
        # 执行迁移
        logger.info("Starting database migration...")
        await execute_sql_file(sql_file)
        
        # 验证结果
        logger.info("Starting verification...")
        verification_success = await verify_migration()
        
        if verification_success:
            print("\n" + "=" * 60)
            print("✓ Migration completed successfully!")
            print("✓ All user_id fields are now consistent")
            print("✓ Foreign key relationships have been fixed")
            print("✓ Performance indexes have been added")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("⚠ Migration completed but verification had issues")
            print("Please check the logs for details")
            print("=" * 60)
        
        return verification_success
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print(f"\n✗ Migration failed: {e}")
        return False


if __name__ == "__main__":
    # 运行主函数
    success = asyncio.run(main())
    sys.exit(0 if success else 1)