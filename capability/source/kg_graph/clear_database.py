# scripts/clear_database.py
from neo4j import GraphDatabase
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseCleaner:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        
    def close(self):
        self.driver.close()
        
    def clear_all_data(self):
        """清空所有数据"""
        with self.driver.session() as session:
            # 1. 获取所有约束
            constraints = session.run("SHOW CONSTRAINTS").data()
            
            # 2. 删除所有约束
            for constraint in constraints:
                constraint_name = constraint.get('name')
                if constraint_name:
                    session.run(f"DROP CONSTRAINT {constraint_name}")
                    logger.info(f"Dropped constraint: {constraint_name}")
            
            # 3. 获取所有索引
            indexes = session.run("SHOW INDEXES").data()
            
            # 4. 删除所有索引
            for index in indexes:
                index_name = index.get('name')
                if index_name:
                    session.run(f"DROP INDEX {index_name}")
                    logger.info(f"Dropped index: {index_name}")
            
            # 5. 删除所有数据
            session.run("MATCH (n) DETACH DELETE n")
            logger.info("Deleted all nodes and relationships")
            
    def verify_empty(self) -> bool:
        """验证数据库是否为空"""
        with self.driver.session() as session:
            # 检查节点数量
            result = session.run("MATCH (n) RETURN count(n) as count")
            node_count = result.single()["count"]
            
            # 检查关系数量
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = result.single()["count"]
            
            # 检查约束数量
            constraints = session.run("SHOW CONSTRAINTS").data()
            constraint_count = len(constraints)
            
            # 检查索引数量
            indexes = session.run("SHOW INDEXES").data()
            index_count = len(indexes)
            
            is_empty = (node_count == 0 and rel_count == 0 
                       and constraint_count == 0 and index_count == 0)
            
            logger.info(f"""Database status:
            - Nodes: {node_count}
            - Relationships: {rel_count}
            - Constraints: {constraint_count}
            - Indexes: {index_count}
            """)
            
            return is_empty

def main():
    # 替换为你的Neo4j连接信息
    uri = "bolt://neo4j:7687"
    user = "neo4j"
    password = "admin@123"  # 替换为你的密码
    
    cleaner = DatabaseCleaner(uri, user, password)
    try:
        # 1. 清空数据库
        logger.info("Starting database cleanup...")
        cleaner.clear_all_data()
        
        # 2. 验证是否清空
        if cleaner.verify_empty():
            logger.info("Database successfully cleared")
        else:
            logger.error("Database not completely cleared!")
            
    finally:
        cleaner.close()

if __name__ == "__main__":
    print("WARNING: This will delete ALL data in the database!")
    confirmation = input("Are you sure you want to proceed? (type 'YES' to confirm): ")
    
    if confirmation == "YES":
        main()
    else:
        print("Operation cancelled.")