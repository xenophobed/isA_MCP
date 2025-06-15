class DBCapabilitiesQueries:
    CREATE_TABLE_NODE = {
        "query": """
        MERGE (t:Table {table_id: $table_id})
        SET t = {
            table_id: $table_id,
            semantic_vector: $semantic_vector,
            functional_vector: $functional_vector,
            contextual_vector: $contextual_vector,
            metadata: $metadata
        }
        """
    }

    SEARCH_TABLE = {
        "query": """
        MATCH (t:Table)
        WHERE t.semantic_vector IS NOT NULL 
          AND t.functional_vector IS NOT NULL 
          AND t.contextual_vector IS NOT NULL
        WITH t,
        // Calculate semantic similarity
        CASE WHEN size(t.semantic_vector) > 0 THEN
            REDUCE(dot = 0.0, i IN RANGE(0, size($query_vector)-1) |
                dot + $query_vector[i] * t.semantic_vector[i]
            ) / sqrt(
                REDUCE(norm1 = 0.0, i IN RANGE(0, size($query_vector)-1) |
                    norm1 + $query_vector[i] * $query_vector[i]
                ) *
                REDUCE(norm2 = 0.0, i IN RANGE(0, size(t.semantic_vector)-1) |
                    norm2 + t.semantic_vector[i] * t.semantic_vector[i]
                )
            ) * $weights.semantic
        ELSE 0 END +
        CASE WHEN size(t.functional_vector) > 0 THEN
            REDUCE(dot = 0.0, i IN RANGE(0, size($query_vector)-1) |
                dot + $query_vector[i] * t.functional_vector[i]
            ) / sqrt(
                REDUCE(norm1 = 0.0, i IN RANGE(0, size($query_vector)-1) |
                    norm1 + $query_vector[i] * $query_vector[i]
                ) *
                REDUCE(norm2 = 0.0, i IN RANGE(0, size(t.functional_vector)-1) |
                    norm2 + t.functional_vector[i] * t.functional_vector[i]
                )
            ) * $weights.functional
        ELSE 0 END +
        CASE WHEN size(t.contextual_vector) > 0 THEN
            REDUCE(dot = 0.0, i IN RANGE(0, size($query_vector)-1) |
                dot + $query_vector[i] * t.contextual_vector[i]
            ) / sqrt(
                REDUCE(norm1 = 0.0, i IN RANGE(0, size($query_vector)-1) |
                    norm1 + $query_vector[i] * $query_vector[i]
                ) *
                REDUCE(norm2 = 0.0, i IN RANGE(0, size(t.contextual_vector)-1) |
                    norm2 + t.contextual_vector[i] * t.contextual_vector[i]
                )
            ) * $weights.contextual
        ELSE 0 END AS score
        WHERE score >= $threshold
        RETURN t.table_id AS table_id,
               t.metadata AS metadata,
               score
        ORDER BY score DESC
        LIMIT $limit
        """
    }
