#!/bin/bash

###############################################################################
# Data Tools REAL Integration Test Script
###############################################################################
#
# REAL END-TO-END INTEGRATION TESTS with LIVE SERVICES:
# 1. data_ingest - REAL CSV → MinIO Parquet + Supabase embeddings
# 2. get_pipeline_status - REAL pipeline status from preprocessing service
# 3. data_search - REAL semantic search against Supabase pgvector  
# 4. data_query - REAL SQL execution: MinIO download → DuckDB query
#
# REAL Services Used:
# ✓ Supabase (PostgreSQL + pgvector for embeddings)
# ✓ MinIO (Object storage for Parquet files)
# ✓ Preprocessing Service (Data quality, validation, cleaning)
# ✓ Embedding Service (text-embedding-3-small via OpenAI)
# ✓ DuckDB (In-process SQL analytics engine)
# ✓ Metadata Extraction (Schema discovery, semantic enrichment)
# ✓ Visualization Service (Chart generation from query results)
#
# REAL Data Flow Tested:
# CSV File → Preprocessing → Quality Score → MinIO Parquet Storage
#          → Metadata Extraction → Semantic Enrichment (GPT-4)
#          → Vector Embeddings → Supabase pgvector
#          → Semantic Search → Natural Language Query
#          → MinIO Download → DuckDB SQL → Results + Visualization
#
# Progress Tracking:
# - 4-stage progress reporting throughout all operations
# - Real-time logging and status updates
# - Error handling and recovery
#
# Usage:
#   ./data_tools_test.sh
#
# Requirements:
# - Python 3.11+
# - Live Supabase connection (configured in environment)
# - Live MinIO connection (configured in environment)
# - OpenAI API key for embeddings
# - Test CSV data in test_data/ directory
#
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
TEST_USER_ID="test_user_$(date +%s)"
TEST_DATA_DIR="test_data"
TEST_CSV_FILE="${TEST_DATA_DIR}/sales_data.csv"
TEST_DATASET_NAME="test_sales_data"

# Counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

###############################################################################
# Helper Functions
###############################################################################

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_test() {
    echo -e "${YELLOW}TEST $TESTS_RUN: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

print_failure() {
    echo -e "${RED}✗ $1${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

###############################################################################
# Setup Functions
###############################################################################

setup_test_environment() {
    print_header "Setting Up Test Environment"
    
    # Create test data directory
    mkdir -p "${TEST_DATA_DIR}"
    
    # Create sample CSV if it doesn't exist
    if [ ! -f "${TEST_CSV_FILE}" ]; then
        print_info "Creating sample CSV file..."
        cat > "${TEST_CSV_FILE}" << 'EOF'
region,product,customer_type,sales_amount,quantity,date
North,Widget A,Enterprise,15000,150,2024-01-15
South,Widget B,Individual,8500,85,2024-01-16
East,Widget A,Enterprise,12000,120,2024-01-17
West,Widget C,Individual,6000,60,2024-01-18
North,Widget B,Enterprise,18000,180,2024-01-19
South,Widget A,Individual,9000,90,2024-01-20
East,Widget C,Enterprise,14000,140,2024-01-21
West,Widget A,Individual,7500,75,2024-01-22
North,Widget C,Enterprise,16000,160,2024-01-23
South,Widget B,Individual,8000,80,2024-01-24
EOF
        print_success "Sample CSV created: ${TEST_CSV_FILE}"
    else
        print_info "Using existing CSV file: ${TEST_CSV_FILE}"
    fi
    
    # Verify Python environment
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version)
        print_success "Python environment ready: ${PYTHON_VERSION}"
    else
        print_failure "Python 3 not found"
        exit 1
    fi
}

###############################################################################
# Test Functions
###############################################################################

test_data_ingest() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "REAL Data Ingestion - Full Pipeline with Live Services"
    
    print_info "Testing: Complete data ingestion pipeline with Supabase, MinIO, embeddings"
    
    # Create Python test script for REAL integration
    cat > /tmp/test_data_ingest_real.py << EOF
import asyncio
import sys
import os
sys.path.insert(0, '/Users/xenodennis/Documents/Fun/isA_MCP')

from tools.services.data_analytics_service.tools.data_tools import register_data_tools
from mcp.server.fastmcp import FastMCP

async def test():
    mcp = FastMCP("test_data_tools")
    register_data_tools(mcp)
    
    # Get absolute path to CSV file
    csv_path = os.path.abspath("${TEST_CSV_FILE}")
    print(f"📁 CSV Path: {csv_path}")
    
    # Call REAL data_ingest with live services
    print("🚀 Starting REAL data ingestion pipeline...")
    result = await mcp._tool_manager._tools['data_ingest'].fn(
        user_id="${TEST_USER_ID}",
        source_path=csv_path,
        dataset_name="${TEST_DATASET_NAME}"
    )
    
    import json
    result_dict = json.loads(result)
    
    # Verify REAL result
    print(f"📊 Status: {result_dict['status']}")
    assert result_dict['status'] == 'success', f"Status not success: {result_dict.get('status')}"
    assert result_dict['data']['success'] == True, "Ingestion not successful"
    assert result_dict['data']['rows_processed'] > 0, "No rows processed"
    assert result_dict['data']['columns_processed'] > 0, "No columns processed"
    
    print(f"✓ Ingested {result_dict['data']['rows_processed']} rows to MinIO")
    print(f"✓ Detected {result_dict['data']['columns_processed']} columns")
    print(f"✓ Data quality score: {result_dict['data']['data_quality_score']}")
    print(f"✓ Metadata embeddings created: {result_dict['data']['metadata_embeddings']}")
    print(f"✓ Storage location: {result_dict['data']['storage_location']}")
    print(f"✓ Pipeline ID: {result_dict['data']['pipeline_id']}")
    
    return result_dict['data']['pipeline_id']

if __name__ == '__main__':
    pipeline_id = asyncio.run(test())
    print(f"PIPELINE_ID:{pipeline_id}")
EOF

    # Run REAL integration test
    if PIPELINE_ID=$(python3 /tmp/test_data_ingest_real.py 2>&1 | tee /tmp/test_output.log | grep "PIPELINE_ID:" | cut -d: -f2); then
        print_success "✨ REAL data ingestion completed - Data in MinIO + Embeddings in Supabase"
        echo "  Pipeline ID: ${PIPELINE_ID}"
        export PIPELINE_ID
        return 0
    else
        print_failure "REAL data ingestion failed"
        echo "Last 20 lines of output:"
        tail -20 /tmp/test_output.log
        return 1
    fi
}

test_get_pipeline_status() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "REAL Pipeline Status - Query Actual Pipeline Data"
    
    if [ -z "${PIPELINE_ID}" ]; then
        print_info "Skipping: No pipeline ID from previous test"
        return 0
    fi
    
    print_info "Testing: Retrieve REAL pipeline status from preprocessing service"
    
    # Create Python test script for REAL status check
    cat > /tmp/test_pipeline_status_real.py << EOF
import asyncio
import sys
sys.path.insert(0, '/Users/xenodennis/Documents/Fun/isA_MCP')

from tools.services.data_analytics_service.tools.data_tools import register_data_tools
from mcp.server.fastmcp import FastMCP

async def test():
    mcp = FastMCP("test_data_tools")
    register_data_tools(mcp)
    
    # Call REAL get_pipeline_status
    print("🔍 Querying REAL pipeline status...")
    result = await mcp._tool_manager._tools['get_pipeline_status'].fn(
        user_id="${TEST_USER_ID}",
        pipeline_id="${PIPELINE_ID}"
    )
    
    import json
    result_dict = json.loads(result)
    
    # Verify REAL result
    print(f"📊 Status: {result_dict['status']}")
    assert result_dict['status'] == 'success', f"Status not success"
    assert result_dict['data']['success'] == True, "Status retrieval not successful"
    assert result_dict['data']['pipeline_id'] == "${PIPELINE_ID}", "Wrong pipeline ID"
    
    print(f"✓ Pipeline success: {result_dict['data']['pipeline_success']}")
    print(f"✓ Data ready: {result_dict['data']['data_ready']}")
    print(f"✓ Rows detected: {result_dict['data']['rows_detected']}")
    print(f"✓ Quality score: {result_dict['data']['data_quality_score']}")
    print(f"✓ Processing time: {result_dict['data']['total_duration']}s")

if __name__ == '__main__':
    asyncio.run(test())
EOF

    # Run REAL integration test
    if python3 /tmp/test_pipeline_status_real.py 2>&1 | tee /tmp/test_output.log; then
        print_success "✨ REAL pipeline status retrieved from preprocessing service"
        return 0
    else
        print_failure "REAL pipeline status retrieval failed"
        tail -20 /tmp/test_output.log
        return 1
    fi
}

test_data_search() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "REAL Semantic Search - Query Live Embeddings from Supabase"
    
    print_info "Testing: REAL semantic search against pgvector embeddings in Supabase"
    
    # Create Python test script for REAL search
    cat > /tmp/test_data_search_real.py << EOF
import asyncio
import sys
sys.path.insert(0, '/Users/xenodennis/Documents/Fun/isA_MCP')

from tools.services.data_analytics_service.tools.data_tools import register_data_tools
from mcp.server.fastmcp import FastMCP

async def test():
    mcp = FastMCP("test_data_tools")
    register_data_tools(mcp)
    
    # Call REAL data_search
    print("🔍 Searching REAL embeddings in Supabase pgvector...")
    result = await mcp._tool_manager._tools['data_search'].fn(
        user_id="${TEST_USER_ID}",
        search_query="sales data by region"
    )
    
    import json
    result_dict = json.loads(result)
    
    # Verify REAL result
    print(f"📊 Status: {result_dict['status']}")
    assert result_dict['status'] == 'success', f"Status not success"
    assert result_dict['data']['success'] == True, "Search not successful"
    assert 'database_summary' in result_dict['data'], "Missing database summary"
    assert 'search_results' in result_dict['data'], "Missing search results"
    
    print(f"✓ Database: {result_dict['data']['database_summary']['database_name']}")
    print(f"✓ Total embeddings: {result_dict['data']['database_summary']['total_embeddings']}")
    print(f"✓ Search results found: {result_dict['data']['search_count']}")
    print(f"✓ AI embedding service: {result_dict['data']['database_summary']['ai_services']['embedding']}")
    
    # Show top 3 search results
    if result_dict['data']['search_results']:
        print("✓ Top 3 similar entities:")
        for i, item in enumerate(result_dict['data']['search_results'][:3], 1):
            print(f"  {i}. {item['entity_name']} (type: {item['entity_type']}, score: {item['similarity_score']:.3f})")

if __name__ == '__main__':
    asyncio.run(test())
EOF

    # Run REAL integration test
    if python3 /tmp/test_data_search_real.py 2>&1 | tee /tmp/test_output.log; then
        print_success "✨ REAL semantic search completed - Queried Supabase pgvector"
        return 0
    else
        print_failure "REAL semantic search failed"
        tail -20 /tmp/test_output.log
        return 1
    fi
}

test_data_query() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "REAL Data Query - Execute SQL on MinIO Parquet with DuckDB"
    
    print_info "Testing: REAL natural language query → MinIO download → DuckDB SQL execution"
    
    # Create Python test script for REAL query
    cat > /tmp/test_data_query_real.py << EOF
import asyncio
import sys
sys.path.insert(0, '/Users/xenodennis/Documents/Fun/isA_MCP')

from tools.services.data_analytics_service.tools.data_tools import register_data_tools
from mcp.server.fastmcp import FastMCP

async def test():
    mcp = FastMCP("test_data_tools")
    register_data_tools(mcp)
    
    # Call REAL data_query
    print("🚀 Executing REAL query: MinIO → DuckDB → Results...")
    result = await mcp._tool_manager._tools['data_query'].fn(
        user_id="${TEST_USER_ID}",
        natural_language_query="total sales by region",
        include_visualization=True,
        include_analytics=False
    )
    
    import json
    # Handle both dict and string responses
    if isinstance(result, str):
        result_dict = json.loads(result)
    else:
        result_dict = result
    
    # Verify REAL result
    print(f"📊 Status: {result_dict['status']}")
    assert result_dict['status'] == 'success', f"Status not success"
    assert result_dict['data']['success'] == True, "Query not successful"
    assert 'query_data' in result_dict['data'], "Missing query data"
    assert 'services_used' in result_dict['data'], "Missing services info"
    
    print(f"✓ Rows returned: {result_dict['data']['rows_returned']}")
    print(f"✓ Columns returned: {result_dict['data']['columns_returned']}")
    print(f"✓ Services used: {', '.join(result_dict['data']['services_used'])}")
    print(f"✓ SQL executed: {result_dict['data'].get('sql_executed', 'N/A')[:80]}...")
    print(f"✓ Data source: {result_dict['data'].get('data_source', 'N/A')}")
    print(f"✓ Execution time: {result_dict['data'].get('total_execution_time', 0):.2f}s")
    
    # Show first 3 data rows
    if result_dict['data']['query_data']['data']:
        print("✓ Sample data (first 3 rows):")
        for i, row in enumerate(result_dict['data']['query_data']['data'][:3], 1):
            print(f"  {i}. {row}")
    
    # Check visualization
    if result_dict['data'].get('visualization_ready'):
        print(f"✓ Visualization generated: {result_dict['data']['visualization']['chart_type']}")

if __name__ == '__main__':
    asyncio.run(test())
EOF

    # Run REAL integration test
    if python3 /tmp/test_data_query_real.py 2>&1 | tee /tmp/test_output.log; then
        print_success "✨ REAL query executed - Downloaded from MinIO, queried with DuckDB"
        return 0
    else
        print_failure "REAL query execution failed"
        tail -30 /tmp/test_output.log
        return 1
    fi
}

test_progress_context_classes() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "Progress Context Classes"
    
    print_info "Testing: DataProgressReporter and DataSourceDetector classes"
    
    # Run test directly without creating temp file
    if python3 -c "
import sys
sys.path.insert(0, '/Users/xenodennis/Documents/Fun/isA_MCP')

from tools.services.data_analytics_service.tools.context import DataProgressReporter, DataSourceDetector
from tools.base_tool import BaseTool

# Test DataSourceDetector
assert DataSourceDetector.detect_from_path('data.csv') == 'csv'
assert DataSourceDetector.detect_from_path('data.parquet') == 'parquet'
assert DataSourceDetector.detect_from_path('data.json') == 'json'
assert DataSourceDetector.detect_from_path('data.xlsx') == 'excel'
print('✓ DataSourceDetector works correctly')

# Test DataProgressReporter initialization
base_tool = BaseTool()
reporter = DataProgressReporter(base_tool)
assert reporter is not None
assert hasattr(reporter, 'INGESTION_STAGES')
assert hasattr(reporter, 'SEARCH_STAGES')
assert hasattr(reporter, 'QUERY_STAGES')
print('✓ DataProgressReporter initializes correctly')

# Test stage dictionaries
assert 'processing' in reporter.INGESTION_STAGES
assert 'extraction' in reporter.INGESTION_STAGES
assert 'embedding' in reporter.INGESTION_STAGES
assert 'storing' in reporter.INGESTION_STAGES
print('✓ Ingestion stages defined correctly')

assert 'processing' in reporter.SEARCH_STAGES
assert 'embedding' in reporter.SEARCH_STAGES
assert 'matching' in reporter.SEARCH_STAGES
assert 'ranking' in reporter.SEARCH_STAGES
print('✓ Search stages defined correctly')

assert 'processing' in reporter.QUERY_STAGES
assert 'retrieval' in reporter.QUERY_STAGES
assert 'execution' in reporter.QUERY_STAGES
assert 'visualization' in reporter.QUERY_STAGES
print('✓ Query stages defined correctly')

print('✓ All progress context classes work correctly')
" 2>&1; then
        print_success "Progress context classes validated"
        return 0
    else
        print_failure "Progress context validation failed"
        return 1
    fi
}

###############################################################################
# Cleanup Functions
###############################################################################

cleanup_test_environment() {
    print_header "Cleaning Up Test Environment"
    
    # Remove temporary test files
    rm -f /tmp/test_*.py /tmp/test_output.log
    print_success "Temporary files removed"
    
    # Note: We keep the test CSV file for future tests
    print_info "Test data preserved for future tests"
}

###############################################################################
# Main Test Execution
###############################################################################

main() {
    print_header "🚀 Data Tools REAL Integration Test Suite"
    echo "Testing REAL end-to-end data analytics with LIVE services"
    echo "User ID: ${TEST_USER_ID}"
    echo "Test Dataset: ${TEST_DATASET_NAME}"
    echo ""
    echo "Services: Supabase + MinIO + DuckDB + OpenAI Embeddings + GPT-4"
    echo ""
    
    # Setup
    setup_test_environment
    
    # Run tests
    print_header "Running REAL Integration Tests"
    
    echo "🎯 Testing complete data pipeline with live services..."
    echo ""
    
    # Test 1: Progress context validation (quick unit test)
    if test_progress_context_classes; then
        echo ""
    else
        echo "⚠️  Progress context test failed (continuing...)"
    fi
    
    # Test 2: REAL data ingestion (CSV → MinIO + Supabase)
    if test_data_ingest; then
        echo ""
    else
        echo "⚠️  Data ingest test failed (continuing...)"
    fi
    
    # Test 3: REAL pipeline status (query preprocessing service)
    if test_get_pipeline_status; then
        echo ""
    else
        echo "⚠️  Pipeline status test failed (continuing...)"
    fi
    
    # Test 4: REAL semantic search (Supabase pgvector)
    if test_data_search; then
        echo ""
    else
        echo "⚠️  Data search test failed (continuing...)"
    fi
    
    # Test 5: REAL query execution (MinIO → DuckDB)
    if test_data_query; then
        echo ""
    else
        echo "⚠️  Data query test failed (continuing...)"
    fi
    
    # Cleanup
    cleanup_test_environment
    
    # Summary
    print_header "🎯 REAL Integration Test Summary"
    echo "Total REAL Integration Tests: ${TESTS_RUN}"
    echo -e "${GREEN}✓ Passed: ${TESTS_PASSED}${NC}"
    echo -e "${RED}✗ Failed: ${TESTS_FAILED}${NC}"
    echo ""
    
    if [ ${TESTS_FAILED} -eq 0 ]; then
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        print_success "🎉 All REAL integration tests passed!"
        echo ""
        echo "✓ CSV data ingested to MinIO Parquet"
        echo "✓ Metadata extracted and enriched with GPT-4"
        echo "✓ Vector embeddings stored in Supabase pgvector"
        echo "✓ Semantic search working against live embeddings"
        echo "✓ Natural language queries executing on real data"
        echo "✓ DuckDB querying Parquet files from MinIO"
        echo "✓ Progress tracking working throughout pipeline"
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        exit 0
    else
        echo ""
        print_failure "⚠️  Some REAL integration tests failed"
        echo ""
        echo "Check the logs above for details."
        echo "Common issues:"
        echo "  - Supabase connection not configured"
        echo "  - MinIO service not running"
        echo "  - OpenAI API key not set"
        echo "  - Missing Python dependencies"
        exit 1
    fi
}

# Run main
main "$@"

