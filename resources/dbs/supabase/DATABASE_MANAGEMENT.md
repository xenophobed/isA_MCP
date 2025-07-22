# Supabase Database Management Guide

## Overview

This guide documents the multi-environment database management strategy for the isA MCP project. The system is designed to maintain consistency across development, testing, staging, and production environments while protecting production data.

## Environment Strategy

```
Local Development → Local Testing → Cloud Staging → Cloud Production
       ↓                ↓             ↓               ↓
  Supabase Local   Supabase Local   Supabase Cloud   Supabase Cloud
   dev schema       test schema     staging project  production project
```

## Directory Structure

```
resources/dbs/supabase/
├── dev/                                    # Local development environment
│   ├── SHARED_INSTANCE_CONFIG.md          # Local Supabase connection details
│   ├── supabase/
│   │   ├── config.toml                    # Multi-schema configuration
│   │   ├── migrations/                    # All migration files
│   │   └── seed.sql                       # Seed data
│   ├── current_dev_structure.sql          # Current dev schema export
│   ├── create_schema_template.sql         # Universal schema template
│   ├── schema_manager.sh                  # Management tool
│   └── extract_dev_schema.sh              # Structure extraction tool
└── DATABASE_MANAGEMENT.md                 # This file
```

## Database Schemas

### Development Schema (`dev`)
- **Purpose**: Active development with real data
- **Tables**: 43 tables (current production-like structure)
- **Management**: Direct psql modifications + migration tracking
- **Protection**: Never modified by automation tools

### Test Schema (`test`)
- **Purpose**: Local testing with migration templates
- **Tables**: Subset for testing (currently 3 core tables)
- **Management**: Recreated from templates as needed
- **Data**: Test data only, frequently reset

### Staging Schema (`staging`)
- **Purpose**: Pre-production testing (will be Supabase Cloud)
- **Tables**: Mirror of production structure
- **Management**: Migration-only, no direct modifications
- **Data**: Production-like test data

### Production Schema (`production`)
- **Purpose**: Live production data (will be Supabase Cloud)
- **Tables**: Complete production structure
- **Management**: Migration-only with strict controls
- **Data**: Live user data

## Management Tools

### 1. Schema Manager (`schema_manager.sh`)

Universal tool for safe schema management:

```bash
# List all schemas and their status
./schema_manager.sh status

# Create a new schema with basic structure
./schema_manager.sh create test

# Sync schema with dev structure (destructive)
./schema_manager.sh sync staging

# Compare schemas
./schema_manager.sh compare test
```

### 2. Structure Extractor (`extract_dev_schema.sh`)

Safe read-only tool to export current dev schema structure:

```bash
# Extract current dev schema structure
./extract_dev_schema.sh
# Output: current_dev_structure.sql
```

### 3. Schema Template (`create_schema_template.sql`)

Universal template for creating consistent schema structure:

```bash
# Create test schema
psql -v target_schema=test -f create_schema_template.sql

# Create staging schema
psql -v target_schema=staging -f create_schema_template.sql
```

## Migration Strategy

### Current State
- **Dev Schema**: 43 tables, evolved through direct psql modifications
- **Generated Migration**: `20250721214251_current_dev_complete.sql` (2961 lines)
- **Template Migration**: Simplified version for new environments

### Best Practices
1. **All future changes must use migrations**
2. **Test migrations on test schema first**
3. **Never modify dev schema directly via tools**
4. **Always backup before major changes**

### Migration Workflow
```bash
# 1. Make changes in dev schema (manual psql if needed)
# 2. Generate migration from changes
supabase db diff -f new_feature_name

# 3. Test migration on test schema
psql -v target_schema=test -f new_migration.sql

# 4. Apply to staging (when ready)
# 5. Apply to production (with approval)
```

## Environment Configuration

### Local Development
```bash
# Connection Details
API_URL: http://127.0.0.1:54321
DB_URL: postgresql://postgres:postgres@127.0.0.1:54322/postgres
Studio: http://127.0.0.1:54323

# Environment Variables
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres
```

### Local Test Environment
```bash
# Same connection as dev, different schema
# Use target_schema=test in all operations
```

### Cloud Staging (Future)
```bash
# Will be separate Supabase Cloud project
SUPABASE_URL=https://staging-xxx.supabase.co
SUPABASE_ANON_KEY=<staging_anon_key>
SUPABASE_SERVICE_ROLE_KEY=<staging_service_key>
```

### Cloud Production (Future)
```bash
# Will be separate Supabase Cloud project
SUPABASE_URL=https://prod-xxx.supabase.co
SUPABASE_ANON_KEY=<prod_anon_key>
SUPABASE_SERVICE_ROLE_KEY=<prod_service_key>
```

## Key Tables Overview

### Core User Management
- `users` - User accounts and profiles
- `sessions` - User sessions and context
- `user_credit_transactions` - Credit system
- `subscriptions` - Subscription management

### MCP System
- `mcp_tools` - Available MCP tools
- `mcp_resources` - MCP resources
- `mcp_prompts` - Prompt templates
- `mcp_unified_search_embeddings` - Search system

### Memory System
- `episodic_memories` - User experiences
- `factual_memories` - Facts and information
- `semantic_memories` - Concepts and relationships
- `procedural_memories` - How-to knowledge
- `working_memories` - Current context
- `session_memories` - Session-specific data

### AI & Models
- `models` - AI model configurations
- `model_embeddings` - Model embeddings
- `model_statistics` - Performance metrics

### Tracing & Analytics
- `traces` - Distributed tracing
- `spans` - Trace spans
- `span_logs` - Detailed logs
- `events` - System events

### E-commerce
- `carts` - Shopping carts
- `orders` - Order management

## Safety Protocols

### Development Schema Protection
1. **Never run automated tools on dev schema**
2. **Always backup before structural changes**
3. **Use schema_manager.sh for safe operations**
4. **Test all changes on test schema first**

### Migration Safety
1. **Always review generated migrations**
2. **Test migrations on non-production first**
3. **Backup production before applying**
4. **Have rollback plan ready**

### Data Protection
1. **Production data never leaves production**
2. **Use anonymized data for testing**
3. **Regular backups of all environments**
4. **Access controls on production**

## Troubleshooting

### Common Issues

#### Migration Conflicts
```bash
# If migrations conflict, check current state
./schema_manager.sh status

# Compare with expected state
./schema_manager.sh compare staging
```

#### Schema Inconsistencies
```bash
# Extract current structure
./extract_dev_schema.sh

# Review differences in current_dev_structure.sql
# Generate corrective migration if needed
```

#### Connection Issues
```bash
# Check Supabase status
supabase status

# Restart if needed
supabase stop && supabase start
```

## Next Steps

1. **Complete Migration Generation**: Create full 43-table migration from dev
2. **Cloud Project Setup**: Create staging and production Supabase projects
3. **CI/CD Integration**: Automate migration deployment
4. **Monitoring Setup**: Track schema changes and performance
5. **Backup Strategy**: Implement automated backups

## References

- [Supabase CLI Documentation](https://supabase.com/docs/guides/cli)
- [Migration Best Practices](https://supabase.com/docs/guides/local-development/migrations)
- [Multi-Environment Setup](https://supabase.com/docs/guides/local-development/environments)