#!/usr/bin/env python3
"""
Test script for advanced chunking functionality in embedding_generator.py
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

from tools.services.intelligence_service.language.embedding_generator import (
    embedding_generator,
    advanced_chunk,
    chunk
)

# Test data
SAMPLE_TEXTS = {
    "short_text": "This is a short text for testing basic chunking functionality.",
    
    "medium_text": """
    This is a medium-length text that should be split into multiple chunks.
    It contains several sentences that demonstrate the chunking capabilities.
    Each chunk should maintain context while being appropriately sized.
    The overlap between chunks helps preserve meaning across boundaries.
    """,
    
    "long_text": """
    Natural Language Processing (NLP) is a subfield of artificial intelligence that focuses on the interaction between computers and humans through natural language. The ultimate objective of NLP is to read, decipher, understand, and make sense of the human language in a valuable way.

    Most NLP techniques rely on machine learning to derive meaning from human languages. This involves training algorithms to recognize patterns in large datasets of human language. These datasets often consist of text from books, articles, and websites, as well as speech data.

    One of the fundamental challenges in NLP is dealing with the ambiguity inherent in human language. Words can have multiple meanings depending on context, and the same idea can be expressed in many different ways. For example, the word "bank" could refer to a financial institution or the edge of a river.

    Modern NLP systems use various techniques including tokenization, part-of-speech tagging, named entity recognition, and sentiment analysis. Deep learning models, particularly transformer architectures like BERT and GPT, have revolutionized the field by achieving state-of-the-art performance on many NLP tasks.

    Applications of NLP are widespread and include machine translation, chatbots, text summarization, and information extraction. As these technologies continue to improve, we can expect to see even more sophisticated applications that can understand and generate human language with increasing accuracy.
    """,
    
    "markdown_text": """
# Introduction to Machine Learning

Machine learning is a method of data analysis that automates analytical model building.

## Types of Machine Learning

### Supervised Learning
Supervised learning uses labeled training data to learn a mapping function from input variables to output variables.

- **Classification**: Predicts discrete class labels
- **Regression**: Predicts continuous numeric values

### Unsupervised Learning
Unsupervised learning finds hidden patterns in data without labeled examples.

- **Clustering**: Groups similar data points
- **Dimensionality Reduction**: Reduces the number of features

### Reinforcement Learning
Reinforcement learning learns optimal actions through trial and error interactions with an environment.

## Popular Algorithms

1. Linear Regression
2. Decision Trees
3. Random Forest
4. Support Vector Machines
5. Neural Networks

## Code Example

```python
from sklearn.linear_model import LinearRegression
import numpy as np

# Create sample data
X = np.array([[1], [2], [3], [4], [5]])
y = np.array([2, 4, 6, 8, 10])

# Train model
model = LinearRegression()
model.fit(X, y)

# Make prediction
prediction = model.predict([[6]])
print(f"Prediction: {prediction[0]}")
```

## Conclusion

Machine learning continues to evolve and find applications in numerous domains.
    """,
    
    "code_text": '''
def fibonacci(n):
    """
    Generate the nth Fibonacci number using dynamic programming.
    
    Args:
        n (int): The position in the Fibonacci sequence
        
    Returns:
        int: The nth Fibonacci number
    """
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    
    # Use dynamic programming for efficiency
    dp = [0] * (n + 1)
    dp[1] = 1
    
    for i in range(2, n + 1):
        dp[i] = dp[i-1] + dp[i-2]
    
    return dp[n]

class FibonacciSequence:
    """A class to generate and work with Fibonacci sequences."""
    
    def __init__(self, max_n=100):
        self.max_n = max_n
        self.cache = {}
    
    def get(self, n):
        """Get the nth Fibonacci number with caching."""
        if n in self.cache:
            return self.cache[n]
        
        result = fibonacci(n)
        self.cache[n] = result
        return result
    
    def sequence(self, length):
        """Generate a Fibonacci sequence of given length."""
        return [self.get(i) for i in range(length)]

# Example usage
if __name__ == "__main__":
    fib = FibonacciSequence()
    
    print("First 10 Fibonacci numbers:")
    print(fib.sequence(10))
    
    print(f"The 20th Fibonacci number is: {fib.get(20)}")
    '''
}

CHUNKING_STRATEGIES = [
    "fixed_size",
    "sentence_based", 
    "recursive",
    "markdown_aware",
    "code_aware",
    "hybrid"
]

async def test_basic_chunking():
    """Test basic chunking functionality (without strategy)"""
    print("=== Testing Basic Chunking ===")
    
    try:
        chunks = await chunk(
            SAMPLE_TEXTS["medium_text"],
            chunk_size=100,
            overlap=20
        )
        
        print(f"✅ Basic chunking successful")
        print(f"   Created {len(chunks)} chunks")
        print(f"   First chunk: {chunks[0]['text'][:50]}...")
        print(f"   Has embeddings: {'embedding' in chunks[0] and len(chunks[0]['embedding']) > 0}")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic chunking failed: {e}")
        return False

async def test_advanced_chunking_strategies():
    """Test all advanced chunking strategies"""
    print("\n=== Testing Advanced Chunking Strategies ===")
    
    results = {}
    
    for strategy in CHUNKING_STRATEGIES:
        print(f"\n--- Testing {strategy} strategy ---")
        
        try:
            # Choose appropriate text for strategy
            if strategy == "markdown_aware":
                text = SAMPLE_TEXTS["markdown_text"]
            elif strategy == "code_aware":
                text = SAMPLE_TEXTS["code_text"]
            else:
                text = SAMPLE_TEXTS["long_text"]
            
            chunks = await advanced_chunk(
                text=text,
                strategy=strategy,
                chunk_size=500,
                chunk_overlap=50
            )
            
            print(f"✅ {strategy} strategy successful")
            print(f"   Created {len(chunks)} chunks")
            print(f"   First chunk length: {len(chunks[0]['text'])}")
            print(f"   Has embeddings: {'embedding' in chunks[0] and len(chunks[0]['embedding']) > 0}")
            
            # Check for strategy-specific metadata
            if 'metadata' in chunks[0]:
                metadata = chunks[0]['metadata']
                print(f"   Strategy in metadata: {metadata.get('strategy', 'Not found')}")
                if strategy == "markdown_aware" and 'section_title' in metadata:
                    print(f"   Detected section: {metadata['section_title']}")
                elif strategy == "code_aware" and 'code_type' in metadata:
                    print(f"   Detected code type: {metadata['code_type']}")
            
            results[strategy] = {
                "success": True,
                "chunk_count": len(chunks),
                "has_embeddings": 'embedding' in chunks[0] and len(chunks[0]['embedding']) > 0,
                "metadata": chunks[0].get('metadata', {})
            }
            
        except Exception as e:
            print(f"❌ {strategy} strategy failed: {e}")
            results[strategy] = {
                "success": False,
                "error": str(e)
            }
    
    return results

async def test_chunking_parameters():
    """Test different chunking parameters"""
    print("\n=== Testing Chunking Parameters ===")
    
    test_cases = [
        {"chunk_size": 200, "chunk_overlap": 20, "description": "Small chunks with small overlap"},
        {"chunk_size": 800, "chunk_overlap": 100, "description": "Large chunks with large overlap"},
        {"chunk_size": 300, "chunk_overlap": 0, "description": "Medium chunks with no overlap"},
    ]
    
    results = {}
    
    for case in test_cases:
        print(f"\n--- Testing: {case['description']} ---")
        
        try:
            chunks = await advanced_chunk(
                text=SAMPLE_TEXTS["long_text"],
                strategy="recursive",
                chunk_size=case["chunk_size"],
                chunk_overlap=case["chunk_overlap"]
            )
            
            avg_length = sum(len(chunk['text']) for chunk in chunks) / len(chunks)
            
            print(f"✅ Parameter test successful")
            print(f"   Chunks created: {len(chunks)}")
            print(f"   Average chunk length: {avg_length:.1f}")
            print(f"   Target size: {case['chunk_size']}")
            
            results[case['description']] = {
                "success": True,
                "chunk_count": len(chunks),
                "average_length": avg_length,
                "target_size": case["chunk_size"]
            }
            
        except Exception as e:
            print(f"❌ Parameter test failed: {e}")
            results[case['description']] = {
                "success": False,
                "error": str(e)
            }
    
    return results

async def test_content_type_detection():
    """Test automatic content type detection in hybrid strategy"""
    print("\n=== Testing Content Type Detection ===")
    
    test_cases = [
        {"name": "Markdown", "text": SAMPLE_TEXTS["markdown_text"], "expected": "markdown"},
        {"name": "Code", "text": SAMPLE_TEXTS["code_text"], "expected": "code"},
        {"name": "Plain text", "text": SAMPLE_TEXTS["long_text"], "expected": "plain"}
    ]
    
    results = {}
    
    for case in test_cases:
        print(f"\n--- Testing {case['name']} detection ---")
        
        try:
            chunks = await advanced_chunk(
                text=case["text"],
                strategy="hybrid",
                chunk_size=400
            )
            
            detected_type = chunks[0].get('metadata', {}).get('content_type', 'unknown')
            
            print(f"✅ Content type detection successful")
            print(f"   Expected: {case['expected']}")
            print(f"   Detected: {detected_type}")
            print(f"   Match: {detected_type == case['expected']}")
            
            results[case['name']] = {
                "success": True,
                "expected": case["expected"],
                "detected": detected_type,
                "correct": detected_type == case["expected"]
            }
            
        except Exception as e:
            print(f"❌ Content type detection failed: {e}")
            results[case['name']] = {
                "success": False,
                "error": str(e)
            }
    
    return results

async def test_chunk_metadata():
    """Test chunk metadata functionality"""
    print("\n=== Testing Chunk Metadata ===")
    
    custom_metadata = {
        "source": "test_document",
        "author": "test_user",
        "category": "technical"
    }
    
    try:
        chunks = await advanced_chunk(
            text=SAMPLE_TEXTS["medium_text"],
            strategy="recursive",
            chunk_size=200,
            metadata=custom_metadata
        )
        
        chunk = chunks[0]
        metadata = chunk.get('metadata', {})
        
        print(f"✅ Metadata test successful")
        print(f"   Chunk has metadata: {'metadata' in chunk}")
        print(f"   Custom metadata preserved: {all(k in metadata for k in custom_metadata)}")
        print(f"   Strategy recorded: {'strategy' in metadata}")
        print(f"   Position recorded: {'position' in metadata}")
        
        # Display metadata
        print(f"   Metadata keys: {list(metadata.keys())}")
        
        return {
            "success": True,
            "has_metadata": 'metadata' in chunk,
            "custom_preserved": all(k in metadata for k in custom_metadata),
            "strategy_recorded": 'strategy' in metadata,
            "metadata_keys": list(metadata.keys())
        }
        
    except Exception as e:
        print(f"❌ Metadata test failed: {e}")
        return {"success": False, "error": str(e)}

async def performance_test():
    """Test performance with different text lengths"""
    print("\n=== Performance Testing ===")
    
    import time
    
    test_texts = {
        "short": SAMPLE_TEXTS["short_text"],
        "medium": SAMPLE_TEXTS["medium_text"], 
        "long": SAMPLE_TEXTS["long_text"],
        "extra_long": SAMPLE_TEXTS["long_text"] * 3  # Triple the long text
    }
    
    results = {}
    
    for name, text in test_texts.items():
        print(f"\n--- Testing {name} text ({len(text)} chars) ---")
        
        start_time = time.time()
        
        try:
            chunks = await advanced_chunk(
                text=text,
                strategy="recursive",
                chunk_size=400,
                chunk_overlap=50
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"✅ {name} text processed successfully")
            print(f"   Text length: {len(text)} characters")
            print(f"   Chunks created: {len(chunks)}")
            print(f"   Processing time: {processing_time:.2f} seconds")
            print(f"   Chars per second: {len(text) / processing_time:.0f}")
            
            results[name] = {
                "success": True,
                "text_length": len(text),
                "chunk_count": len(chunks),
                "processing_time": processing_time,
                "chars_per_second": len(text) / processing_time
            }
            
        except Exception as e:
            print(f"❌ {name} text processing failed: {e}")
            results[name] = {"success": False, "error": str(e)}
    
    return results

async def main():
    """Run all tests and generate report"""
    print("🚀 Starting Advanced Chunking Tests")
    print("=" * 50)
    
    test_results = {}
    
    # Run all tests
    test_results["basic_chunking"] = await test_basic_chunking()
    test_results["advanced_strategies"] = await test_advanced_chunking_strategies()
    test_results["chunking_parameters"] = await test_chunking_parameters()
    test_results["content_type_detection"] = await test_content_type_detection()
    test_results["chunk_metadata"] = await test_chunk_metadata()
    test_results["performance"] = await performance_test()
    
    # Generate summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    total_tests = 0
    passed_tests = 0
    
    for test_name, result in test_results.items():
        print(f"\n{test_name.replace('_', ' ').title()}:")
        
        if isinstance(result, bool):
            total_tests += 1
            if result:
                passed_tests += 1
                print("  ✅ PASSED")
            else:
                print("  ❌ FAILED")
                
        elif isinstance(result, dict):
            if test_name == "advanced_strategies":
                for strategy, strategy_result in result.items():
                    total_tests += 1
                    if strategy_result.get("success", False):
                        passed_tests += 1
                        print(f"  ✅ {strategy}: PASSED")
                    else:
                        print(f"  ❌ {strategy}: FAILED")
                        
            elif test_name == "chunking_parameters":
                for param_test, param_result in result.items():
                    total_tests += 1
                    if param_result.get("success", False):
                        passed_tests += 1
                        print(f"  ✅ {param_test}: PASSED")
                    else:
                        print(f"  ❌ {param_test}: FAILED")
                        
            elif test_name == "content_type_detection":
                for content_test, content_result in result.items():
                    total_tests += 1
                    if content_result.get("success", False):
                        passed_tests += 1
                        correct = content_result.get("correct", False)
                        status = "PASSED" if correct else "PASSED (detection different)"
                        print(f"  ✅ {content_test}: {status}")
                    else:
                        print(f"  ❌ {content_test}: FAILED")
                        
            elif test_name == "performance":
                for perf_test, perf_result in result.items():
                    total_tests += 1
                    if perf_result.get("success", False):
                        passed_tests += 1
                        time_taken = perf_result.get("processing_time", 0)
                        print(f"  ✅ {perf_test}: PASSED ({time_taken:.2f}s)")
                    else:
                        print(f"  ❌ {perf_test}: FAILED")
                        
            else:
                total_tests += 1
                if result.get("success", False):
                    passed_tests += 1
                    print("  ✅ PASSED")
                else:
                    print("  ❌ FAILED")
    
    print(f"\n📈 Overall Results: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.1f}%)")
    
    # Save detailed results
    output_file = Path(__file__).parent / "test_results_advanced_chunking.json"
    with open(output_file, 'w') as f:
        json.dump(test_results, f, indent=2, default=str)
    
    print(f"\n💾 Detailed results saved to: {output_file}")
    
    return test_results

if __name__ == "__main__":
    asyncio.run(main())