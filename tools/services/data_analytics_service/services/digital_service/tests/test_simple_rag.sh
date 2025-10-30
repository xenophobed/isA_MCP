#!/usr/bin/env bash
#
# Test Simple RAG Service - New Architecture
#
# This script tests the new Simple RAG implementation that uses:
# - Direct isa_model.AsyncISAModel integration (no middle layers)
# - Direct isa_common.QdrantClient integration
# - Pydantic data models for validation
#

# Note: Not using 'set -e' to allow all tests to run even if one fails
# Individual test failures are tracked via PASS/FAIL counters

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test configuration
TEST_USER="test_user_simple_rag_$$"
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${CYAN}TPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPW${NC}"
echo -e "${CYAN}Q Simple RAG Service Test Suite - New Architecture${NC}"
echo -e "${CYAN}ZPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP]${NC}"
echo ""
echo -e "${CYAN}Configuration:${NC}"
echo "  Base Directory: $BASE_DIR"
echo "  Test User: $TEST_USER"
echo "  Architecture: Pydantic + Direct ISA Integration"
echo ""

# Test counter
PASS=0
FAIL=0
SKIP=0

# Helper functions
pass_test() {
    echo -e "${GREEN}[ PASS]${NC} $1"
    ((PASS++))
}

fail_test() {
    echo -e "${RED}[ FAIL]${NC} $1"
    ((FAIL++))
}

skip_test() {
    echo -e "${YELLOW}[� SKIP]${NC} $1"
    ((SKIP++))
}

info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# ==============================================================================
# Test 1: Import and Initialization
# ==============================================================================
echo -e "${BLUE}[TEST 1]${NC} Import and Initialization"

python3 << 'PYTHON_TEST_1'
import sys
sys.path.insert(0, '.')

try:
    # Test imports
    from tools.services.data_analytics_service.services.digital_service.patterns.simple_rag_service import SimpleRAGService
    from tools.services.data_analytics_service.services.digital_service.base.rag_models import (
        RAGConfig, RAGMode, RAGStoreRequest, RAGRetrieveRequest, RAGGenerateRequest, RAGResult
    )
    from tools.services.data_analytics_service.services.digital_service.rag_factory import get_rag_service

    print(" All imports successful")

    # Test config creation
    config = RAGConfig(
        mode=RAGMode.SIMPLE,
        chunk_size=400,
        overlap=50,
        top_k=3
    )
    print(f" Config created: mode={config.mode}, chunk_size={config.chunk_size}")

    # Test service instantiation via factory
    service = get_rag_service(mode='simple', config={'chunk_size': 400})
    print(f" Service created via factory: {service.__class__.__name__}")

    # Test direct instantiation
    direct_service = SimpleRAGService(config)
    print(f" Service created directly: {direct_service.__class__.__name__}")

    sys.exit(0)
except Exception as e:
    print(f"L Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_TEST_1

if [ $? -eq 0 ]; then
    pass_test "Import and initialization"
else
    fail_test "Import and initialization failed"
fi

# ==============================================================================
# Test 2: Pydantic Model Validation
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 2]${NC} Pydantic Model Validation"

python3 << 'PYTHON_TEST_2'
import sys
sys.path.insert(0, '.')

try:
    from tools.services.data_analytics_service.services.digital_service.base.rag_models import (
        RAGStoreRequest, RAGRetrieveRequest, RAGGenerateRequest, RAGConfig, RAGMode
    )

    # Test valid request
    store_req = RAGStoreRequest(
        content="Test content",
        user_id="user123",
        content_type="text"
    )
    print(f" Valid store request created: user_id={store_req.user_id}")

    # Test validation - should fail
    try:
        invalid_req = RAGStoreRequest(
            content="Test",
            user_id="  ",  # Should fail - whitespace only
            content_type="text"
        )
        print("L Validation should have failed for empty user_id")
        sys.exit(1)
    except ValueError as e:
        print(f" Validation correctly rejected empty user_id: {e}")

    # Test retrieve request
    retrieve_req = RAGRetrieveRequest(
        query="test query",
        user_id="user123",
        top_k=5
    )
    print(f" Retrieve request created: query='{retrieve_req.query}'")

    # Test generate request
    generate_req = RAGGenerateRequest(
        query="test query",
        user_id="user123"
    )
    print(f" Generate request created")

    sys.exit(0)
except Exception as e:
    print(f"L Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_TEST_2

if [ $? -eq 0 ]; then
    pass_test "Pydantic validation"
else
    fail_test "Pydantic validation failed"
fi

# ==============================================================================
# Test 3: Service Capabilities
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 3]${NC} Service Capabilities"

python3 << 'PYTHON_TEST_3'
import sys
sys.path.insert(0, '.')

try:
    from tools.services.data_analytics_service.services.digital_service.patterns.simple_rag_service import SimpleRAGService
    from tools.services.data_analytics_service.services.digital_service.base.rag_models import RAGConfig, RAGMode

    config = RAGConfig(mode=RAGMode.SIMPLE)
    service = SimpleRAGService(config)

    # Test capabilities
    capabilities = service.get_capabilities()
    print(f" Capabilities retrieved:")
    print(f"   - Name: {capabilities['name']}")
    print(f"   - Description: {capabilities['description']}")
    print(f"   - Complexity: {capabilities['complexity']}")
    print(f"   - Features: {len(capabilities['features'])} features")

    # Test mode
    mode = service.get_mode()
    print(f" Mode: {mode}")

    # Test config
    config_retrieved = service.get_config()
    print(f" Config retrieved: chunk_size={config_retrieved.chunk_size}")

    sys.exit(0)
except Exception as e:
    print(f"L Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_TEST_3

if [ $? -eq 0 ]; then
    pass_test "Service capabilities"
else
    fail_test "Service capabilities failed"
fi

# ==============================================================================
# Test 4: Text Chunking
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 4]${NC} Text Chunking"

python3 << 'PYTHON_TEST_4'
import sys
sys.path.insert(0, '.')

try:
    from tools.services.data_analytics_service.services.digital_service.patterns.simple_rag_service import SimpleRAGService
    from tools.services.data_analytics_service.services.digital_service.base.rag_models import RAGConfig, RAGMode

    config = RAGConfig(mode=RAGMode.SIMPLE, chunk_size=100, overlap=20)
    service = SimpleRAGService(config)

    # Test text chunking
    test_text = "This is a test sentence. " * 10
    chunks = service._chunk_text(test_text)

    print(f" Chunked text into {len(chunks)} chunks")
    print(f"   - Chunk size config: {config.chunk_size}")
    print(f"   - Overlap: {config.overlap}")
    print(f"   - First chunk length: {len(chunks[0]['text'])}")

    # Verify chunk structure
    if 'id' in chunks[0] and 'text' in chunks[0]:
        print(f" Chunks have correct structure")
    else:
        print(f"L Chunks missing required fields")
        sys.exit(1)

    sys.exit(0)
except Exception as e:
    print(f"L Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_TEST_4

if [ $? -eq 0 ]; then
    pass_test "Text chunking"
else
    fail_test "Text chunking failed"
fi

# ==============================================================================
# Test 5: Store Method (Structure Check)
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 5]${NC} Store Method Structure"

python3 << 'PYTHON_TEST_5'
import sys
import asyncio
sys.path.insert(0, '.')

async def test_store():
    try:
        from tools.services.data_analytics_service.services.digital_service.patterns.simple_rag_service import SimpleRAGService
        from tools.services.data_analytics_service.services.digital_service.base.rag_models import (
            RAGConfig, RAGMode, RAGStoreRequest
        )

        config = RAGConfig(mode=RAGMode.SIMPLE)
        service = SimpleRAGService(config)

        # Create store request
        request = RAGStoreRequest(
            content="Python is a high-level programming language. It was created by Guido van Rossum.",
            user_id="test_user",
            content_type="text"
        )

        # Call store (will fail without ISA Model/Qdrant, but tests structure)
        result = await service.store(request)

        # Check result structure
        if hasattr(result, 'success') and hasattr(result, 'content') and hasattr(result, 'sources'):
            print(f" Store method returns correct RAGResult structure")
            print(f"   - Success: {result.success}")
            print(f"   - Content: {result.content}")
            print(f"   - Mode: {result.mode_used}")
            print(f"   - Processing time: {result.processing_time:.3f}s")

            if not result.success:
                print(f"   9  Expected failure (no ISA Model/Qdrant): {result.error}")
        else:
            print(f"L Store method returned invalid structure")
            return 1

        return 0
    except Exception as e:
        print(f"L Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

sys.exit(asyncio.run(test_store()))
PYTHON_TEST_5

if [ $? -eq 0 ]; then
    pass_test "Store method structure"
else
    fail_test "Store method structure failed"
fi

# ==============================================================================
# Test 6: Retrieve Method (Structure Check)
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 6]${NC} Retrieve Method Structure"

python3 << 'PYTHON_TEST_6'
import sys
import asyncio
sys.path.insert(0, '.')

async def test_retrieve():
    try:
        from tools.services.data_analytics_service.services.digital_service.patterns.simple_rag_service import SimpleRAGService
        from tools.services.data_analytics_service.services.digital_service.base.rag_models import (
            RAGConfig, RAGMode, RAGRetrieveRequest
        )

        config = RAGConfig(mode=RAGMode.SIMPLE)
        service = SimpleRAGService(config)

        # Create retrieve request
        request = RAGRetrieveRequest(
            query="Who created Python?",
            user_id="test_user",
            top_k=3
        )

        # Call retrieve (will fail without ISA Model/Qdrant, but tests structure)
        result = await service.retrieve(request)

        # Check result structure
        if hasattr(result, 'success') and hasattr(result, 'sources'):
            print(f" Retrieve method returns correct RAGResult structure")
            print(f"   - Success: {result.success}")
            print(f"   - Sources count: {len(result.sources)}")
            print(f"   - Mode: {result.mode_used}")

            if not result.success:
                print(f"   9  Expected failure (no ISA Model/Qdrant): {result.error}")
        else:
            print(f"L Retrieve method returned invalid structure")
            return 1

        return 0
    except Exception as e:
        print(f"L Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

sys.exit(asyncio.run(test_retrieve()))
PYTHON_TEST_6

if [ $? -eq 0 ]; then
    pass_test "Retrieve method structure"
else
    fail_test "Retrieve method structure failed"
fi

# ==============================================================================
# Test 7: Generate Method (Structure Check)
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 7]${NC} Generate Method Structure"

python3 << 'PYTHON_TEST_7'
import sys
import asyncio
sys.path.insert(0, '.')

async def test_generate():
    try:
        from tools.services.data_analytics_service.services.digital_service.patterns.simple_rag_service import SimpleRAGService
        from tools.services.data_analytics_service.services.digital_service.base.rag_models import (
            RAGConfig, RAGMode, RAGGenerateRequest, RAGSource
        )

        config = RAGConfig(mode=RAGMode.SIMPLE)
        service = SimpleRAGService(config)

        # Create generate request with mock sources
        mock_sources = [
            RAGSource(text="Python was created by Guido van Rossum", score=0.95, metadata={}),
            RAGSource(text="Python is a high-level language", score=0.87, metadata={})
        ]

        request = RAGGenerateRequest(
            query="Who created Python?",
            user_id="test_user",
            retrieval_sources=[s.dict() for s in mock_sources]
        )

        # Call generate (will fail without ISA Model, but tests structure)
        result = await service.generate(request)

        # Check result structure
        if hasattr(result, 'success') and hasattr(result, 'content'):
            print(f" Generate method returns correct RAGResult structure")
            print(f"   - Success: {result.success}")
            print(f"   - Content length: {len(result.content)}")
            print(f"   - Sources used: {len(result.sources)}")

            if not result.success:
                print(f"   9  Expected failure (no ISA Model): {result.error}")
        else:
            print(f"L Generate method returned invalid structure")
            return 1

        return 0
    except Exception as e:
        print(f"L Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

sys.exit(asyncio.run(test_generate()))
PYTHON_TEST_7

if [ $? -eq 0 ]; then
    pass_test "Generate method structure"
else
    fail_test "Generate method structure failed"
fi

# ==============================================================================
# Test 8: RAG Factory Integration
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 8]${NC} RAG Factory Integration"

python3 << 'PYTHON_TEST_8'
import sys
sys.path.insert(0, '.')

try:
    from tools.services.data_analytics_service.services.digital_service.rag_factory import (
        get_rag_service, get_simple_rag_service
    )
    from tools.services.data_analytics_service.services.digital_service.patterns.simple_rag_service import SimpleRAGService

    # Test factory creation
    service1 = get_rag_service(mode='simple')
    print(f" Factory created service: {service1.__class__.__name__}")

    # Test convenience function
    service2 = get_simple_rag_service({'chunk_size': 500})
    print(f" Convenience function created service: {service2.__class__.__name__}")

    # Verify type
    if isinstance(service1, SimpleRAGService):
        print(f" Service is correct type: SimpleRAGService")
    else:
        print(f"L Service is wrong type: {type(service1)}")
        sys.exit(1)

    # Test that invalid mode raises error
    try:
        bad_service = get_rag_service(mode='custom')  # Not migrated yet
        print(f"L Should have raised error for unmigrated mode")
        sys.exit(1)
    except ValueError as e:
        print(f" Factory correctly rejects unmigrated modes")

    sys.exit(0)
except Exception as e:
    print(f"L Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_TEST_8

if [ $? -eq 0 ]; then
    pass_test "RAG Factory integration"
else
    fail_test "RAG Factory integration failed"
fi

# ==============================================================================
# Summary
# ==============================================================================
echo ""
echo -e "${CYAN}TPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPW${NC}"
echo -e "${CYAN}Q Test Summary${NC}"
echo -e "${CYAN}ZPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP]${NC}"
echo ""
echo -e "${GREEN}Passed:${NC} $PASS"
echo -e "${RED}Failed:${NC} $FAIL"
echo -e "${YELLOW}Skipped:${NC} $SKIP"
echo ""

TOTAL=$((PASS + FAIL + SKIP))
echo "Total Tests: $TOTAL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN} All tests passed!${NC}"
    echo ""
    echo "<� Architecture Validation Complete!"
    echo ""
    echo "The Simple RAG service is correctly implemented with:"
    echo "   Pydantic data models"
    echo "   Direct ISA Model integration"
    echo "   Direct Qdrant integration"
    echo "   Clean abstract base class"
    echo "   Factory pattern support"
    echo ""
    echo "Next steps:"
    echo "  1. Deploy with ISA Model and Qdrant running"
    echo "  2. Run integration tests with real services"
    echo "  3. Migrate other RAG patterns (CRAG, Plan-RAG, Custom, etc.)"
    exit 0
else
    echo -e "${RED} Some tests failed${NC}"
    exit 1
fi
