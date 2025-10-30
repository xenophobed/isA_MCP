#!/bin/bash
###############################################################################
# RAG System Diagnostic Runner
#
# Universal diagnostic script for all RAG patterns and pipelines
#
# Usage:
#   ./run_diagnostic.sh [OPTIONS]
#
# Options:
#   -s, --service <service>    RAG service to test (default: custom_rag)
#                              Options: custom_rag, simple_rag, crag, self_rag,
#                                       raptor, plan_rag, hm_rag, graph_rag
#   -u, --user <user_id>       User ID for testing (default: test_user)
#   -q, --query <query>        Query to test (default: "Sample query")
#   -k, --top-k <number>       Number of results to retrieve (default: 5)
#   -m, --model <model>        LLM model for evaluation (default: gpt-4o-mini)
#   -v, --verbose              Verbose output
#   -o, --output <file>        Save report to file (JSON format)
#   -h, --help                 Show this help message
#
# Examples:
#   # Test custom RAG service
#   ./run_diagnostic.sh -s custom_rag -u test_user -q "乙肝可以存干细胞么"
#
#   # Test multiple services
#   ./run_diagnostic.sh -s simple_rag -q "What is CRM?"
#
#   # Save report to file
#   ./run_diagnostic.sh -s custom_rag -u test_user -o report.json
#
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
SERVICE="custom_rag"
USER_ID="test_user"
QUERY="Sample query for testing RAG system"
TOP_K=5
MODEL="gpt-4o-mini"
VERBOSE=false
OUTPUT_FILE=""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../../../../../.." && pwd )"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--service)
            SERVICE="$2"
            shift 2
            ;;
        -u|--user)
            USER_ID="$2"
            shift 2
            ;;
        -q|--query)
            QUERY="$2"
            shift 2
            ;;
        -k|--top-k)
            TOP_K="$2"
            shift 2
            ;;
        -m|--model)
            MODEL="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -h|--help)
            grep "^#" "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Print header
echo -e "${BLUE}================================================================================================${NC}"
echo -e "${BLUE}                          RAG SYSTEM DIAGNOSTIC RUNNER${NC}"
echo -e "${BLUE}================================================================================================${NC}"
echo ""
echo -e "${GREEN}Configuration:${NC}"
echo -e "  Service:   ${YELLOW}$SERVICE${NC}"
echo -e "  User ID:   ${YELLOW}$USER_ID${NC}"
echo -e "  Query:     ${YELLOW}$QUERY${NC}"
echo -e "  Top-K:     ${YELLOW}$TOP_K${NC}"
echo -e "  Model:     ${YELLOW}$MODEL${NC}"
echo -e "  Verbose:   ${YELLOW}$VERBOSE${NC}"
[[ -n "$OUTPUT_FILE" ]] && echo -e "  Output:    ${YELLOW}$OUTPUT_FILE${NC}"
echo ""

# Create Python runner script
PYTHON_SCRIPT=$(cat <<EOF
import asyncio
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path("$PROJECT_ROOT")
sys.path.insert(0, str(project_root))

from tools.services.data_analytics_service.services.digital_service.evaluation.diagnostic_service import (
    RAGDiagnosticService
)

# Service registry - map service names to their implementations
SERVICE_REGISTRY = {
    'custom_rag': 'tools.services.data_analytics_service.services.digital_service.patterns.custom_rag_service',
    'simple_rag': 'tools.services.data_analytics_service.services.digital_service.patterns.simple_rag_service',
    'crag': 'tools.services.data_analytics_service.services.digital_service.patterns.crag_service',
    'self_rag': 'tools.services.data_analytics_service.services.digital_service.patterns.self_rag_service',
    'raptor': 'tools.services.data_analytics_service.services.digital_service.patterns.raptor_service',
    'plan_rag': 'tools.services.data_analytics_service.services.digital_service.patterns.plan_rag_service',
    'hm_rag': 'tools.services.data_analytics_service.services.digital_service.patterns.hm_rag_service',
    'graph_rag': 'tools.services.data_analytics_service.services.digital_service.patterns.graph_rag_service',
}

async def load_rag_service(service_name):
    """Dynamically load RAG service"""
    if service_name not in SERVICE_REGISTRY:
        print(f"❌ Error: Unknown service '{service_name}'")
        print(f"Available services: {', '.join(SERVICE_REGISTRY.keys())}")
        sys.exit(1)

    module_path = SERVICE_REGISTRY[service_name]

    try:
        # Import module dynamically
        module_parts = module_path.split('.')
        module = __import__(module_path, fromlist=[module_parts[-1]])

        # Try common getter patterns
        getter_names = [
            f'get_{service_name}_service',
            f'get_{service_name}',
            'get_service',
            f'{service_name.replace("_", "").title()}Service'
        ]

        service = None
        for getter_name in getter_names:
            if hasattr(module, getter_name):
                attr = getattr(module, getter_name)
                if callable(attr):
                    service = attr()
                    break

        if service is None:
            # Try to find a class with 'Service' suffix
            for name in dir(module):
                if name.endswith('Service') and not name.startswith('_'):
                    cls = getattr(module, name)
                    if callable(cls):
                        service = cls()
                        break

        if service is None:
            print(f"❌ Error: Could not instantiate service from {module_path}")
            sys.exit(1)

        return service

    except ImportError as e:
        print(f"❌ Error: Could not import {module_path}: {e}")
        print(f"This service may not be implemented yet.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading service: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

async def main():
    # Configuration from shell variables
    service_name = "$SERVICE"
    user_id = "$USER_ID"
    query = """$QUERY"""
    top_k = int("$TOP_K")
    model = "$MODEL"
    verbose = "$VERBOSE" == "true"
    output_file = "$OUTPUT_FILE"

    try:
        # Load RAG service
        print(f"🔧 Loading {service_name} service...")
        rag_service = await load_rag_service(service_name)
        print(f"✅ Service loaded successfully")
        print()

        # Initialize diagnostic service
        diagnostic_service = RAGDiagnosticService(model=model)

        # Run diagnostic
        report = await diagnostic_service.run_full_diagnostic(
            rag_service=rag_service,
            user_id=user_id,
            query=query,
            top_k=top_k
        )

        # Save report if requested
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"\\n💾 Report saved to: {output_file}")

        # Return exit code based on overall status
        if report['overall_status'] == 'pass':
            sys.exit(0)
        elif report['overall_status'] == 'warning':
            sys.exit(1)
        else:
            sys.exit(2)

    except Exception as e:
        print(f"\\n❌ Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(3)

if __name__ == "__main__":
    asyncio.run(main())
EOF
)

# Run Python script
cd "$PROJECT_ROOT"

if [ "$VERBOSE" = true ]; then
    echo -e "${BLUE}Running diagnostic...${NC}"
    echo ""
fi

echo "$PYTHON_SCRIPT" | python3

# Capture exit code
EXIT_CODE=$?

# Print result summary
echo ""
echo -e "${BLUE}================================================================================================${NC}"
case $EXIT_CODE in
    0)
        echo -e "${GREEN}✅ DIAGNOSTIC PASSED${NC}"
        ;;
    1)
        echo -e "${YELLOW}⚠️  DIAGNOSTIC WARNING${NC}"
        ;;
    2)
        echo -e "${RED}❌ DIAGNOSTIC FAILED${NC}"
        ;;
    *)
        echo -e "${RED}❌ DIAGNOSTIC ERROR${NC}"
        ;;
esac
echo -e "${BLUE}================================================================================================${NC}"

exit $EXIT_CODE
