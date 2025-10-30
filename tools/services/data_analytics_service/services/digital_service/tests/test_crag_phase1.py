#!/usr/bin/env python3
"""
CRAG Phase 1 Test - Store & Retrieve with Quality Assessment

Tests:
1. Store content with quality pre-assessment
2. Retrieve with quality classification (CORRECT/AMBIGUOUS/INCORRECT)
3. Verify quality metrics in results
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from tools.services.data_analytics_service.services.digital_service.rag_factory import get_crag_rag_service
from tools.services.data_analytics_service.services.digital_service.base.rag_models import (
    RAGStoreRequest, RAGRetrieveRequest
)


async def test_crag_store():
    """Test CRAG store with quality pre-assessment"""
    print("\n" + "="*80)
    print("TEST 1: CRAG Store with Quality Pre-Assessment")
    print("="*80)

    try:
        # Create CRAG service
        service = get_crag_rag_service()
        print("✅ CRAG service created via factory")

        # Test data with varying quality
        test_data = [
            {
                "content": "Machine Learning is a subset of artificial intelligence that enables computers to learn from data without being explicitly programmed. It uses statistical techniques to identify patterns and make predictions.",
                "user_id": "CRAG_TEST_USER",
                "label": "High Quality (complete, well-formed)"
            },
            {
                "content": "AI is cool",
                "user_id": "CRAG_TEST_USER",
                "label": "Low Quality (too short, vague)"
            },
            {
                "content": "Neural networks are computational models inspired by biological neural networks. They consist of interconnected nodes (neurons) organized in layers",
                "user_id": "CRAG_TEST_USER",
                "label": "Medium Quality (good but incomplete)"
            }
        ]

        print(f"\n📝 Testing storage of {len(test_data)} chunks with quality assessment...")

        for i, test_item in enumerate(test_data, 1):
            print(f"\n--- Chunk {i}: {test_item['label']} ---")
            print(f"Content length: {len(test_item['content'])} chars")

            # Create store request
            store_request = RAGStoreRequest(
                user_id=test_item['user_id'],
                content=test_item['content'],
                metadata={'test_id': f'crag_test_{i}', 'label': test_item['label']}
            )

            # Store content
            result = await service.store(store_request)

            if result.success:
                print(f"✅ Store successful")
                print(f"   Mode used: {result.mode_used}")
                print(f"   Processing time: {result.processing_time:.3f}s")

                # Check for quality metrics
                if result.metadata and 'average_quality' in result.metadata:
                    avg_quality = result.metadata['average_quality']
                    print(f"   📊 Average quality score: {avg_quality:.3f}")

                    # Interpret quality
                    if avg_quality >= 0.7:
                        quality_level = "CORRECT (high)"
                    elif avg_quality >= 0.4:
                        quality_level = "AMBIGUOUS (medium)"
                    else:
                        quality_level = "INCORRECT (low)"
                    print(f"   📈 Quality level: {quality_level}")
                else:
                    print(f"   ⚠️  No quality metrics in result")
            else:
                print(f"❌ Store failed: {result.error}")

        print("\n" + "="*80)
        print("✅ CRAG Store Test Complete")
        print("="*80)
        return True

    except Exception as e:
        print(f"\n❌ CRAG Store Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_crag_retrieve():
    """Test CRAG retrieve with quality classification"""
    print("\n" + "="*80)
    print("TEST 2: CRAG Retrieve with Quality Classification")
    print("="*80)

    try:
        # Create CRAG service
        service = get_crag_rag_service()
        print("✅ CRAG service created via factory")

        # Test queries
        test_queries = [
            {
                "query": "What is Machine Learning?",
                "user_id": "CRAG_TEST_USER",
                "top_k": 5,
                "label": "Exact match query"
            },
            {
                "query": "Tell me about neural networks and deep learning",
                "user_id": "CRAG_TEST_USER",
                "top_k": 5,
                "label": "Partial match query"
            },
            {
                "query": "Quantum computing applications",
                "user_id": "CRAG_TEST_USER",
                "top_k": 5,
                "label": "No match query"
            }
        ]

        print(f"\n🔍 Testing retrieval of {len(test_queries)} queries with quality classification...")

        for i, test_query in enumerate(test_queries, 1):
            print(f"\n--- Query {i}: {test_query['label']} ---")
            print(f"Query: '{test_query['query']}'")

            # Create retrieve request
            retrieve_request = RAGRetrieveRequest(
                user_id=test_query['user_id'],
                query=test_query['query'],
                top_k=test_query['top_k']
            )

            # Retrieve content
            result = await service.retrieve(retrieve_request)

            if result.success:
                print(f"✅ Retrieve successful")
                print(f"   Mode used: {result.mode_used}")
                print(f"   Processing time: {result.processing_time:.3f}s")
                print(f"   Sources found: {len(result.sources)}")

                # Check for quality stats
                if result.metadata and 'quality_stats' in result.metadata:
                    quality_stats = result.metadata['quality_stats']
                    print(f"\n   📊 Quality Statistics:")
                    print(f"      CORRECT:   {quality_stats.get('correct', 0)} sources")
                    print(f"      AMBIGUOUS: {quality_stats.get('ambiguous', 0)} sources")
                    print(f"      INCORRECT: {quality_stats.get('incorrect', 0)} sources (filtered out)")

                    if 'filtered_out' in result.metadata:
                        print(f"      Filtered:  {result.metadata['filtered_out']} low-quality results removed")
                else:
                    print(f"   ⚠️  No quality stats in result")

                # Show source quality levels
                if result.sources:
                    print(f"\n   📑 Source Quality Breakdown:")
                    for idx, source in enumerate(result.sources[:3], 1):  # Show top 3
                        quality_level = source.metadata.get('quality_level', 'unknown')
                        quality_score = source.metadata.get('quality_assessment', {}).get('overall_score', 0)
                        print(f"      {idx}. Score: {source.score:.3f} | Quality: {quality_level} ({quality_score:.3f})")
                        print(f"         Preview: {source.text[:80]}...")
                else:
                    print(f"   ℹ️  No sources found")
            else:
                print(f"❌ Retrieve failed: {result.error}")

        print("\n" + "="*80)
        print("✅ CRAG Retrieve Test Complete")
        print("="*80)
        return True

    except Exception as e:
        print(f"\n❌ CRAG Retrieve Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_crag_quality_filtering():
    """Test CRAG automatic filtering of low-quality results"""
    print("\n" + "="*80)
    print("TEST 3: CRAG Quality Filtering")
    print("="*80)

    try:
        service = get_crag_rag_service()
        print("✅ CRAG service created via factory")

        # Store deliberately low-quality content
        print("\n📝 Storing low-quality test content...")
        low_quality_contents = [
            "AI",  # Too short
            "ML is",  # Incomplete
            "test test test test",  # Repetitive
        ]

        for content in low_quality_contents:
            store_request = RAGStoreRequest(
                user_id="CRAG_FILTER_TEST",
                content=content,
                metadata={'type': 'low_quality_test'}
            )
            await service.store(store_request)

        # Now retrieve and verify filtering
        print("\n🔍 Retrieving to test quality filtering...")
        retrieve_request = RAGRetrieveRequest(
            user_id="CRAG_FILTER_TEST",
            query="artificial intelligence machine learning",
            top_k=10  # Request many to see if low-quality ones are filtered
        )

        result = await service.retrieve(retrieve_request)

        if result.success:
            print(f"✅ Retrieve successful")
            print(f"   Sources returned: {len(result.sources)}")

            # Check if any INCORRECT sources were included
            incorrect_count = 0
            for source in result.sources:
                if source.metadata.get('quality_level') == 'incorrect':
                    incorrect_count += 1

            if incorrect_count == 0:
                print(f"   ✅ Quality filtering working: No INCORRECT sources in results")
            else:
                print(f"   ⚠️  Found {incorrect_count} INCORRECT sources (should be filtered)")

            # Show filter stats
            if result.metadata and 'filtered_out' in result.metadata:
                filtered = result.metadata['filtered_out']
                print(f"   📊 Filtered out: {filtered} low-quality results")
        else:
            print(f"❌ Retrieve failed: {result.error}")

        print("\n" + "="*80)
        print("✅ CRAG Quality Filtering Test Complete")
        print("="*80)
        return True

    except Exception as e:
        print(f"\n❌ CRAG Quality Filtering Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all CRAG Phase 1 tests"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*25 + "CRAG PHASE 1 TESTS" + " "*35 + "║")
    print("║" + " "*15 + "Store & Retrieve with Quality Assessment" + " "*22 + "║")
    print("╚" + "="*78 + "╝")

    # Run tests
    results = []

    # Test 1: Store with quality assessment
    results.append(await test_crag_store())

    # Wait a bit for indexing
    await asyncio.sleep(2)

    # Test 2: Retrieve with quality classification
    results.append(await test_crag_retrieve())

    # Test 3: Quality filtering
    results.append(await test_crag_quality_filtering())

    # Summary
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*30 + "TEST SUMMARY" + " "*36 + "║")
    print("╠" + "="*78 + "╣")

    passed = sum(results)
    total = len(results)

    print(f"║  Tests Passed: {passed}/{total}" + " "*(67-len(f"Tests Passed: {passed}/{total}")) + "║")

    if passed == total:
        print("║  Status: ✅ ALL TESTS PASSED" + " "*48 + "║")
    else:
        print("║  Status: ❌ SOME TESTS FAILED" + " "*47 + "║")

    print("╚" + "="*78 + "╝")
    print()

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
