import os
os.environ['ENV'] = 'local'

import asyncio
from datetime import datetime
from app.config.config_manager import config_manager
from app.capability.source.conv_extractor import ConversationExtractor
from app.capability.source.conv_embedder import ConversationEmbedder
from app.capability.registry.conv_graph_manager import ConversationGraphManager
from app.services.ai.models.ai_factory import AIFactory
import json

logger = config_manager.get_logger(__name__)

async def test_conversation_knowledge_flow():
    """Test the complete conversation knowledge flow"""
    extractor = None
    embedder = None
    graph_manager = None
    
    try:
        # Initialize components
        extractor = ConversationExtractor()
        embedder = ConversationEmbedder()
        graph_manager = ConversationGraphManager()
        
        await extractor.initialize()
        await embedder.initialize()
        await graph_manager.initialize()
        
        test_conv_id = 'conv_iphone_support_123'
        
        logger.info("\n" + "="*50)
        logger.info("Knowledge Graph Test Flow")
        logger.info("="*50)
        
        # Step 1: Extract facts
        logger.info("\n1. Fact Extraction")
        logger.info("-"*30)
        extraction_result = await extractor.extract_conversation(test_conv_id)
        
        if extraction_result and extraction_result.get("atomic_facts"):
            for fact in extraction_result["atomic_facts"]:
                logger.info("\nAtomic Fact:")
                logger.info(f"Content: {fact.atomic_fact}")
                logger.info(f"Entities: {', '.join(fact.entities)}")
                
        # Step 2: Generate embeddings
        logger.info("\n2. Vector Generation")
        logger.info("-"*30)
        conversation_vectors = await embedder.embed_conversation_facts(
            test_conv_id,
            extraction_result["atomic_facts"]
        )
        logger.info(f"Generated {len(conversation_vectors)} fact vectors")
        
        # Step 3: Sync to knowledge stores
        logger.info("\n3. Knowledge Store Sync")
        logger.info("-"*30)
        
        # 3.1 Get current store stats before sync
        neo4j_stats = await graph_manager.get_graph_stats()
        qdrant_stats = await graph_manager.get_vector_stats()
        
        logger.info("\nBefore Sync:")
        logger.info("Neo4j Graph:")
        logger.info(f"- Facts: {neo4j_stats['fact_count']}")
        logger.info(f"- Entities: {neo4j_stats['entity_count']}")
        logger.info(f"- Relationships: {neo4j_stats['relation_count']}")
        
        logger.info("\nQdrant Vector Store:")
        logger.info(f"- Collection: {qdrant_stats['collection_name']}")
        logger.info(f"- Points: {qdrant_stats['point_count']}")
        logger.info(f"- Vector Dimension: {qdrant_stats['dimension']}")
        logger.info(f"- Distance Function: {qdrant_stats['distance']}")
        
        # 3.2 Sync knowledge
        await graph_manager.sync_conversation_knowledge(
            test_conv_id,
            conversation_vectors
        )
        
        # 3.3 Get updated stats
        neo4j_stats = await graph_manager.get_graph_stats()
        qdrant_stats = await graph_manager.get_vector_stats()
        
        logger.info("\nAfter Sync:")
        logger.info("Neo4j Graph:")
        logger.info(f"- Facts: {neo4j_stats['fact_count']}")
        logger.info(f"- Entities: {neo4j_stats['entity_count']}")
        logger.info(f"- Relationships: {neo4j_stats['relation_count']}")
        
        logger.info("\nQdrant Vector Store:")
        logger.info(f"- Collection: {qdrant_stats['collection_name']}")
        logger.info(f"- Points: {qdrant_stats['point_count']}")
        logger.info(f"- Vector Dimension: {qdrant_stats['dimension']}")
        logger.info(f"- Distance Function: {qdrant_stats['distance']}")
        
        # Step 4: Test search capabilities
        logger.info("\n4. Search Capabilities Test")
        logger.info("-"*30)
        test_query = "iPhone 15 Pro的价格是多少？"
        logger.info(f"\nSearch Query: {test_query}")
        
        # Generate query vector
        query_vector = await graph_manager.embed_service.create_text_embedding(test_query)
        
        # Search similar facts
        search_results = await graph_manager.search_similar_facts(
            query_vector=query_vector,
            limit=3,
            min_similarity=0.7
        )
        
        # 4.1 Neo4j Graph Search Results
        logger.info("\nNeo4j Graph Search Results:")
        logger.info("-"*20)
        for idx, result in enumerate(search_results["neo4j_results"], 1):
            logger.info(f"\nResult #{idx}")
            logger.info(f"Vector Similarity: {result['score']:.4f}")
            logger.info(f"Confidence Score: {result['confidence']:.4f}")
            logger.info(f"Content: {result['content']}")
            logger.info(f"ID: {result['id']}")
            if result['entities']:
                logger.info(f"Related Entities: {', '.join(result['entities'])}")
            else:
                logger.info("Related Entities: None")
            
        # 4.2 Qdrant Vector Search Results
        logger.info("\nQdrant Vector Search Results:")
        logger.info("-"*20)
        for idx, result in enumerate(search_results["qdrant_results"], 1):
            logger.info(f"\nResult #{idx}")
            logger.info(f"Vector Similarity: {result['score']:.4f}")
            logger.info(f"Content: {result['content']}")
            logger.info(f"ID: {result['id']}")
            logger.info(f"Timestamp: {result['timestamp']}")
            if result['entities']:
                logger.info(f"Related Entities: {', '.join(result['entities'])}")
            else:
                logger.info("Related Entities: None")
        
        # Step 5: Graph Structure Analysis
        logger.info("\n5. Knowledge Graph Structure")
        logger.info("-"*30)
        
        # 5.1 Get all facts and their relationships
        graph_results = await graph_manager.neo4j_service.query(
            """
            MATCH (f:Fact)
            OPTIONAL MATCH (f)-[r:MENTIONS]->(e:Entity)
            RETURN f.content as fact, 
                   f.confidence as confidence,
                   collect(e.content) as entities,
                   count(r) as relation_count
            ORDER BY f.confidence DESC
            """,
            {}
        )
        
        logger.info("\nFact Nodes and Relationships:")
        for idx, record in enumerate(graph_results, 1):
            logger.info(f"\nFact #{idx}:")
            logger.info(f"Content: {record['fact']}")
            
            # 安全地处理confidence值
            confidence = record.get('confidence')
            if confidence is not None:
                logger.info(f"Confidence: {confidence:.4f}")
            else:
                logger.info("Confidence: N/A")
                
            logger.info(f"Entity Relations: {record['relation_count']}")
            
            # 处理实体列表
            entities = record.get('entities', [])
            if entities:
                logger.info(f"Connected Entities: {', '.join(entities)}")
            else:
                logger.info("Connected Entities: None")
                
            # 添加分隔线
            if idx < len(graph_results):
                logger.info("-" * 20)
            
    except Exception as e:
        logger.error(f"Error during test: {e}")
        raise
    finally:
        # Cleanup resources
        cleanup_errors = []
        
        if graph_manager:
            try:
                await graph_manager.cleanup()
            except Exception as e:
                cleanup_errors.append(f"Graph manager cleanup error: {str(e)}")
                
        if embedder:
            try:
                await embedder.cleanup()
            except Exception as e:
                cleanup_errors.append(f"Embedder cleanup error: {str(e)}")
                
        if extractor:
            try:
                await extractor.cleanup()
            except Exception as e:
                cleanup_errors.append(f"Extractor cleanup error: {str(e)}")
        
        try:
            await config_manager.cleanup()
        except Exception as e:
            cleanup_errors.append(f"Config manager cleanup error: {str(e)}")
            
        if cleanup_errors:
            logger.error("Multiple cleanup errors occurred:")
            for error in cleanup_errors:
                logger.error(f"- {error}")

if __name__ == "__main__":
    asyncio.run(test_conversation_knowledge_flow())
