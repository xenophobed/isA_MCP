from typing import Dict, Any
from .base import BaseQuery, QueryType

class ContextExpansionQueries:
    """Collection of context expansion queries for Neo4j"""

    FIND_SIMILAR_CONVERSATIONS = BaseQuery(
        name="find_similar_conversations",
        query="""
        MATCH (c:Conversation)-[:HAS_ATOMIC_FACT]->(af:AtomicFact)-[:HAS_KEY_ELEMENT]->(ke:KeyElement)
        WHERE ke.content IN $core_elements
        
        WITH DISTINCT c, 
             collect(DISTINCT af) as atomic_facts,
             collect(DISTINCT ke.content) as matched_elements,
             count(DISTINCT ke) as matching_count
        
        WHERE matching_count >= 1
        
        RETURN {
            conversation_id: c.id,
            created_at: toString(c.created_at),
            facts: [fact IN atomic_facts | {
                content: fact.content,
                created_at: toString(fact.created_at),
                key_elements: [(fact)-[:HAS_KEY_ELEMENT]->(ke) | ke.content]
            }],
            relevance_score: matching_count,
            matched_elements: matched_elements
        } as result
        ORDER BY matching_count DESC
        LIMIT 5
        """,
        query_type=QueryType.READ,
        parameters={"core_elements": list},
        cacheable=True
    )

    FIND_KNOWLEDGE_COLLECTIONS = BaseQuery(
        name="find_knowledge_collections",
        query="""
        MATCH (ks:KnowledgeSource)-[:HAS_COLLECTION]->(col:Collection)
        WHERE ks.status = 'active'

        WITH ks, col
        OPTIONAL MATCH (col)-[:CONTAINS_ELEMENT]->(ke:KeyElement)
        WHERE ke.content IN $core_elements

        WITH ks, col, collect(DISTINCT ke.content) as matched_elements
        OPTIONAL MATCH (col)-[:HAS_EXAMPLE]->(eq:ExampleQuery)
        WHERE any(element IN $core_elements WHERE eq.content CONTAINS element)

        WITH ks, col, matched_elements,
            collect(DISTINCT eq.content) as matched_queries,
            size(matched_elements) + size(collect(DISTINCT eq)) as matching_count
        WHERE matching_count > 0

        RETURN {
            knowledge_source: {
                capability_id: ks.capability_id,
                name: ks.name,
                type: ks.type,
                description: ks.description,
                status: ks.status,
                last_updated: toString(ks.last_updated)
            },
            collection: {
                name: col.name,
                status: col.status
            },
            matched_elements: matched_elements,
            matched_queries: matched_queries,
            relevance_score: matching_count
        } as result
        ORDER BY matching_count DESC
        LIMIT 5
        """,
        query_type=QueryType.READ,
        parameters={"core_elements": list},
        cacheable=True
    )

    FIND_RELEVANT_TOOLS = BaseQuery(
        name="find_relevant_tools",
        query="""
        MATCH (t:Tool)
        WHERE t.status = 'active'
        
        OPTIONAL MATCH (t)-[:RELATES_TO]->(ke:KeyElement)
        WHERE ke.content IN $core_elements

        WITH t, 
            collect(DISTINCT ke.content) as matched_elements,
            size(collect(DISTINCT ke)) as matching_count
        WHERE matching_count > 0
        
        RETURN {
            capability_id: t.capability_id,
            name: t.name,
            type: t.type,
            description: t.description,
            status: t.status,
            last_updated: toString(t.last_updated),
            api_endpoint: t.api_endpoint,
            input_schema: t.input_schema,
            output_schema: t.output_schema,
            rate_limits: t.rate_limits,
            node_name: t.node_name,
            graph_source: t.graph_source,
            matched_elements: matched_elements,
            relevance_score: matching_count
        } as result
        ORDER BY matching_count DESC
        LIMIT 5
        """,
        query_type=QueryType.READ,
        parameters={"core_elements": list},
        cacheable=True
    )

    GET_DATABASE_CONTEXT = BaseQuery(
        name="get_database_context",
        query="""
        MATCH (db:Database)-[:CONTAINS]->(o:Order)
        WHERE o.order_no = $order_no
        OPTIONAL MATCH (c:Customer)-[:HAS_ORDER]->(o)
        OPTIONAL MATCH (o)-[:HAS_TRACKING]->(t:TrackingStatus)
        
        RETURN {
            customer: CASE WHEN c IS NOT NULL 
                THEN {
                    id: c.id,
                    code: c.code,
                    name: c.name
                }
                ELSE null 
            END,
            order: {
                order_no: o.order_no,
                status: o.status,
                receive_time: toString(o.receive_time),
                shipping_time: toString(o.shipping_time)
            },
            tracking: CASE WHEN t IS NOT NULL 
                THEN {
                    order_no: t.order_no,
                    status: t.status,
                    updated_at: toString(t.updated_at)
                }
                ELSE null 
            END
        } as result
        """,
        query_type=QueryType.READ,
        parameters={"order_no": str},
        cacheable=True
    )

    SYNC_KNOWLEDGE_SOURCE = BaseQuery(
        name="sync_knowledge_source",
        query="""
        MERGE (ks:KnowledgeSource {capability_id: $capability_id})
        SET ks.name = $name,
            ks.type = $type,
            ks.description = $description,
            ks.last_updated = $last_updated,
            ks.status = 'active'

        WITH ks

        // Create collection nodes with semantics
        UNWIND $collections as collection_data
        MERGE (col:Collection {name: collection_data.name})
        SET col.status = collection_data.info.status
        MERGE (ks)-[:HAS_COLLECTION]->(col)
        WITH col, collection_data

        // Create semantic relationships
        UNWIND collection_data.semantics.key_elements as element
        MERGE (ke:KeyElement {content: element})
        MERGE (col)-[:CONTAINS_ELEMENT]->(ke)

        WITH col, collection_data
        UNWIND collection_data.semantics.example_queries as query
        MERGE (eq:ExampleQuery {content: query})
        MERGE (col)-[:HAS_EXAMPLE]->(eq)
        """,
        query_type=QueryType.WRITE,
        parameters={
            "capability_id": str,
            "name": str,
            "type": str,
            "description": str,
            "last_updated": str,
            "collections": list
        }
    )

    SYNC_TOOL_CAPABILITY = BaseQuery(
        name="sync_tool_capability",
        query="""
        MERGE (t:Tool {capability_id: $capability_id})
        SET t.name = $name,
            t.type = $type,
            t.description = $description,
            t.last_updated = $last_updated,
            t.status = $status,
            t.api_endpoint = $api_endpoint,
            t.input_schema = $input_schema,
            t.output_schema = $output_schema,
            t.rate_limits = $rate_limits,
            t.node_name = $node_name,
            t.graph_source = $graph_source
        
        WITH t
        
        // Create or update key elements and relationships
        UNWIND $key_elements as element
        MERGE (ke:KeyElement {content: element})
        MERGE (t)-[:RELATES_TO]->(ke)
        """,
        query_type=QueryType.WRITE,
        parameters={
            "capability_id": str,
            "name": str,
            "type": str,
            "description": str,
            "last_updated": str,
            "status": str,
            "api_endpoint": str,
            "input_schema": str,
            "output_schema": str,
            "rate_limits": str,
            "node_name": str,
            "graph_source": str,
            "key_elements": list
        }
    )

    SYNC_DATABASE_CAPABILITY = BaseQuery(
        name="sync_database_capability",
        query="""
        MERGE (db:Database {capability_id: $capability_id})
        SET db.name = $name,
            db.type = $type,
            db.description = $description,
            db.last_updated = $last_updated,
            db.status = $status,
            db.database_type = $database_type

        WITH db

        // Process order data and create relationships
        UNWIND $order_data as order
        
        // Create or update Customer node
        MERGE (c:Customer {code: order.customer_code})
        ON CREATE SET c.name = order.customer_name
        ON MATCH SET c.name = order.customer_name
        
        // Create or update Order node
        MERGE (o:Order {order_no: order.order_no})
        ON CREATE SET 
            o.status = order.status,
            o.receive_time = CASE 
                WHEN order.receive_time IS NOT NULL 
                THEN datetime(replace(order.receive_time, ' ', 'T'))
                ELSE null 
            END,
            o.shipping_time = CASE 
                WHEN order.shipping_time IS NOT NULL 
                THEN datetime(replace(order.shipping_time, ' ', 'T'))
                ELSE null 
            END
        ON MATCH SET 
            o.status = order.status,
            o.receive_time = CASE 
                WHEN order.receive_time IS NOT NULL 
                THEN datetime(replace(order.receive_time, ' ', 'T'))
                ELSE o.receive_time 
            END,
            o.shipping_time = CASE 
                WHEN order.shipping_time IS NOT NULL 
                THEN datetime(replace(order.shipping_time, ' ', 'T'))
                ELSE o.shipping_time 
            END
        
        // Create or update Tracking node
        MERGE (track:TrackingStatus {
            order_no: order.order_no,
            status: order.tracking_status
        })
        ON CREATE SET 
            track.updated_at = CASE 
                WHEN order.tracking_time IS NOT NULL 
                THEN datetime(replace(order.tracking_time, ' ', 'T'))
                ELSE null 
            END
        ON MATCH SET 
            track.updated_at = CASE 
                WHEN order.tracking_time IS NOT NULL 
                THEN datetime(replace(order.tracking_time, ' ', 'T'))
                ELSE track.updated_at 
            END
        
        // Create relationships
        MERGE (c)-[:HAS_ORDER]->(o)
        MERGE (o)-[:HAS_TRACKING]->(track)
        MERGE (db)-[:CONTAINS]->(o)
        """,
        query_type=QueryType.WRITE,
        parameters={
            "capability_id": str,
            "name": str,
            "type": str,
            "description": str,
            "last_updated": str,
            "status": str,
            "database_type": str,
            "order_data": list
        }
    )

    @staticmethod
    def register_all(registry):
        """Register all queries"""
        # Register existing queries
        registry.register_query(ContextExpansionQueries.FIND_SIMILAR_CONVERSATIONS)
        registry.register_query(ContextExpansionQueries.FIND_KNOWLEDGE_COLLECTIONS)
        registry.register_query(ContextExpansionQueries.FIND_RELEVANT_TOOLS)
        registry.register_query(ContextExpansionQueries.GET_DATABASE_CONTEXT)
        
        # Register sync queries
        registry.register_query(ContextExpansionQueries.SYNC_KNOWLEDGE_SOURCE)
        registry.register_query(ContextExpansionQueries.SYNC_TOOL_CAPABILITY)
        registry.register_query(ContextExpansionQueries.SYNC_DATABASE_CAPABILITY)
