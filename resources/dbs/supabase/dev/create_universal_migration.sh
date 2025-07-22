#!/bin/bash

# Universal Migration Generator
# This script creates schema-agnostic migrations from the complete dev migration

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_MIGRATION="$SCRIPT_DIR/supabase/migrations/20250721214251_current_dev_complete.sql"
OUTPUT_DIR="$SCRIPT_DIR/universal_migrations"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_blue() {
    echo -e "${BLUE}[MIGRATE]${NC} $1"
}

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo_info "Creating universal migrations from complete dev schema..."

# Function to create schema-agnostic migration
create_universal_migration() {
    local target_schema=$1
    local output_file="$OUTPUT_DIR/create_${target_schema}_schema.sql"
    
    echo_blue "Creating migration for: $target_schema"
    
    # Create header
    cat > "$output_file" << EOF
-- Universal Migration for $target_schema Schema
-- Generated from complete dev schema (43 tables)
-- This migration creates the complete isA MCP database structure
-- 
-- Usage: psql -f this_file.sql
-- Or: supabase migration apply (if using Supabase CLI)

-- Ensure target schema exists
CREATE SCHEMA IF NOT EXISTS $target_schema;

-- Grant permissions
GRANT ALL ON SCHEMA $target_schema TO postgres;
GRANT USAGE ON SCHEMA $target_schema TO anon, authenticated;

-- Set search path for this migration
SET search_path TO $target_schema, public;

EOF

    # Process the source migration and replace "dev" with target schema
    sed "s/\"dev\"/\"$target_schema\"/g" "$SOURCE_MIGRATION" | \
    sed "s/'dev\./'$target_schema\./g" | \
    grep -v "create schema if not exists" >> "$output_file"

    # Add footer
    cat >> "$output_file" << EOF

-- Reset search path
RESET search_path;

-- Migration completed for $target_schema schema
-- Total tables: 43
-- Includes: sequences, tables, indexes, foreign keys, and constraints
EOF

    echo_blue "Created: $output_file"
}

# Create migrations for different environments
create_universal_migration "test"
create_universal_migration "staging" 
create_universal_migration "production"

# Create a special version for cloud deployment
echo_blue "Creating cloud deployment migration..."
cat > "$OUTPUT_DIR/cloud_deployment.sql" << 'EOF'
-- Cloud Deployment Migration
-- This version uses 'public' schema for cloud deployments
-- where you don't need multiple schemas in the same database

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Set search path
SET search_path TO public;

EOF

# Add the complete structure but for public schema
sed "s/\"dev\"/\"public\"/g" "$SOURCE_MIGRATION" | \
sed "s/'dev\./'public\./g" | \
grep -v "create schema if not exists" >> "$OUTPUT_DIR/cloud_deployment.sql"

cat >> "$OUTPUT_DIR/cloud_deployment.sql" << 'EOF'

-- Reset search path
RESET search_path;

-- Cloud deployment migration completed
-- Schema: public (default for cloud)
-- Total tables: 43
EOF

echo_info "Universal migrations created in: $OUTPUT_DIR"
echo_info "Available migrations:"
ls -la "$OUTPUT_DIR"