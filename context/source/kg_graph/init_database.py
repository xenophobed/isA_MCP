# scripts/init_database.py
from neo4j import GraphDatabase
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseInitializer:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        
    def close(self):
        self.driver.close()
        
    def init_constraints(self):
        """初始化必要的约束"""
        with self.driver.session() as session:
            constraints = [
                # User相关约束
                "CREATE CONSTRAINT IF NOT EXISTS FOR (n:User) REQUIRE n.id IS UNIQUE",
                
                # Conversation相关约束
                "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Conversation) REQUIRE n.id IS UNIQUE",
                
                # Intent相关约束
                "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Intent) REQUIRE n.id IS UNIQUE",
                
                # Product相关约束
                "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Product) REQUIRE n.id IS UNIQUE",
                
                # Topic相关约束
                "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Topic) REQUIRE n.id IS UNIQUE"
            ]
            
            for constraint in constraints:
                try:
                    session.run(constraint)
                    logger.info(f"Created constraint: {constraint}")
                except Exception as e:
                    logger.error(f"Failed to create constraint: {str(e)}")

def main():
    # 替换为你的Neo4j连接信息
    uri = "bolt://neo4j:7687"
    user = "neo4j"
    password = "admin@123"  # 替换为你的密码
    
    initializer = DatabaseInitializer(uri, user, password)
    try:
        logger.info("Starting database initialization...")
        initializer.init_constraints()
        logger.info("Database initialization completed")
        
    finally:
        initializer.close()

if __name__ == "__main__":
    main()