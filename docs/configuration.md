# Configuration

ISA MCP uses a layered configuration approach:

- **`config/init.yaml`** -- Service definitions, auto-discovery settings, startup order
- **`.env` files** -- Environment-specific variables (`deployment/dev/.env`, etc.)
- **Environment variables** -- Runtime overrides (highest priority)

## Detailed Guides

- [Server & Infrastructure Configuration](./guidance/configuration.md) -- YAML configs, service dependencies, startup order, directory structure
- [Environment Variables Reference](./env/README.md) -- All env vars with defaults, profiles, validation rules
- [Deployment Configuration](./deployment.md) -- K8s health checks, resource requirements, scaling
