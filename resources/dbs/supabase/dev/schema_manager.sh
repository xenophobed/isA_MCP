#!/bin/bash

# Schema Manager - Safe database schema management tool
# This script helps manage multiple schemas without affecting dev schema

DB_URL="postgresql://postgres:postgres@127.0.0.1:54322/postgres"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo_blue() {
    echo -e "${BLUE}[SCHEMA]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Schema Manager - Safe database schema management"
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  list                    - List all schemas and their tables"
    echo "  create <schema>         - Create a new schema with basic structure"
    echo "  sync <schema>           - Sync schema with dev structure (safe)"
    echo "  compare <schema>        - Compare schema with dev"
    echo "  backup <schema>         - Backup a schema"
    echo "  status                  - Show status of all schemas"
    echo ""
    echo "Examples:"
    echo "  $0 list"
    echo "  $0 create test"
    echo "  $0 sync staging"
    echo "  $0 compare test"
}

# Function to list all schemas
list_schemas() {
    echo_info "Listing all schemas and their tables:"
    echo ""
    
    for schema in dev test staging; do
        echo_blue "Schema: $schema"
        table_count=$(psql "$DB_URL" -t -c "\dt $schema.*" 2>/dev/null | wc -l | tr -d ' ' || echo "0")
        if [ "$table_count" -gt 0 ]; then
            psql "$DB_URL" -c "\dt $schema.*" 2>/dev/null || echo "  No tables found"
        else
            echo "  No tables found"
        fi
        echo ""
    done
}

# Function to create schema with basic structure
create_schema() {
    local schema_name=$1
    
    if [ -z "$schema_name" ]; then
        echo_error "Schema name required"
        return 1
    fi
    
    if [ "$schema_name" = "dev" ]; then
        echo_error "Cannot modify dev schema for safety"
        return 1
    fi
    
    echo_info "Creating schema: $schema_name"
    psql "$DB_URL" -v target_schema="$schema_name" -f "$SCRIPT_DIR/create_schema_template.sql"
}

# Function to sync schema with dev (read-only from dev)
sync_schema() {
    local schema_name=$1
    
    if [ -z "$schema_name" ]; then
        echo_error "Schema name required"
        return 1
    fi
    
    if [ "$schema_name" = "dev" ]; then
        echo_error "Cannot sync dev schema with itself"
        return 1
    fi
    
    echo_warn "This will recreate $schema_name schema based on dev structure"
    echo_warn "All data in $schema_name will be lost!"
    read -p "Continue? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo_info "Syncing $schema_name with dev structure..."
        # This would use the complete migration generated from dev
        psql "$DB_URL" -v target_schema="$schema_name" -f "$SCRIPT_DIR/create_schema_template.sql"
    else
        echo_info "Sync cancelled"
    fi
}

# Function to compare schemas
compare_schemas() {
    local schema_name=$1
    
    if [ -z "$schema_name" ]; then
        echo_error "Schema name required"
        return 1
    fi
    
    echo_info "Comparing $schema_name with dev:"
    
    echo_blue "Tables in dev:"
    psql "$DB_URL" -t -c "\dt dev.*" | awk '{print $3}' | sort
    echo ""
    
    echo_blue "Tables in $schema_name:"
    psql "$DB_URL" -t -c "\dt $schema_name.*" | awk '{print $3}' | sort
}

# Function to show status
show_status() {
    echo_info "Schema Status Report:"
    echo ""
    
    for schema in dev test staging; do
        echo_blue "Schema: $schema"
        table_count=$(psql "$DB_URL" -t -c "\dt $schema.*" 2>/dev/null | wc -l | tr -d ' ' || echo "0")
        echo "  Tables: $table_count"
        
        if [ "$table_count" -gt 0 ]; then
            echo "  Sample tables:"
            psql "$DB_URL" -t -c "\dt $schema.*" 2>/dev/null | head -3 | awk '{print "    - " $3}'
        fi
        echo ""
    done
}

# Main execution
case "${1:-help}" in
    "list")
        list_schemas
        ;;
    "create")
        create_schema "$2"
        ;;
    "sync")
        sync_schema "$2"
        ;;
    "compare")
        compare_schemas "$2"
        ;;
    "status")
        show_status
        ;;
    "help"|*)
        show_usage
        ;;
esac