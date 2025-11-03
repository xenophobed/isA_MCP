#!/bin/bash

# CRAG RAG Test via MCP Interface
# Tests CRAG quality-aware storage and retrieval through real infrastructure

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         CRAG RAG MCP Integration Test                          ║"
echo "║         Testing Quality-Aware RAG via MCP Interface            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Test configuration
MCP_URL="http://localhost:8081/mcp"
TEST_USER="CRAG_MCP_TEST"
OUTPUT_DIR="/tmp"

echo "📝 Test Configuration:"
echo "   MCP URL: $MCP_URL"
echo "   Test User: $TEST_USER"
echo "   RAG Mode: crag (quality-aware)"
echo ""

# Function to call MCP
call_mcp() {
    local tool_name=$1
    local arguments=$2
    local test_name=$3

    echo "─────────────────────────────────────────────────────────────────"
    echo "🧪 Test: $test_name"
    echo "   Tool: $tool_name"
    echo "─────────────────────────────────────────────────────────────────"

    curl -s -X POST "$MCP_URL" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"id\": $RANDOM,
            \"method\": \"tools/call\",
            \"params\": {
                \"name\": \"$tool_name\",
                \"arguments\": $arguments
            }
        }" | tee "${OUTPUT_DIR}/crag_${tool_name}_output.txt"

    echo ""
    echo ""
}

echo "════════════════════════════════════════════════════════════════"
echo "Phase 1: Store Content with CRAG Quality Assessment"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Test 1: Store high-quality content
echo "📤 Test 1.1: Storing HIGH-QUALITY content (should score >= 0.7)"
call_mcp "store_knowledge" \
    "{
        \"user_id\": \"$TEST_USER\",
        \"content\": \"Machine Learning is a subset of artificial intelligence that enables computers to learn from data without being explicitly programmed. It uses statistical techniques to identify patterns and make predictions based on historical data.\",
        \"content_type\": \"text\",
        \"options\": {
            \"rag_mode\": \"crag\"
        }
    }" \
    "Store high-quality content with CRAG"

# Test 2: Store medium-quality content
echo "📤 Test 1.2: Storing MEDIUM-QUALITY content (should score 0.4-0.7)"
call_mcp "store_knowledge" \
    "{
        \"user_id\": \"$TEST_USER\",
        \"content\": \"Neural networks are computational models inspired by biological neural networks\",
        \"content_type\": \"text\",
        \"options\": {
            \"rag_mode\": \"crag\"
        }
    }" \
    "Store medium-quality content with CRAG"

# Test 3: Store low-quality content
echo "📤 Test 1.3: Storing LOW-QUALITY content (should score < 0.4)"
call_mcp "store_knowledge" \
    "{
        \"user_id\": \"$TEST_USER\",
        \"content\": \"AI is cool\",
        \"content_type\": \"text\",
        \"options\": {
            \"rag_mode\": \"crag\"
        }
    }" \
    "Store low-quality content with CRAG"

echo "⏳ Waiting 3 seconds for indexing..."
sleep 3

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "Phase 2: Retrieve with CRAG Quality Classification"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Test 4: Search with quality classification
echo "🔍 Test 2.1: Search with CRAG quality classification"
call_mcp "search_knowledge" \
    "{
        \"user_id\": \"$TEST_USER\",
        \"query\": \"What is Machine Learning and how does it work?\",
        \"top_k\": 5,
        \"options\": {
            \"rag_mode\": \"crag\"
        }
    }" \
    "Search with CRAG quality filtering"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "Phase 3: Generate Response with CRAG"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Test 5: Generate response with CRAG
echo "💬 Test 3.1: Generate quality-aware response with CRAG"
call_mcp "knowledge_response" \
    "{
        \"user_id\": \"$TEST_USER\",
        \"query\": \"Explain Machine Learning to me\",
        \"response_options\": {
            \"rag_mode\": \"crag\",
            \"context_limit\": 3,
            \"enable_citations\": true
        }
    }" \
    "Generate response with CRAG quality awareness"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "Test Results Analysis"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Analyze outputs
echo "📊 Analyzing CRAG test outputs..."
echo ""

# Check for quality metrics
echo "🔍 Checking for CRAG quality metrics in outputs:"
if grep -q "quality_assessment\|quality_score" "${OUTPUT_DIR}/crag_store_knowledge_output.txt" 2>/dev/null; then
    echo "   ✅ Quality assessment found in store results"
else
    echo "   ⚠️  Quality assessment not found in store results (stored in backend)"
fi

if grep -q "quality_assessment\|quality_level" "${OUTPUT_DIR}/crag_search_knowledge_output.txt" 2>/dev/null; then
    echo "   ✅ Quality classification found in search results"
else
    echo "   ⚠️  Quality classification not found in search results"
fi

# Check for CRAG mode usage
echo ""
echo "🔍 Verifying CRAG mode was used:"
if grep -q "rag_mode_used.*crag\|\"rag_mode\": \"crag\"" "${OUTPUT_DIR}/crag_knowledge_response_output.txt" 2>/dev/null; then
    echo "   ✅ CRAG mode confirmed in outputs"
else
    echo "   ⚠️  CRAG mode not found in outputs"
fi

# Extract quality scores if present
echo ""
echo "📈 Quality Scores (if available):"
grep -o "quality[^,}]*" "${OUTPUT_DIR}/crag_"*.txt 2>/dev/null | head -10 || echo "   (Quality scores may be in structured content)"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "Test Complete!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "📁 Output files saved to:"
echo "   ${OUTPUT_DIR}/crag_*.txt"
echo ""
echo "🔍 To view detailed results:"
echo "   cat ${OUTPUT_DIR}/crag_store_knowledge_output.txt"
echo "   cat ${OUTPUT_DIR}/crag_search_knowledge_output.txt"
echo "   cat ${OUTPUT_DIR}/crag_knowledge_response_output.txt"
echo ""
