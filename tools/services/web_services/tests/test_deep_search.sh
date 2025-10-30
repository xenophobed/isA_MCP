#!/bin/bash
# Deep Search Test Script
# Tests the new deep search functionality with multi-strategy fusion

echo "════════════════════════════════════════════════════════════════════════════════"
echo "🔬 DEEP SEARCH TEST - Multi-Strategy Web Search with Query Analysis"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

# Test 1: Simple technical query with deep search
echo "📝 Test 1: Technical Query (depth=2, auto RAG mode)"
echo "────────────────────────────────────────────────────────────────────────────────"
echo "Query: 'Python async programming'"
echo "Expected: Should detect TECHNICAL domain, recommend strategies"
echo ""

curl -s -X POST 'http://localhost:8081/mcp' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "id": 1,
    "params": {
      "name": "web_search",
      "arguments": {
        "query": "Python async programming",
        "user_id": "test_user_001",
        "deep_search": true,
        "depth": 2,
        "max_results_per_level": 5
      }
    }
  }' | while IFS= read -r line; do
    if [[ $line == data:* ]]; then
      data="${line#data: }"
      echo "$data" | python3 -c "
import sys
import json

data = json.load(sys.stdin)

if 'result' in data:
    content = data['result'].get('content', [])
    if content:
        response_text = content[0].get('text', '')
        try:
            response_data = json.loads(response_text)

            if response_data.get('status') == 'success':
                result = response_data.get('data', {})
                metadata = result.get('deep_search_metadata', {})
                profile = metadata.get('query_profile', {})

                print('✅ DEEP SEARCH SUCCESS')
                print('─' * 80)
                print(f'📊 Results: {result.get(\"total\", 0)}')
                print(f'⏱️  Execution time: {metadata.get(\"execution_time\", 0):.2f}s')
                print(f'🔄 Iterations: {metadata.get(\"depth_completed\", 0)}/{metadata.get(\"depth_completed\", 0)}')
                print()

                print('🧠 Query Analysis:')
                print(f'   Complexity: {profile.get(\"complexity\", \"unknown\").upper()}')
                print(f'   Domain: {profile.get(\"domain\", \"unknown\").upper()}')
                print(f'   Type: {profile.get(\"query_type\", \"unknown\").upper()}')
                print(f'   RAG Mode: {metadata.get(\"rag_mode\", \"unknown\").upper()}')
                print()

                print('🔍 Search Strategies Used:')
                for strategy in metadata.get('strategies_used', []):
                    print(f'   • {strategy}')
                print()

                print('📈 Iteration Details:')
                for iteration in metadata.get('iterations', []):
                    print(f'   Iteration {iteration[\"iteration\"]}: {iteration[\"results\"]} results')
                    print(f'     Query: \"{iteration[\"query\"]}\"')
                    print(f'     Strategies: {\" + \".join(iteration[\"strategies\"])}')
                print()

                print('🏆 Top 5 Fused Results:')
                for i, res in enumerate(result.get('results', [])[:5], 1):
                    print(f'   [{i}] {res[\"title\"][:70]}...')
                    print(f'       URL: {res[\"url\"]}')
                    print(f'       Fusion Score: {res[\"fusion_score\"]:.4f}')
                    print(f'       Found by: {\" + \".join(res[\"strategies\"])}')
                    print()
            else:
                print(f'❌ ERROR: {response_data.get(\"error\", \"Unknown error\")}')
        except Exception as e:
            print(f'❌ Parse error: {e}')
"
    fi
  done

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

# Test 2: Research query (higher complexity)
echo "📝 Test 2: Research Query (depth=2, should use plan_rag)"
echo "────────────────────────────────────────────────────────────────────────────────"
echo "Query: 'AI safety research landscape 2024'"
echo "Expected: HIGH complexity, ACADEMIC domain, RESEARCH type"
echo ""

curl -s -X POST 'http://localhost:8081/mcp' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "id": 2,
    "params": {
      "name": "web_search",
      "arguments": {
        "query": "AI safety research landscape 2024",
        "user_id": "researcher_001",
        "deep_search": true,
        "depth": 2,
        "max_results_per_level": 8
      }
    }
  }' | while IFS= read -r line; do
    if [[ $line == data:* ]]; then
      data="${line#data: }"
      echo "$data" | python3 -c "
import sys
import json

data = json.load(sys.stdin)

if 'result' in data:
    content = data['result'].get('content', [])
    if content:
        response_text = content[0].get('text', '')
        try:
            response_data = json.loads(response_text)

            if response_data.get('status') == 'success':
                result = response_data.get('data', {})
                metadata = result.get('deep_search_metadata', {})
                profile = metadata.get('query_profile', {})

                print('✅ DEEP SEARCH SUCCESS')
                print('─' * 80)
                print(f'📊 Results: {result.get(\"total\", 0)}')
                print(f'⏱️  Execution time: {metadata.get(\"execution_time\", 0):.2f}s')
                print()

                print('🧠 Query Analysis:')
                print(f'   Complexity: {profile.get(\"complexity\", \"unknown\").upper()}')
                print(f'   Domain: {profile.get(\"domain\", \"unknown\").upper()}')
                print(f'   Type: {profile.get(\"query_type\", \"unknown\").upper()}')
                print(f'   RAG Mode: {metadata.get(\"rag_mode\", \"unknown\").upper()}')
                print()

                # Show fusion stats
                if result.get('results'):
                    # Calculate multi-strategy results
                    multi_strategy = sum(1 for r in result['results'] if len(r.get('strategies', [])) > 1)
                    print('📊 Fusion Statistics:')
                    print(f'   Multi-strategy results: {multi_strategy}/{result.get(\"total\", 0)}')

                    # Strategy distribution
                    strategy_counts = {}
                    for res in result['results']:
                        for strategy in res.get('strategies', []):
                            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

                    print('   Strategy contribution:')
                    for strategy, count in sorted(strategy_counts.items(), key=lambda x: x[1], reverse=True):
                        percentage = (count / result.get('total', 1)) * 100
                        print(f'     • {strategy}: {count} results ({percentage:.1f}%)')
                print()

                print('🏆 Top 3 Multi-Strategy Results:')
                multi_strat = [r for r in result.get('results', []) if len(r.get('strategies', [])) > 1][:3]
                for i, res in enumerate(multi_strat, 1):
                    print(f'   [{i}] {res[\"title\"][:60]}...')
                    print(f'       Strategies: {\" + \".join(res[\"strategies\"])}')
                    print(f'       Fusion Score: {res[\"fusion_score\"]:.4f}')
                    print()
            else:
                print(f'❌ ERROR: {response_data.get(\"error\", \"Unknown error\")}')
        except Exception as e:
            print(f'❌ Parse error: {e}')
"
    fi
  done

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

# Test 3: Comparison query
echo "📝 Test 3: Comparison Query"
echo "────────────────────────────────────────────────────────────────────────────────"
echo "Query: 'Docker vs Kubernetes comparison'"
echo "Expected: COMPARISON type, TECHNICAL domain"
echo ""

curl -s -X POST 'http://localhost:8081/mcp' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "id": 3,
    "params": {
      "name": "web_search",
      "arguments": {
        "query": "Docker vs Kubernetes comparison",
        "user_id": "dev_001",
        "deep_search": true,
        "depth": 2,
        "max_results_per_level": 6
      }
    }
  }' | while IFS= read -r line; do
    if [[ $line == data:* ]]; then
      data="${line#data: }"
      echo "$data" | python3 -c "
import sys
import json

data = json.load(sys.stdin)

if 'result' in data:
    content = data['result'].get('content', [])
    if content:
        response_text = content[0].get('text', '')
        try:
            response_data = json.loads(response_text)

            if response_data.get('status') == 'success':
                result = response_data.get('data', {})
                metadata = result.get('deep_search_metadata', {})
                profile = metadata.get('query_profile', {})

                print('✅ DEEP SEARCH SUCCESS')
                print('─' * 80)
                print(f'📊 Results: {result.get(\"total\", 0)}')
                print(f'⏱️  Execution time: {metadata.get(\"execution_time\", 0):.2f}s')
                print()

                print('🧠 Query Analysis:')
                print(f'   Complexity: {profile.get(\"complexity\", \"unknown\").upper()}')
                print(f'   Domain: {profile.get(\"domain\", \"unknown\").upper()}')
                print(f'   Type: {profile.get(\"query_type\", \"unknown\").upper()} ← Should be COMPARISON')
                print(f'   RAG Mode: {metadata.get(\"rag_mode\", \"unknown\").upper()}')
                print()

                print('🏆 All Results:')
                for i, res in enumerate(result.get('results', []), 1):
                    print(f'   [{i}] {res[\"title\"][:65]}')
                    print(f'       Score: {res[\"fusion_score\"]:.4f} | Strategies: {len(res.get(\"strategies\", []))}')
                print()
            else:
                print(f'❌ ERROR: {response_data.get(\"error\", \"Unknown error\")}')
        except Exception as e:
            print(f'❌ Parse error: {e}')
"
    fi
  done

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "✅ DEEP SEARCH TEST COMPLETE"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""
echo "📊 Summary:"
echo "   • Deep search executes multiple search strategies in parallel"
echo "   • Query analyzer automatically classifies query complexity and domain"
echo "   • Reciprocal Rank Fusion (RRF) combines results from all strategies"
echo "   • Multi-strategy results (found by 2+ strategies) rank higher"
echo "   • Iterative refinement explores topic more deeply across iterations"
echo ""
