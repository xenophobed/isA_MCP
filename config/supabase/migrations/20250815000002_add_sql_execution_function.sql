-- Add SQL execution function for advanced vector search queries
-- Migration: 20250815000002_add_sql_execution_function

-- Create a secure function to execute dynamic SQL for vector search
-- This is needed for complex full-text search queries with ranking
CREATE OR REPLACE FUNCTION dev.execute_vector_search_sql(sql_query text)
RETURNS TABLE(
    id uuid,
    text text,
    metadata jsonb,
    created_at timestamptz,
    rank_score real,
    embedding_vector vector(1536),
    headline text
) 
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Basic SQL injection protection - only allow SELECT statements
    IF sql_query !~* '^SELECT' THEN
        RAISE EXCEPTION 'Only SELECT statements are allowed';
    END IF;
    
    -- Additional safety check - ensure it's querying user_knowledge table
    IF sql_query !~* 'user_knowledge' THEN
        RAISE EXCEPTION 'Query must be on user_knowledge table';
    END IF;
    
    -- Execute the dynamic SQL and return results
    RETURN QUERY EXECUTE sql_query;
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION dev.execute_vector_search_sql(text) TO authenticated;

-- Create a simplified version for basic text search
CREATE OR REPLACE FUNCTION dev.search_user_knowledge_text(
    p_user_id text,
    p_query text,
    p_limit integer DEFAULT 10
)
RETURNS TABLE(
    id uuid,
    text text,
    metadata jsonb,
    created_at timestamptz,
    rank_score real,
    headline text
) 
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    ts_query_text text;
BEGIN
    -- Prepare the text search query
    -- Clean the input query for tsquery
    ts_query_text := trim(regexp_replace(p_query, '[^a-zA-Z0-9\s]', ' ', 'g'));
    ts_query_text := regexp_replace(ts_query_text, '\s+', ' | ', 'g');
    
    -- Return search results with ranking
    RETURN QUERY
    SELECT 
        uk.id,
        uk.text,
        uk.metadata,
        uk.created_at,
        ts_rank(uk.text_search_vector, to_tsquery('english', ts_query_text))::real as rank_score,
        ts_headline('english', uk.text, to_tsquery('english', ts_query_text), 'MaxWords=30, MinWords=10') as headline
    FROM dev.user_knowledge uk
    WHERE uk.user_id = p_user_id 
        AND uk.text_search_vector @@ to_tsquery('english', ts_query_text)
    ORDER BY rank_score DESC
    LIMIT p_limit;
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION dev.search_user_knowledge_text(text, text, integer) TO authenticated;

-- Create function for vector similarity search using SQL
CREATE OR REPLACE FUNCTION dev.search_user_knowledge_vector(
    p_user_id text,
    p_embedding vector(1536),
    p_limit integer DEFAULT 10
)
RETURNS TABLE(
    id uuid,
    text text,
    metadata jsonb,
    created_at timestamptz,
    similarity_score real,
    embedding_vector vector(1536)
) 
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Return vector similarity search results
    RETURN QUERY
    SELECT 
        uk.id,
        uk.text,
        uk.metadata,
        uk.created_at,
        (1 - (uk.embedding_vector <=> p_embedding))::real as similarity_score,
        uk.embedding_vector
    FROM dev.user_knowledge uk
    WHERE uk.user_id = p_user_id 
        AND uk.embedding_vector IS NOT NULL
    ORDER BY uk.embedding_vector <=> p_embedding
    LIMIT p_limit;
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION dev.search_user_knowledge_vector(text, vector(1536), integer) TO authenticated;

-- Create hybrid search function that combines both approaches
CREATE OR REPLACE FUNCTION dev.search_user_knowledge_hybrid(
    p_user_id text,
    p_query text,
    p_embedding vector(1536),
    p_text_weight real DEFAULT 0.3,
    p_vector_weight real DEFAULT 0.7,
    p_limit integer DEFAULT 10
)
RETURNS TABLE(
    id uuid,
    text text,
    metadata jsonb,
    created_at timestamptz,
    text_score real,
    vector_score real,
    combined_score real,
    headline text,
    embedding_vector vector(1536)
) 
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    ts_query_text text;
BEGIN
    -- Prepare the text search query
    ts_query_text := trim(regexp_replace(p_query, '[^a-zA-Z0-9\s]', ' ', 'g'));
    ts_query_text := regexp_replace(ts_query_text, '\s+', ' | ', 'g');
    
    -- Return hybrid search results
    RETURN QUERY
    WITH text_results AS (
        SELECT 
            uk.id,
            uk.text,
            uk.metadata,
            uk.created_at,
            ts_rank(uk.text_search_vector, to_tsquery('english', ts_query_text)) as text_rank,
            ts_headline('english', uk.text, to_tsquery('english', ts_query_text), 'MaxWords=30, MinWords=10') as headline,
            uk.embedding_vector
        FROM dev.user_knowledge uk
        WHERE uk.user_id = p_user_id 
            AND uk.text_search_vector @@ to_tsquery('english', ts_query_text)
    ),
    vector_results AS (
        SELECT 
            uk.id,
            uk.text,
            uk.metadata,
            uk.created_at,
            (1 - (uk.embedding_vector <=> p_embedding)) as vector_sim,
            uk.embedding_vector
        FROM dev.user_knowledge uk
        WHERE uk.user_id = p_user_id 
            AND uk.embedding_vector IS NOT NULL
    ),
    combined_results AS (
        SELECT 
            COALESCE(tr.id, vr.id) as id,
            COALESCE(tr.text, vr.text) as text,
            COALESCE(tr.metadata, vr.metadata) as metadata,
            COALESCE(tr.created_at, vr.created_at) as created_at,
            COALESCE(tr.text_rank, 0)::real as text_score,
            COALESCE(vr.vector_sim, 0)::real as vector_score,
            (COALESCE(tr.text_rank, 0) * p_text_weight + COALESCE(vr.vector_sim, 0) * p_vector_weight)::real as combined_score,
            tr.headline,
            COALESCE(tr.embedding_vector, vr.embedding_vector) as embedding_vector
        FROM text_results tr
        FULL OUTER JOIN vector_results vr ON tr.id = vr.id
    )
    SELECT 
        cr.id,
        cr.text,
        cr.metadata,
        cr.created_at,
        cr.text_score,
        cr.vector_score,
        cr.combined_score,
        cr.headline,
        cr.embedding_vector
    FROM combined_results cr
    WHERE cr.combined_score > 0
    ORDER BY cr.combined_score DESC
    LIMIT p_limit;
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION dev.search_user_knowledge_hybrid(text, text, vector(1536), real, real, integer) TO authenticated;

-- Add comments for documentation
COMMENT ON FUNCTION dev.execute_vector_search_sql(text) IS 'Execute dynamic SQL for advanced vector search queries with security checks';
COMMENT ON FUNCTION dev.search_user_knowledge_text(text, text, integer) IS 'Full-text search on user knowledge with PostgreSQL tsvector/tsquery';
COMMENT ON FUNCTION dev.search_user_knowledge_vector(text, vector(1536), integer) IS 'Vector similarity search on user knowledge using cosine distance';
COMMENT ON FUNCTION dev.search_user_knowledge_hybrid(text, text, vector(1536), real, real, integer) IS 'Hybrid search combining full-text and vector similarity with weighted scoring';