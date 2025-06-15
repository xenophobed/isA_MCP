# src/neo4j_updater.py
from neo4j import GraphDatabase
from typing import Dict, List

class Neo4jUpdater:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def update_collection_metadata(self, metadata: Dict):
        with self.driver.session() as session:
            session.execute_write(self._update_collection, metadata)

    def _update_collection(self, tx, metadata: Dict):
        # Create or update database node
        db_query = """
        MERGE (db:MongoDatabase {name: $db_name})
        SET db.updated_at = datetime()
        RETURN db
        """
        db = tx.run(db_query, db_name=metadata['database']).single()

        # Create or update collection node
        coll_query = """
        MERGE (col:MongoCollection {
            name: $name,
            database: $database
        })
        SET col.document_count = $document_count,
            col.avg_document_size = $avg_document_size,
            col.indexes = $indexes,
            col.updated_at = datetime()
        WITH col
        MATCH (db:MongoDatabase {name: $database})
        MERGE (db)-[:HAS_COLLECTION]->(col)
        RETURN col
        """
        collection = tx.run(coll_query, **metadata).single()

        # Update fields
        for field_name, field_info in metadata['fields'].items():
            field_query = """
            MERGE (f:Field {
                name: $field_name,
                collection: $collection_name,
                database: $database
            })
            SET f += $field_info,
                f.updated_at = datetime()
            WITH f
            MATCH (col:MongoCollection {
                name: $collection_name,
                database: $database
            })
            MERGE (col)-[:HAS_FIELD]->(f)
            """
            tx.run(field_query, 
                  field_name=field_name,
                  collection_name=metadata['name'],
                  database=metadata['database'],
                  field_info=field_info)