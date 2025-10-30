#!/bin/bash
###############################################################################
# Example: Test Custom RAG Service
###############################################################################

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DIAGNOSTIC_SCRIPT="$SCRIPT_DIR/../run_diagnostic.sh"

echo "Testing Custom RAG Service..."
echo ""

# Test with Chinese medical query
$DIAGNOSTIC_SCRIPT \
    --service custom_rag \
    --user test_user_rag_page \
    --query "乙肝可以存干细胞么" \
    --top-k 5 \
    --model gpt-4o-mini \
    --output /tmp/custom_rag_diagnostic.json \
    --verbose

echo ""
echo "Report saved to: /tmp/custom_rag_diagnostic.json"
