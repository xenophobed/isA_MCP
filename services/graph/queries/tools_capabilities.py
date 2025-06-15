from .base import BaseQuery, QueryType

class ToolCapabilitiesQueries:
    """Collection of tool capabilities-related queries"""

    CREATE_TOOL_CAPABILITY = BaseQuery(
        name="create_tool_capability",
        query="""
        // Create Tool node
        CREATE (t:Tool {
            id: $tool_id,
            name: $name,
            description: $description,
            hash: $hash
        })
        
        // Create Vector nodes with semantic properties
        CREATE (sv:SemanticVector {
            core_concept: $semantic_core_concept,
            domain: $semantic_domain,
            service_type: $semantic_service_type,
            vector: $semantic_vector
        })
        
        // Create Vector nodes with functional properties
        CREATE (fv:FunctionalVector {
            operation: $functional_operation,
            vector: $functional_vector
        })
        
        // Create Vector nodes with contextual properties
        CREATE (cv:ContextualVector {
            usage_context: $contextual_usage_context,
            vector: $contextual_vector
        })
        
        // Create relationships
        CREATE (t)-[:HAS_SEMANTIC]->(sv)
        CREATE (t)-[:HAS_FUNCTIONAL]->(fv)
        CREATE (t)-[:HAS_CONTEXTUAL]->(cv)
        """,
        query_type=QueryType.WRITE,
        parameters={
            "tool_id": str,
            "name": str,
            "description": str,
            "hash": str,
            "semantic_core_concept": str,
            "semantic_domain": str,
            "semantic_service_type": str,
            "semantic_vector": list,
            "functional_operation": str,
            "functional_vector": list,
            "contextual_usage_context": str,
            "contextual_vector": list
        }
    )

    SEARCH_BY_VECTOR = BaseQuery(
        name="search_by_vector",
        query="""
        // Match tools and their vectors
        MATCH (t:Tool)-[:HAS_SEMANTIC]->(sv:SemanticVector)
        MATCH (t)-[:HAS_FUNCTIONAL]->(fv:FunctionalVector)
        MATCH (t)-[:HAS_CONTEXTUAL]->(cv:ContextualVector)
        
        // Calculate cosine similarity
        WITH t, sv, fv, cv,
        // Semantic similarity
        REDUCE(dot = 0.0, i IN RANGE(0, size($semantic_vector)-1) |
            dot + $semantic_vector[i] * sv.vector[i]
        ) / sqrt(
            REDUCE(norm1 = 0.0, i IN RANGE(0, size($semantic_vector)-1) |
                norm1 + $semantic_vector[i] * $semantic_vector[i]
            ) *
            REDUCE(norm2 = 0.0, i IN RANGE(0, size(sv.vector)-1) |
                norm2 + sv.vector[i] * sv.vector[i]
            )
        ) as semantic_score,
        
        // Functional similarity
        REDUCE(dot = 0.0, i IN RANGE(0, size($functional_vector)-1) |
            dot + $functional_vector[i] * fv.vector[i]
        ) / sqrt(
            REDUCE(norm1 = 0.0, i IN RANGE(0, size($functional_vector)-1) |
                norm1 + $functional_vector[i] * $functional_vector[i]
            ) *
            REDUCE(norm2 = 0.0, i IN RANGE(0, size(fv.vector)-1) |
                norm2 + fv.vector[i] * fv.vector[i]
            )
        ) as functional_score,
        
        // Contextual similarity
        REDUCE(dot = 0.0, i IN RANGE(0, size($contextual_vector)-1) |
            dot + $contextual_vector[i] * cv.vector[i]
        ) / sqrt(
            REDUCE(norm1 = 0.0, i IN RANGE(0, size($contextual_vector)-1) |
                norm1 + $contextual_vector[i] * $contextual_vector[i]
            ) *
            REDUCE(norm2 = 0.0, i IN RANGE(0, size(cv.vector)-1) |
                norm2 + cv.vector[i] * cv.vector[i]
            )
        ) as contextual_score
        
        // Calculate weighted score
        WITH t, sv, fv, cv,
             toFloat($weights.semantic) * semantic_score +
             toFloat($weights.functional) * functional_score +
             toFloat($weights.contextual) * contextual_score as total_score
        
        // Filter and return results
        WHERE total_score >= $threshold
        RETURN t.id as tool_id,
               t.name as name,
               t.description as description,
               sv.core_concept as concept,
               sv.domain as domain,
               fv.operation as operation,
               cv.usage_context as usage_context,
               total_score as score
        ORDER BY score DESC
        LIMIT $limit
        """,
        query_type=QueryType.READ,
        parameters={
            "semantic_vector": list,
            "functional_vector": list,
            "contextual_vector": list,
            "weights": dict,
            "threshold": float,
            "limit": int
        }
    )

    SEARCH_BY_VECTOR_FALLBACK = BaseQuery(
        name="search_by_vector_fallback",
        query="""
        // Match tools and their vectors
        MATCH (t:Tool)-[:HAS_SEMANTIC]->(sv:SemanticVector)
        MATCH (t)-[:HAS_FUNCTIONAL]->(fv:FunctionalVector)
        MATCH (t)-[:HAS_CONTEXTUAL]->(cv:ContextualVector)
        
        // Calculate cosine similarity manually
        WITH t, sv, fv, cv,
        // Semantic similarity
        REDUCE(dot = 0.0, i IN RANGE(0, size($semantic_vector)-1) |
            dot + $semantic_vector[i] * sv.vector[i]
        ) / sqrt(
            REDUCE(norm1 = 0.0, i IN RANGE(0, size($semantic_vector)-1) |
                norm1 + $semantic_vector[i] * $semantic_vector[i]
            ) *
            REDUCE(norm2 = 0.0, i IN RANGE(0, size(sv.vector)-1) |
                norm2 + sv.vector[i] * sv.vector[i]
            )
        ) as semantic_score,
        
        // Functional similarity
        REDUCE(dot = 0.0, i IN RANGE(0, size($functional_vector)-1) |
            dot + $functional_vector[i] * fv.vector[i]
        ) / sqrt(
            REDUCE(norm1 = 0.0, i IN RANGE(0, size($functional_vector)-1) |
                norm1 + $functional_vector[i] * $functional_vector[i]
            ) *
            REDUCE(norm2 = 0.0, i IN RANGE(0, size(fv.vector)-1) |
                norm2 + fv.vector[i] * fv.vector[i]
            )
        ) as functional_score,
        
        // Contextual similarity
        REDUCE(dot = 0.0, i IN RANGE(0, size($contextual_vector)-1) |
            dot + $contextual_vector[i] * cv.vector[i]
        ) / sqrt(
            REDUCE(norm1 = 0.0, i IN RANGE(0, size($contextual_vector)-1) |
                norm1 + $contextual_vector[i] * $contextual_vector[i]
            ) *
            REDUCE(norm2 = 0.0, i IN RANGE(0, size(cv.vector)-1) |
                norm2 + cv.vector[i] * cv.vector[i]
            )
        ) as contextual_score
        
        // Calculate weighted score
        WITH t, sv, fv, cv,
             toFloat($weights.semantic) * semantic_score +
             toFloat($weights.functional) * functional_score +
             toFloat($weights.contextual) * contextual_score as total_score
        
        // Filter and return results
        WHERE total_score >= $threshold
        RETURN t.id as tool_id,
               t.name as name,
               t.description as description,
               sv.core_concept as concept,
               sv.domain as domain,
               fv.operation as operation,
               cv.usage_context as usage_context,
               total_score as score
        ORDER BY score DESC
        LIMIT $limit
        """,
        query_type=QueryType.READ,
        parameters={
            "semantic_vector": list,
            "functional_vector": list,
            "contextual_vector": list,
            "weights": dict,
            "threshold": float,
            "limit": int
        }
    )

    SEARCH_BY_TEXT = BaseQuery(
        name="search_by_text",
        query="""
        MATCH (t:Tool)
        WHERE t.name CONTAINS $query OR 
              t.description CONTAINS $query
        RETURN t.id as tool_id,
               t.name as name,
               t.description as description
        LIMIT $limit
        """,
        query_type=QueryType.READ,
        parameters={
            "query": str,
            "limit": int
        }
    )