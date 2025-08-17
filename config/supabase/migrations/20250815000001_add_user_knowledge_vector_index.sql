-- Add vector index and full-text search support to user_knowledge table
-- Migration: 20250815000001_add_user_knowledge_vector_index

-- Step 1: Add vector index for embedding similarity search
-- Using IVFFLAT with cosine distance for text-embedding-3-small (1536 dimensions)
CREATE INDEX IF NOT EXISTS idx_user_knowledge_embedding_vector 
ON dev.user_knowledge 
USING ivfflat (embedding_vector vector_cosine_ops) 
WITH (lists = 100);

-- Step 2: Add full-text search vector column for BM25 search
ALTER TABLE dev.user_knowledge 
ADD COLUMN IF NOT EXISTS text_search_vector tsvector;

-- Step 3: Create GIN index for full-text search
CREATE INDEX IF NOT EXISTS idx_user_knowledge_text_search 
ON dev.user_knowledge 
USING gin(text_search_vector);

-- Step 4: Create function to update text search vector
CREATE OR REPLACE FUNCTION dev.update_user_knowledge_text_search()
RETURNS TRIGGER AS $$
BEGIN
    -- Generate tsvector from text content with custom configuration
    NEW.text_search_vector := to_tsvector('english', COALESCE(NEW.text, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Step 5: Create trigger to automatically update text search vector
DROP TRIGGER IF EXISTS trigger_update_user_knowledge_text_search ON dev.user_knowledge;
CREATE TRIGGER trigger_update_user_knowledge_text_search
    BEFORE INSERT OR UPDATE OF text
    ON dev.user_knowledge
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_user_knowledge_text_search();

-- Step 6: Populate existing records with text search vectors
UPDATE dev.user_knowledge 
SET text_search_vector = to_tsvector('english', COALESCE(text, ''))
WHERE text_search_vector IS NULL;

-- Step 7: Add composite index for user filtering with vector search
CREATE INDEX IF NOT EXISTS idx_user_knowledge_user_id_embedding 
ON dev.user_knowledge (user_id, embedding_vector);

-- Step 8: Add composite index for user filtering with text search
CREATE INDEX IF NOT EXISTS idx_user_knowledge_user_id_text_search 
ON dev.user_knowledge (user_id, text_search_vector);

-- Step 9: Add metadata filtering index for advanced search
CREATE INDEX IF NOT EXISTS idx_user_knowledge_user_metadata_gin 
ON dev.user_knowledge 
USING gin (user_id, metadata);

-- Step 10: Add timestamp index for incremental updates
CREATE INDEX IF NOT EXISTS idx_user_knowledge_updated_at_user 
ON dev.user_knowledge (updated_at DESC, user_id);

-- Analyze table to update statistics for query planner
ANALYZE dev.user_knowledge;

-- Add comment for documentation
COMMENT ON INDEX dev.idx_user_knowledge_embedding_vector IS 'IVFFLAT index for vector similarity search using cosine distance';
COMMENT ON INDEX dev.idx_user_knowledge_text_search IS 'GIN index for full-text search using tsvector';
COMMENT ON COLUMN dev.user_knowledge.text_search_vector IS 'Preprocessed text search vector for BM25 ranking';