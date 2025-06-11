# setup_schema.py
from neo4j import GraphDatabase
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KGSetup:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
        
    def create_constraints(self):
        with self.driver.session() as session:
            # 创建唯一性约束
            constraints = [
                # 实体约束
                """CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person)
                   REQUIRE p.id IS UNIQUE""",
                """CREATE CONSTRAINT IF NOT EXISTS FOR (t:Topic)
                   REQUIRE t.id IS UNIQUE""",
                """CREATE CONSTRAINT IF NOT EXISTS FOR (c:Conversation)
                   REQUIRE c.id IS UNIQUE""",
                """CREATE CONSTRAINT IF NOT EXISTS FOR (q:Question)
                   REQUIRE q.id IS UNIQUE""",
                """CREATE CONSTRAINT IF NOT EXISTS FOR (a:Answer)
                   REQUIRE a.id IS UNIQUE"""
            ]
            
            for constraint in constraints:
                try:
                    session.run(constraint)
                    logger.info(f"Created constraint: {constraint}")
                except Exception as e:
                    logger.error(f"Failed to create constraint: {str(e)}")

    def create_test_data(self):
        with self.driver.session() as session:
            # 创建测试数据
            session.run("""
                // 创建用户
                CREATE (u1:Person {id: 'user1', name: '用户1'})
                CREATE (u2:Person {id: 'user2', name: '用户2'})
                
                // 创建话题
                CREATE (t1:Topic {id: 'topic1', name: 'Python编程'})
                CREATE (t2:Topic {id: 'topic2', name: '机器学习'})
                
                // 创建对话
                CREATE (c1:Conversation {
                    id: 'conv1',
                    timestamp: datetime(),
                    content: '关于Python的讨论'
                })
                
                // 创建问答
                CREATE (q1:Question {
                    id: 'q1',
                    content: 'Python如何处理异步操作？'
                })
                CREATE (a1:Answer {
                    id: 'a1',
                    content: '可以使用async/await关键字...'
                })
                
                // 创建关系
                CREATE (u1)-[:ASKED]->(q1)
                CREATE (q1)-[:BELONGS_TO]->(t1)
                CREATE (u2)-[:ANSWERED]->(a1)
                CREATE (q1)-[:HAS_ANSWER]->(a1)
                CREATE (u1)-[:PARTICIPATED_IN]->(c1)
                CREATE (c1)-[:DISCUSSED]->(t1)
            """)
            logger.info("Created test data successfully")

def main():
    # 替换为你的Neo4j Desktop连接信息
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "admin@123"  # 替换为你设置的密码
    
    kg_setup = KGSetup(uri, user, password)
    
    try:
        # 创建约束
        kg_setup.create_constraints()
        
        # 创建测试数据
        kg_setup.create_test_data()
        
        logger.info("Schema setup completed successfully")
        
    finally:
        kg_setup.close()

if __name__ == "__main__":
    main()