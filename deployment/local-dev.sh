#!/bin/bash
# =============================================================================
# Local Development Script - isA_MCP
# =============================================================================
set -e

PROJECT_NAME="isa_mcp"
SERVICE_PORT="8081"
MAIN_MODULE="main:app"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

case "${1:-}" in
    --setup)
        echo "Setting up $PROJECT_NAME..."

        # Create venv
        rm -rf .venv
        uv venv .venv --python 3.12

        # Install base (ISA packages editable) + project packages
        uv pip install -r deployment/requirements/base_dev.txt --python .venv/bin/python
        uv pip install -r deployment/requirements/project.txt --python .venv/bin/python

        # Install isA_Vibe (agent framework) - editable for development
        ISA_VIBE_PATH="$PROJECT_ROOT/../isA_Vibe"
        if [ -d "$ISA_VIBE_PATH" ]; then
            echo "Installing isA_Vibe from $ISA_VIBE_PATH..."
            uv pip install -e "$ISA_VIBE_PATH" --python .venv/bin/python
        else
            echo "Warning: isA_Vibe not found at $ISA_VIBE_PATH, skipping..."
        fi

        # Services are natively accessible via Kind NodePort mappings (no port-forward needed)
        # PostgreSQL: localhost:5432  |  Redis: localhost:6379    |  Qdrant: localhost:6333/6334
        # MinIO: localhost:9000/9001  |  Neo4j: localhost:7474/7687  |  NATS: localhost:4222
        # MQTT (EMQX): localhost:1883 |  Consul: localhost:8500   |  APISIX: localhost:9080/9180

        echo "Setup complete! Run: $0 --run"
        ;;
    --run)
        # Kill existing process on port
        lsof -ti:$SERVICE_PORT | xargs kill -9 2>/dev/null || true
        source deployment/environments/dev.env 2>/dev/null || true
        .venv/bin/python -m uvicorn $MAIN_MODULE --host 0.0.0.0 --port $SERVICE_PORT --reload
        ;;
    --status)
        echo "Venv: .venv"
        echo "=== ISA Packages ==="
        uv pip list --python .venv/bin/python 2>/dev/null | grep -E "isa-|claude-agent" || echo "Not installed"
        ;;
    *)
        # Full setup + run
        $0 --setup
        $0 --run
        ;;
esac
