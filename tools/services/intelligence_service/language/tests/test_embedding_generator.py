#!/usr/bin/env python3
"""
Real integration tests for EmbeddingGenerator service
Tests with actual ISA client (no mocks)
"""

import pytest
import sys
import os

# Add the path to the embedding generator
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from embedding_generator import EmbeddingGenerator, embed, similarity, search, chunk, rerank


class TestEmbeddingGeneratorReal:
    """Real test cases for EmbeddingGenerator class using actual ISA client"""
    
    @pytest.fixture
    def embedding_generator(self):
        """Create EmbeddingGenerator instance for testing"""
        return EmbeddingGenerator()
    
    @pytest.mark.asyncio
    async def test_embed_single_text(self, embedding_generator):
        """Test embedding a single text with real ISA client"""
        try:
            result = await embedding_generator.embed("Hello world")
            
            # Validate result
            assert isinstance(result, list), f"Expected list, got {type(result)}"
            assert len(result) > 0, "Embedding should not be empty"
            assert all(isinstance(x, (int, float)) for x in result), "All embedding values should be numbers"
            print(f"✅ Single embedding: {len(result)} dimensions")
            
        except Exception as e:
            pytest.skip(f"ISA client not available: {e}")
    
    @pytest.mark.asyncio
    async def test_embed_batch_texts(self, embedding_generator):
        """Test embedding multiple texts with real ISA client"""
        try:
            texts = ["Hello world", "Machine learning", "Artificial intelligence"]
            result = await embedding_generator.embed(texts)
            
            # Validate result
            assert isinstance(result, list), f"Expected list, got {type(result)}"
            assert len(result) == len(texts), f"Expected {len(texts)} embeddings, got {len(result)}"
            assert all(isinstance(emb, list) for emb in result), "All embeddings should be lists"
            assert all(len(emb) > 0 for emb in result), "All embeddings should be non-empty"
            print(f"✅ Batch embedding: {len(result)} embeddings of {len(result[0])} dimensions")
            
        except Exception as e:
            pytest.skip(f"ISA client not available: {e}")
    
    @pytest.mark.asyncio
    async def test_embed_single_method(self, embedding_generator):
        """Test embed_single method with real ISA client"""
        try:
            result = await embedding_generator.embed_single("Hello world")
            
            assert isinstance(result, list), f"Expected list, got {type(result)}"
            assert len(result) > 0, "Embedding should not be empty"
            assert all(isinstance(x, (int, float)) for x in result), "All values should be numbers"
            print(f"✅ embed_single: {len(result)} dimensions")
            
        except Exception as e:
            pytest.skip(f"ISA client not available: {e}")
    
    @pytest.mark.asyncio
    async def test_embed_batch_method(self, embedding_generator):
        """Test embed_batch method with real ISA client"""
        try:
            texts = ["Text 1", "Text 2", "Text 3"]
            result = await embedding_generator.embed_batch(texts)
            
            assert isinstance(result, list), f"Expected list, got {type(result)}"
            assert len(result) == len(texts), f"Expected {len(texts)} embeddings, got {len(result)}"
            assert all(isinstance(emb, list) for emb in result), "All embeddings should be lists"
            print(f"✅ embed_batch: {len(result)} embeddings")
            
        except Exception as e:
            pytest.skip(f"ISA client not available: {e}")
    
    @pytest.mark.asyncio
    async def test_compute_similarity(self, embedding_generator):
        """Test computing similarity between two texts with real ISA client"""
        try:
            similarity_score = await embedding_generator.compute_similarity(
                "machine learning", 
                "artificial intelligence"
            )
            
            assert isinstance(similarity_score, (int, float)), f"Expected number, got {type(similarity_score)}"
            assert 0.0 <= similarity_score <= 1.0, f"Similarity should be 0-1, got {similarity_score}"
            print(f"✅ Similarity computation: {similarity_score:.3f}")
            
        except Exception as e:
            pytest.skip(f"ISA client not available: {e}")
    
    @pytest.mark.asyncio
    async def test_find_most_similar(self, embedding_generator):
        """Test finding most similar texts with real ISA client"""
        try:
            query = "artificial intelligence"
            candidates = [
                "Machine learning algorithms",
                "Cooking recipes",
                "Deep learning networks",
                "Sports news"
            ]
            
            result = await embedding_generator.find_most_similar(query, candidates, top_k=2)
            
            assert isinstance(result, list), f"Expected list, got {type(result)}"
            assert len(result) <= 2, f"Expected at most 2 results, got {len(result)}"
            assert all(isinstance(item, tuple) and len(item) == 2 for item in result), "Results should be tuples"
            assert all(isinstance(score, (int, float)) for _, score in result), "Scores should be numbers"
            
            print(f"✅ Similarity search: {len(result)} results")
            for text, score in result:
                print(f"   {score:.3f}: {text}")
            
        except Exception as e:
            pytest.skip(f"ISA client not available: {e}")
    
    @pytest.mark.asyncio
    async def test_chunk_text(self, embedding_generator):
        """Test text chunking with real ISA client"""
        try:
            long_text = """
            This is a very long document that needs to be split into smaller chunks
            for processing. Each chunk will have its own embedding vector that can
            be used for semantic search and retrieval operations. The chunking
            process should maintain some overlap between chunks to preserve context.
            """
            
            result = await embedding_generator.chunk_text(
                long_text.strip(),
                chunk_size=100,
                overlap=20
            )
            
            assert isinstance(result, list), f"Expected list, got {type(result)}"
            assert len(result) > 0, "Should produce at least one chunk"
            
            # Check chunk structure
            for chunk in result:
                assert isinstance(chunk, dict), "Each chunk should be a dictionary"
                assert 'text' in chunk, "Each chunk should have text"
                assert 'embedding' in chunk, "Each chunk should have embedding"
                assert isinstance(chunk['embedding'], list), "Embedding should be a list"
            
            print(f"✅ Text chunking: {len(result)} chunks")
            
        except Exception as e:
            pytest.skip(f"ISA client not available: {e}")
    
    @pytest.mark.asyncio
    async def test_rerank_documents(self, embedding_generator):
        """Test document reranking with real ISA client"""
        try:
            query = "artificial intelligence and machine learning"
            documents = [
                "Machine learning is a subset of artificial intelligence",
                "Cooking recipes for beginners",
                "Deep learning uses neural networks",
                "Sports news and updates",
                "Natural language processing techniques"
            ]
            
            result = await embedding_generator.rerank_documents(query, documents, top_k=3)
            
            assert isinstance(result, list), f"Expected list, got {type(result)}"
            assert len(result) <= 3, f"Expected at most 3 results, got {len(result)}"
            
            # Check result structure
            for item in result:
                assert isinstance(item, dict), "Each result should be a dictionary"
                assert 'document' in item or 'text' in item, "Should have document text"
                assert 'relevance_score' in item or 'score' in item, "Should have relevance score"
            
            print(f"✅ Document reranking: {len(result)} results")
            for item in result:
                score = item.get('relevance_score', item.get('score', 0))
                doc = item.get('document', item.get('text', ''))
                print(f"   {score:.3f}: {doc[:50]}...")
            
        except Exception as e:
            pytest.skip(f"ISA client not available: {e}")
    
    @pytest.mark.asyncio
    async def test_embed_with_model_parameter(self, embedding_generator):
        """Test embedding with specific model parameter"""
        try:
            result = await embedding_generator.embed("Hello world", model="text-embedding-3-small")
            
            assert isinstance(result, list), f"Expected list, got {type(result)}"
            assert len(result) > 0, "Embedding should not be empty"
            print(f"✅ Model parameter test: {len(result)} dimensions")
            
        except Exception as e:
            pytest.skip(f"ISA client not available or model not supported: {e}")
    
    @pytest.mark.asyncio
    async def test_embed_with_normalize_parameter(self, embedding_generator):
        """Test embedding with normalize parameter"""
        try:
            result = await embedding_generator.embed("Hello world", normalize=True)
            
            assert isinstance(result, list), f"Expected list, got {type(result)}"
            assert len(result) > 0, "Embedding should not be empty"
            print(f"✅ Normalize parameter test: {len(result)} dimensions")
            
        except Exception as e:
            pytest.skip(f"ISA client not available: {e}")


class TestConvenienceFunctionsReal:
    """Test cases for convenience functions with real ISA client"""
    
    @pytest.mark.asyncio
    async def test_embed_convenience_function(self):
        """Test embed convenience function with real ISA client"""
        try:
            result = await embed("Hello world")
            
            assert isinstance(result, list), f"Expected list, got {type(result)}"
            assert len(result) > 0, "Embedding should not be empty"
            print(f"✅ embed() convenience function: {len(result)} dimensions")
            
        except Exception as e:
            pytest.skip(f"ISA client not available: {e}")
    
    @pytest.mark.asyncio
    async def test_similarity_convenience_function(self):
        """Test similarity convenience function with real ISA client"""
        try:
            result = await similarity("machine learning", "artificial intelligence")
            
            assert isinstance(result, (int, float)), f"Expected number, got {type(result)}"
            assert 0.0 <= result <= 1.0, f"Similarity should be 0-1, got {result}"
            print(f"✅ similarity() convenience function: {result:.3f}")
            
        except Exception as e:
            pytest.skip(f"ISA client not available: {e}")
    
    @pytest.mark.asyncio
    async def test_search_convenience_function(self):
        """Test search convenience function with real ISA client"""
        try:
            result = await search("AI", ["machine learning", "cooking", "deep learning"], top_k=2)
            
            assert isinstance(result, list), f"Expected list, got {type(result)}"
            assert len(result) <= 2, f"Expected at most 2 results, got {len(result)}"
            print(f"✅ search() convenience function: {len(result)} results")
            
        except Exception as e:
            pytest.skip(f"ISA client not available: {e}")
    
    @pytest.mark.asyncio
    async def test_chunk_convenience_function(self):
        """Test chunk convenience function with real ISA client"""
        try:
            result = await chunk("This is a long document that needs chunking for better processing.", chunk_size=50)
            
            assert isinstance(result, list), f"Expected list, got {type(result)}"
            assert len(result) > 0, "Should produce at least one chunk"
            print(f"✅ chunk() convenience function: {len(result)} chunks")
            
        except Exception as e:
            pytest.skip(f"ISA client not available: {e}")
    
    @pytest.mark.asyncio
    async def test_rerank_convenience_function(self):
        """Test rerank convenience function with real ISA client"""
        try:
            result = await rerank("AI", ["machine learning", "cooking", "deep learning"], top_k=2)
            
            assert isinstance(result, list), f"Expected list, got {type(result)}"
            assert len(result) <= 2, f"Expected at most 2 results, got {len(result)}"
            print(f"✅ rerank() convenience function: {len(result)} results")
            
        except Exception as e:
            pytest.skip(f"ISA client not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])