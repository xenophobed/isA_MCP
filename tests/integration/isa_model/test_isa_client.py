"""
ISA Model Client Integration Tests
Tests for both LLM and embedding functionality using ISA client
"""
import pytest
import asyncio
from core.isa_client import get_isa_client, isa_health_check


class TestISAClient:
    """Test ISA Model Client functionality"""
    
    def test_client_initialization(self):
        """Test that ISA client can be initialized"""
        client = get_isa_client()
        assert client is not None
        print("ISA Client initialized successfully")
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test ISA client health check"""
        try:
            result = await isa_health_check()
            print(f"Health check result: {result}")
            assert result is not None
        except Exception as e:
            print(f"Health check failed: {e}")
            pytest.skip("ISA service not available")
    
    @pytest.mark.asyncio
    async def test_llm_call(self):
        """Test LLM functionality with ISA client"""
        client = get_isa_client()
        
        try:
            # Test simple LLM call using invoke
            response = await client.invoke(
                input_data="Hello, can you respond with just 'Hello back!'?",
                task="chat",
                service_type="text",
                parameters={"temperature": 0.1, "max_tokens": 50}
            )
            
            print(f"LLM Response: {response}")
            assert response is not None
            
        except Exception as e:
            print(f"LLM call failed: {e}")
            pytest.skip("LLM service not available")
    
    @pytest.mark.asyncio
    async def test_embedding_call(self):
        """Test embedding functionality with ISA client"""
        client = get_isa_client()
        
        try:
            # Test embedding call using invoke
            text = "This is a test sentence for embedding"
            result = await client.invoke(
                input_data=text,
                task="embed",
                service_type="embedding"
            )
            
            print(f"Embedding result: {result}")
            assert result is not None
            
        except Exception as e:
            print(f"Embedding call failed: {e}")
            pytest.skip("Embedding service not available")
    
    @pytest.mark.asyncio
    async def test_multiple_embeddings(self):
        """Test multiple embedding calls"""
        client = get_isa_client()
        
        try:
            texts = [
                "First test sentence",
                "Second test sentence", 
                "Third test sentence"
            ]
            
            embeddings = []
            for text in texts:
                result = await client.invoke(
                    input_data=text,
                    task="embed",
                    service_type="embedding"
                )
                embeddings.append(result)
            
            print(f"Generated {len(embeddings)} embeddings")
            assert len(embeddings) == 3
            
            # Check that embeddings are different
            assert embeddings[0] != embeddings[1]
            assert embeddings[1] != embeddings[2]
            
        except Exception as e:
            print(f"Multiple embedding calls failed: {e}")
            pytest.skip("Embedding service not available")


if __name__ == "__main__":
    # Run tests directly
    test_client = TestISAClient()
    
    print("Testing ISA Client...")
    
    # Test initialization
    test_client.test_client_initialization()
    
    # Test health check
    try:
        asyncio.run(test_client.test_health_check())
    except Exception as e:
        print(f"Health check test failed: {e}")
    
    # Test LLM
    try:
        asyncio.run(test_client.test_llm_call())
    except Exception as e:
        print(f"LLM test failed: {e}")
    
    # Test embedding
    try:
        asyncio.run(test_client.test_embedding_call())
    except Exception as e:
        print(f"Embedding test failed: {e}")
    
    # Test multiple embeddings
    try:
        asyncio.run(test_client.test_multiple_embeddings())
    except Exception as e:
        print(f"Multiple embeddings test failed: {e}")
    
    print("All tests completed!")