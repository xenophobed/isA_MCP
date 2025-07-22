#!/bin/bash

# Fix Cloud Migration Script
# This script creates a cleaner migration for cloud deployment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_MIGRATION="$SCRIPT_DIR/supabase/migrations/20250721214251_current_dev_complete.sql"
OUTPUT_FILE="$SCRIPT_DIR/universal_migrations/cloud_deployment_fixed.sql"

echo "Creating fixed cloud migration..."

# Create fixed migration
cat > "$OUTPUT_FILE" << 'EOF'
-- Fixed Cloud Deployment Migration
-- This version addresses UUID and schema reference issues

-- Enable required extensions first
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Set search path
SET search_path TO public;

EOF

# Process the source migration with better replacements
sed \
  -e 's/"dev"/"public"/g' \
  -e "s/'dev\./'public\./g" \
  -e 's/uuid_generate_v4()/gen_random_uuid()/g' \
  -e '/create schema if not exists/d' \
  -e '/ERROR:/d' \
  "$SOURCE_MIGRATION" | \
grep -v "schema.*does not exist" >> "$OUTPUT_FILE"

# Add footer
cat >> "$OUTPUT_FILE" << 'EOF'

-- Reset search path
RESET search_path;

-- Cloud deployment migration completed
EOF

echo "Fixed migration created: $OUTPUT_FILE"