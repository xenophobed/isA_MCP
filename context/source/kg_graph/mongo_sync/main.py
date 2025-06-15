# main.py
import logging
from concurrent.futures import ThreadPoolExecutor
import threading
import time
from app.core.config import Settings
from src.schema_extractor import SchemaExtractor
from src.neo4j_updator import Neo4jUpdater
from src.mongo_watcher import MongoWatcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SchemaSync:
    def __init__(self):
        self.schema_extractor = SchemaExtractor(
            self.Settings.MONGODB_URI,
            self.Settings.MONGODB_SAMPLE_SIZE
        )
        self.neo4j_updater = Neo4jUpdater(
            self.Settings.NEO4J_URI,
            self.Settings.NEO4J_USER,
            self.Settings.NEO4J_PASSWORD
        )
        
    def sync_collection(self, db_name: str, collection_name: str):
        """Sync a single collection's metadata to Neo4j."""
        try:
            metadata = self.schema_extractor.analyze_collection(
                db_name,
                collection_name
            )
            self.neo4j_updater.update_collection_metadata(metadata)
            logger.info(f"Synced {db_name}.{collection_name}")
        except Exception as e:
            logger.error(f"Error syncing {db_name}.{collection_name}: {e}")

    def sync_all(self):
        """Sync all configured collections."""
        db_name = Settings.MONGODB_DB_NAME
        for collection_name in Settings.MONGODB_COLLECTIONS:
            self.sync_collection(db_name, collection_name)

    def start_watchers(self):
        """Start change stream watchers for all collections."""
        with ThreadPoolExecutor() as executor:
            db_name = Settings.MONGODB_DB_NAME
            for collection_name in Settings.MONGODB_COLLECTIONS:
                watcher = MongoWatcher(
                    self.Settings.MONGODB_URI,
                    self.sync_collection
                )
                executor.submit(
                    watcher.watch_collection,
                        db_name,
                        collection_name
                    )

    def run(self):
        """Main run loop."""
        logger.info("Starting MongoDB to Neo4j schema sync")
        
        # Initial sync
        self.sync_all()
        
        self.start_watchers()
        
        # Periodic full sync
        while True:
            time.sleep(self.config.sync_interval)
            self.sync_all()

if __name__ == "__main__":
    sync = SchemaSync()
    sync.run()