-- Supabase RAG Setup Script
-- Run this in your Supabase SQL Editor to set up RAG with pgvector

-- Enable the pgvector extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create RAG documents table
CREATE TABLE IF NOT EXISTS rag_documents (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(1536), -- OpenAI text-embedding-3-small dimension
    collection_name TEXT NOT NULL DEFAULT 'default',
    metadata JSONB DEFAULT '{}',
    source TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS rag_documents_collection_idx ON rag_documents(collection_name);
CREATE INDEX IF NOT EXISTS rag_documents_created_at_idx ON rag_documents(created_at);
CREATE INDEX IF NOT EXISTS rag_documents_source_idx ON rag_documents(source);

-- Create vector similarity index (using cosine distance)
CREATE INDEX IF NOT EXISTS rag_documents_embedding_idx ON rag_documents 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create function for document similarity search
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.0,
    match_count int DEFAULT 5,
    collection_filter text DEFAULT NULL
)
RETURNS TABLE (
    id text,
    content text,
    metadata jsonb,
    source text,
    collection_name text,
    created_at timestamptz,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.content,
        d.metadata,
        d.source,
        d.collection_name,
        d.created_at,
        1 - (d.embedding <=> query_embedding) AS similarity
    FROM rag_documents d
    WHERE 
        (collection_filter IS NULL OR d.collection_name = collection_filter)
        AND 1 - (d.embedding <=> query_embedding) > match_threshold
    ORDER BY d.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Create function to get collection statistics
CREATE OR REPLACE FUNCTION get_collection_stats(collection_name text)
RETURNS TABLE (
    total_documents bigint,
    total_characters bigint,
    average_length float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*) as total_documents,
        SUM(LENGTH(content)) as total_characters,
        AVG(LENGTH(content)) as average_length
    FROM rag_documents 
    WHERE rag_documents.collection_name = get_collection_stats.collection_name;
END;
$$;

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for updating updated_at timestamp
DROP TRIGGER IF EXISTS update_rag_documents_updated_at ON rag_documents;
CREATE TRIGGER update_rag_documents_updated_at
    BEFORE UPDATE ON rag_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (optional, for multi-tenant usage)
-- ALTER TABLE rag_documents ENABLE ROW LEVEL SECURITY;

-- Example policy (uncomment if you want to enable RLS)
-- CREATE POLICY "Users can view their own documents" ON rag_documents
--     FOR SELECT USING (auth.uid()::text = metadata->>'user_id');

-- Insert some sample documents for testing
INSERT INTO rag_documents (id, content, collection_name, metadata, source) 
VALUES 
    ('sample-1', 'This is a sample document about machine learning and artificial intelligence.', 'samples', '{"topic": "AI", "author": "system"}', 'system'),
    ('sample-2', 'Natural language processing is a subfield of AI that focuses on language understanding.', 'samples', '{"topic": "NLP", "author": "system"}', 'system'),
    ('sample-3', 'Vector databases enable semantic search by storing high-dimensional embeddings.', 'samples', '{"topic": "databases", "author": "system"}', 'system')
ON CONFLICT (id) DO NOTHING;

-- Grant necessary permissions (adjust based on your setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON rag_documents TO authenticated;
-- GRANT EXECUTE ON FUNCTION match_documents TO authenticated;
-- GRANT EXECUTE ON FUNCTION get_collection_stats TO authenticated;

-- Display setup completion message
DO $$
BEGIN
    RAISE NOTICE 'RAG setup completed successfully!';
    RAISE NOTICE 'Tables created: rag_documents';
    RAISE NOTICE 'Functions created: match_documents, get_collection_stats';
    RAISE NOTICE 'Indexes created for optimal vector search performance';
    RAISE NOTICE 'Sample documents inserted for testing';
END $$;