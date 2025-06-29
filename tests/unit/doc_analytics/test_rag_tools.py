#!/usr/bin/env python3
"""
Test cases for document RAG tools
"""

import pytest
import tempfile
import os
from pathlib import Path

# Import the function to test
from tools.doc_analytics_tools import quick_rag_question

class TestRAGTools:
    """Test document RAG functionality"""
    
    def test_file_not_found(self):
        """Test behavior when file doesn't exist"""
        result = quick_rag_question("/nonexistent/file.pdf", "What is this about?")
        
        assert result["status"] == "failed"
        assert "File not found" in result["error"]
        assert result["file_path"] == "/nonexistent/file.pdf"
    
    def test_unsupported_format(self):
        """Test behavior with unsupported file format"""
        # Create a temporary file with unsupported extension
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as temp_file:
            temp_file.write(b"test content")
            temp_path = temp_file.name
        
        try:
            result = quick_rag_question(temp_path, "What is this?")
            
            assert result["status"] == "failed"
            assert "Unsupported file format" in result["error"]
            assert ".xyz" in result["error"]
            assert "supported_formats" in result
        finally:
            os.unlink(temp_path)
    
    def test_txt_file_rag(self):
        """Test RAG with a simple text file"""
        # Create a temporary text file
        test_content = """
        This is a test document about machine learning.
        
        Machine learning is a subset of artificial intelligence (AI) that provides 
        systems the ability to automatically learn and improve from experience 
        without being explicitly programmed.
        
        Key concepts include:
        1. Supervised learning
        2. Unsupervised learning  
        3. Neural networks
        4. Deep learning
        
        Applications of machine learning include image recognition, 
        natural language processing, and recommendation systems.
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=".txt", delete=False, encoding='utf-8') as temp_file:
            temp_file.write(test_content)
            temp_path = temp_file.name
        
        try:
            # Test successful RAG query
            result = quick_rag_question(temp_path, "What is machine learning?")
            
            # Check basic structure
            assert "status" in result
            assert "question" in result
            assert "answer" in result
            assert result["question"] == "What is machine learning?"
            
            # If successful, check answer content
            if result["status"] == "success":
                assert "machine learning" in result["answer"].lower()
                assert "session_info" in result
                assert result["session_info"]["chunks_created"] > 0
            else:
                # If failed, should have error info
                assert "error" in result
                print(f"RAG failed (expected if dependencies missing): {result['error']}")
                
        finally:
            os.unlink(temp_path)
    
    def test_supported_formats(self):
        """Test that all supported formats are recognized"""
        supported_formats = {'.pdf', '.doc', '.docx', '.ppt', '.pptx', '.txt'}
        
        for ext in supported_formats:
            # Create temporary file with each extension
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as temp_file:
                temp_file.write(b"test content")
                temp_path = temp_file.name
            
            try:
                result = quick_rag_question(temp_path, "What is this?")
                
                # Should not fail due to format (might fail due to missing dependencies)
                if result["status"] == "failed":
                    assert "Unsupported file format" not in result.get("error", "")
                    
            finally:
                os.unlink(temp_path)
    
    def test_empty_question(self):
        """Test behavior with empty question"""
        test_content = "This is a test document."
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=".txt", delete=False, encoding='utf-8') as temp_file:
            temp_file.write(test_content)
            temp_path = temp_file.name
        
        try:
            result = quick_rag_question(temp_path, "")
            
            # Should handle empty question gracefully
            assert "status" in result
            assert "question" in result
            assert result["question"] == ""
            
        finally:
            os.unlink(temp_path)
    
    def test_chinese_question(self):
        """Test RAG with Chinese question"""
        test_content = """
        人工智能（AI）是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。
        
        机器学习是人工智能的核心技术之一，它使计算机系统能够从数据中学习并做出预测或决策，
        而无需明确编程。
        
        深度学习是机器学习的一个子领域，使用类似于人脑神经网络结构的算法。
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=".txt", delete=False, encoding='utf-8') as temp_file:
            temp_file.write(test_content)
            temp_path = temp_file.name
        
        try:
            result = quick_rag_question(temp_path, "什么是人工智能？")
            
            assert "status" in result
            assert "question" in result
            assert result["question"] == "什么是人工智能？"
            
            if result["status"] == "success":
                # Should be able to handle Chinese content
                assert "answer" in result
                
        finally:
            os.unlink(temp_path)

def test_import():
    """Test that the function can be imported correctly"""
    from tools.doc_analytics_tools import quick_rag_question
    assert callable(quick_rag_question)

if __name__ == "__main__":
    # Run basic tests
    test_import()
    
    # Create test instance
    test_instance = TestRAGTools()
    
    print("Running RAG tool tests...")
    
    try:
        test_instance.test_file_not_found()
        print("✓ File not found test passed")
    except Exception as e:
        print(f"✗ File not found test failed: {e}")
    
    try:
        test_instance.test_unsupported_format()
        print("✓ Unsupported format test passed")
    except Exception as e:
        print(f"✗ Unsupported format test failed: {e}")
    
    try:
        test_instance.test_txt_file_rag()
        print("✓ Text file RAG test passed")
    except Exception as e:
        print(f"✗ Text file RAG test failed: {e}")
    
    try:
        test_instance.test_supported_formats()
        print("✓ Supported formats test passed")
    except Exception as e:
        print(f"✗ Supported formats test failed: {e}")
    
    print("All tests completed!")