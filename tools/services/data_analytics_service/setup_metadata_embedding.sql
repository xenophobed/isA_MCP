-- Data Analytics Metadata Embedding Setup Script
-- Run this in your PostgreSQL/Supabase SQL Editor to set up metadata embeddings with pgvector

-- Enable the pgvector extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create metadata embeddings table for data analytics
CREATE TABLE IF NOT EXISTS db_metadata_embedding (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL, -- 'table', 'column', 'relationship', 'business_rule', 'semantic_tag'
    entity_name TEXT NOT NULL,
    entity_full_name TEXT NOT NULL, -- e.g., 'table:companies' or 'column:companies.company_code'
    content TEXT NOT NULL, -- The text content that was embedded
    embedding vector(1536), -- OpenAI text-embedding-3-small dimension
    metadata JSONB DEFAULT '{}', -- Additional metadata (confidence, source table info, etc.)
    semantic_tags TEXT[] DEFAULT '{}', -- Array of semantic tags
    confidence_score FLOAT DEFAULT 0.0, -- Confidence score from semantic analysis
    source_step INTEGER DEFAULT 2, -- Which analysis step generated this (2=semantic enricher, 3=embedding storage)
    database_source TEXT DEFAULT '', -- Source database/schema name
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS db_metadata_embedding_entity_type_idx ON db_metadata_embedding(entity_type);
CREATE INDEX IF NOT EXISTS db_metadata_embedding_entity_name_idx ON db_metadata_embedding(entity_name);
CREATE INDEX IF NOT EXISTS db_metadata_embedding_created_at_idx ON db_metadata_embedding(created_at);
CREATE INDEX IF NOT EXISTS db_metadata_embedding_source_idx ON db_metadata_embedding(database_source);
CREATE INDEX IF NOT EXISTS db_metadata_embedding_confidence_idx ON db_metadata_embedding(confidence_score);

-- Create vector similarity index (using cosine distance)
CREATE INDEX IF NOT EXISTS db_metadata_embedding_vector_idx ON db_metadata_embedding 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create function for metadata similarity search
CREATE OR REPLACE FUNCTION match_metadata_embeddings(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.0,
    match_count int DEFAULT 10,
    entity_type_filter text DEFAULT NULL,
    database_filter text DEFAULT NULL,
    min_confidence float DEFAULT 0.0
)
RETURNS TABLE (
    id text,
    entity_type text,
    entity_name text,
    entity_full_name text,
    content text,
    metadata jsonb,
    semantic_tags text[],
    confidence_score float,
    database_source text,
    created_at timestamptz,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.entity_type,
        e.entity_name,
        e.entity_full_name,
        e.content,
        e.metadata,
        e.semantic_tags,
        e.confidence_score,
        e.database_source,
        e.created_at,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM db_metadata_embedding e
    WHERE 
        (entity_type_filter IS NULL OR e.entity_type = entity_type_filter)
        AND (database_filter IS NULL OR e.database_source = database_filter)
        AND e.confidence_score >= min_confidence
        AND 1 - (e.embedding <=> query_embedding) > match_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Create function for finding similar entities by name/type
CREATE OR REPLACE FUNCTION find_similar_entities(
    entity_name_pattern text,
    entity_type_filter text DEFAULT NULL,
    similarity_threshold float DEFAULT 0.7,
    result_limit int DEFAULT 5
)
RETURNS TABLE (
    id text,
    entity_type text,
    entity_name text,
    content text,
    confidence_score float,
    semantic_tags text[]
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.entity_type,
        e.entity_name,
        e.content,
        e.confidence_score,
        e.semantic_tags
    FROM db_metadata_embedding e
    WHERE 
        (entity_type_filter IS NULL OR e.entity_type = entity_type_filter)
        AND (
            SIMILARITY(e.entity_name, entity_name_pattern) > similarity_threshold
            OR e.entity_name ILIKE '%' || entity_name_pattern || '%'
        )
    ORDER BY SIMILARITY(e.entity_name, entity_name_pattern) DESC
    LIMIT result_limit;
END;
$$;

-- Create function to get metadata statistics by entity type
CREATE OR REPLACE FUNCTION get_metadata_stats(database_name text DEFAULT NULL)
RETURNS TABLE (
    entity_type text,
    total_entities bigint,
    avg_confidence float,
    total_semantic_tags bigint
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.entity_type,
        COUNT(*) as total_entities,
        AVG(e.confidence_score) as avg_confidence,
        SUM(array_length(e.semantic_tags, 1)) as total_semantic_tags
    FROM db_metadata_embedding e
    WHERE (database_name IS NULL OR e.database_source = database_name)
    GROUP BY e.entity_type
    ORDER BY total_entities DESC;
END;
$$;

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_metadata_embedding_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for updating updated_at timestamp
DROP TRIGGER IF EXISTS update_db_metadata_embedding_updated_at ON db_metadata_embedding;
CREATE TRIGGER update_db_metadata_embedding_updated_at
    BEFORE UPDATE ON db_metadata_embedding
    FOR EACH ROW
    EXECUTE FUNCTION update_metadata_embedding_updated_at();

-- Create function to cleanup old embeddings
CREATE OR REPLACE FUNCTION cleanup_old_metadata_embeddings(
    days_old integer DEFAULT 30,
    database_name text DEFAULT NULL
)
RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE
    deleted_count integer;
BEGIN
    DELETE FROM db_metadata_embedding 
    WHERE created_at < NOW() - INTERVAL '1 day' * days_old
    AND (database_name IS NULL OR database_source = database_name);
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$;

-- Enable Row Level Security (optional, for multi-tenant usage)
-- ALTER TABLE db_metadata_embedding ENABLE ROW LEVEL SECURITY;

-- Example policy (uncomment if you want to enable RLS)
-- CREATE POLICY "Users can view their own metadata" ON db_metadata_embedding
--     FOR SELECT USING (auth.uid()::text = metadata->>'user_id');

-- Insert some sample metadata embeddings for testing
INSERT INTO db_metadata_embedding (
    id, entity_type, entity_name, entity_full_name, content, 
    metadata, semantic_tags, confidence_score, database_source
) VALUES 
    (
        'test-table-companies', 
        'table', 
        'companies', 
        'table:companies',
        'Table: companies, Type: entity, Importance: medium, Records: 1000, Key attributes: company_code, company_name',
        '{"record_count": 1000, "business_importance": "medium"}',
        ARRAY['domain:customer', 'semantic:entity'],
        0.85,
        'customs_trade_db'
    ),
    (
        'test-column-company-code',
        'column',
        'company_code',
        'column:companies.company_code',
        'Column: companies.company_code - varchar, Business identifier for company entity',
        '{"table_name": "companies", "data_type": "varchar", "is_nullable": false}',
        ARRAY['semantic:identifier', 'business:identifier'],
        0.90,
        'customs_trade_db'
    ),
    (
        'test-rule-foreign-key',
        'business_rule',
        'fk_declarations_company',
        'rule:fk_declarations_company',
        'Foreign key relationship: declarations.company_code must reference valid companies.company_code',
        '{"rule_type": "referential_integrity", "tables_involved": ["declarations", "companies"]}',
        ARRAY['constraint:foreign_key', 'integrity:referential'],
        0.95,
        'customs_trade_db'
    )
ON CONFLICT (id) DO NOTHING;

-- Grant necessary permissions (adjust based on your setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON db_metadata_embedding TO authenticated;
-- GRANT EXECUTE ON FUNCTION match_metadata_embeddings TO authenticated;
-- GRANT EXECUTE ON FUNCTION find_similar_entities TO authenticated;
-- GRANT EXECUTE ON FUNCTION get_metadata_stats TO authenticated;

-- Display setup completion message
DO $$
BEGIN
    RAISE NOTICE 'Data Analytics Metadata Embedding setup completed successfully!';
    RAISE NOTICE 'Table created: db_metadata_embedding';
    RAISE NOTICE 'Functions created: match_metadata_embeddings, find_similar_entities, get_metadata_stats';
    RAISE NOTICE 'Indexes created for optimal vector search performance';
    RAISE NOTICE 'Sample metadata embeddings inserted for testing';
    RAISE NOTICE 'Ready to store semantic metadata with vector embeddings!';
END $$;