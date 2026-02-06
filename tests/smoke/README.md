# E2E Tests

End-to-end shell scripts for manual testing and CI/CD integration.

## Purpose

These scripts test the full system without mocks, useful for:
- Smoke tests after deployment
- Manual verification during development
- CI/CD pipeline integration tests

## Structure

```
e2e/
├── api/              # MCP protocol tests
├── cache/            # Redis caching tests
├── tool_calling/     # LLM tool calling tests
└── voice/            # Audio pipeline tests
```

## Running Tests

```bash
# Make scripts executable
chmod +x tests/e2e/**/*.sh

# Run individual test
./tests/e2e/api/test_mcp_protocol.sh

# Run all e2e tests
for script in tests/e2e/**/*.sh; do
    echo "Running $script..."
    bash "$script"
done
```

## Prerequisites

- MCP server running locally or specify `MCP_URL` environment variable
- Required services (PostgreSQL, Qdrant, Redis) available
- API keys configured in environment

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_URL` | `http://localhost:8000` | MCP server URL |
| `MCP_API_KEY` | - | API key for authentication |
| `VERBOSE` | `false` | Enable verbose output |

## Adding New Tests

1. Create a new `.sh` file in the appropriate directory
2. Include proper error handling (`set -e`)
3. Use environment variables for configuration
4. Return exit code 0 for success, non-zero for failure
