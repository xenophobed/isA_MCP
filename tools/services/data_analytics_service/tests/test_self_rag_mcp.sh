#!/bin/bash

# Self-RAG MCP Integration Test
# Tests self-reflection and iterative refinement through real infrastructure

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         Self-RAG MCP Integration Test                          ║"
echo "║         Testing Self-Reflection RAG via MCP Interface          ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Test configuration
MCP_URL="http://localhost:8081/mcp"
TEST_USER="SELF_RAG_MCP_TEST"
OUTPUT_DIR="/tmp"

echo "📝 Test Configuration:"
echo "   MCP URL: $MCP_URL"
echo "   Test User: $TEST_USER"
echo "   RAG Mode: self_rag (self-reflection)"
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
        }" | tee "${OUTPUT_DIR}/self_rag_${tool_name}_output.txt"

    echo ""
    echo ""
}

echo "════════════════════════════════════════════════════════════════"
echo "Phase 1: Store Content for Self-RAG"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Test 1: Store comprehensive content
echo "📤 Test 1.1: Storing comprehensive content for self-reflection"
call_mcp "store_knowledge" \
    "{
        \"user_id\": \"$TEST_USER\",
        \"content\": \"Deep Learning is a subset of machine learning based on artificial neural networks with multiple layers. Deep learning models can automatically learn hierarchical representations from data, making them particularly effective for tasks like image recognition, natural language processing, and speech recognition. The key advantage of deep learning is its ability to learn features automatically without manual feature engineering.\",
        \"content_type\": \"text\",
        \"options\": {
            \"rag_mode\": \"self_rag\"
        }
    }" \
    "Store comprehensive content with Self-RAG"

# Test 2: Store incomplete content (to trigger refinement)
echo "📤 Test 1.2: Storing incomplete content (may trigger refinement)"
call_mcp "store_knowledge" \
    "{
        \"user_id\": \"$TEST_USER\",
        \"content\": \"Neural networks process information through connected nodes called neurons.\",
        \"content_type\": \"text\",
        \"options\": {
            \"rag_mode\": \"self_rag\"
        }
    }" \
    "Store incomplete content with Self-RAG"

echo "⏳ Waiting 3 seconds for indexing..."
sleep 3

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "Phase 2: Retrieve with Self-Assessment"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Test 3: Search with self-assessment
echo "🔍 Test 2.1: Search with Self-RAG self-assessment"
call_mcp "search_knowledge" \
    "{
        \"user_id\": \"$TEST_USER\",
        \"query\": \"What is Deep Learning and how does it differ from traditional machine learning?\",
        \"top_k\": 5,
        \"options\": {
            \"rag_mode\": \"self_rag\"
        }
    }" \
    "Search with Self-RAG self-assessment"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "Phase 3: Generate with Self-Reflection"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Test 4: Generate response with self-reflection
echo "💬 Test 3.1: Generate response with self-reflection and refinement"
call_mcp "knowledge_response" \
    "{
        \"user_id\": \"$TEST_USER\",
        \"query\": \"Explain Deep Learning in detail and how it works\",
        \"response_options\": {
            \"rag_mode\": \"self_rag\",
            \"context_limit\": 3,
            \"enable_citations\": true
        }
    }" \
    "Generate response with Self-RAG reflection"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "Test Results Analysis"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Analyze outputs
echo "📊 Analyzing Self-RAG test outputs..."
echo ""

# Check for self-reflection metrics
echo "🔍 Checking for Self-RAG features in outputs:"
if grep -q "self_reflection_used\|refinement_performed\|quality_score" "${OUTPUT_DIR}/self_rag_knowledge_response_output.txt" 2>/dev/null; then
    echo "   ✅ Self-reflection features found in response"
else
    echo "   ⚠️  Self-reflection features not found in response"
fi

if grep -q "self_rag_mode\|self_assessed" "${OUTPUT_DIR}/self_rag_search_knowledge_output.txt" 2>/dev/null; then
    echo "   ✅ Self-RAG mode confirmed in search results"
else
    echo "   ⚠️  Self-RAG mode not found in search results"
fi

# Check for Self-RAG mode usage
echo ""
echo "🔍 Verifying Self-RAG mode was used:"
if grep -q "rag_mode_used.*self_rag\|\"rag_mode\": \"self_rag\"" "${OUTPUT_DIR}/self_rag_knowledge_response_output.txt" 2>/dev/null; then
    echo "   ✅ Self-RAG mode confirmed in outputs"
else
    echo "   ⚠️  Self-RAG mode not found in outputs"
fi

# Extract self-reflection metrics if present
echo ""
echo "📈 Self-Reflection Metrics (if available):"
grep -o "refinement_performed[^,}]*\|quality_score[^,}]*\|self_reflection_used[^,}]*" "${OUTPUT_DIR}/self_rag_"*.txt 2>/dev/null | head -10 || echo "   (Reflection metrics may be in structured content)"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "Test Complete!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "📁 Output files saved to:"
echo "   ${OUTPUT_DIR}/self_rag_*.txt"
echo ""
echo "🔍 To view detailed results:"
echo "   cat ${OUTPUT_DIR}/self_rag_store_knowledge_output.txt"
echo "   cat ${OUTPUT_DIR}/self_rag_search_knowledge_output.txt"
echo "   cat ${OUTPUT_DIR}/self_rag_knowledge_response_output.txt"
echo ""
