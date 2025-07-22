#!/bin/bash

# Script to extract dev schema structure and create migration
# This script is SAFE - it only reads from dev schema, never modifies it

DB_URL="postgresql://postgres:postgres@127.0.0.1:54322/postgres"
OUTPUT_FILE="current_dev_structure.sql"

echo "-- Current dev schema structure (READ-ONLY EXPORT)" > $OUTPUT_FILE
echo "-- Generated on: $(date)" >> $OUTPUT_FILE
echo "-- This file can be used to create the same structure in other schemas" >> $OUTPUT_FILE
echo "" >> $OUTPUT_FILE

echo "🔍 Extracting dev schema structure (READ-ONLY)..."

# Extract all table names from dev schema
echo "📋 Getting table list..."
psql "$DB_URL" -t -c "\dt dev.*" | awk '{print $3}' | grep -v "^$" > tables.tmp

# For each table, extract its structure
echo "📊 Extracting table structures..."
while read table; do
    if [ ! -z "$table" ]; then
        echo "-- Table: $table" >> $OUTPUT_FILE
        psql "$DB_URL" -c "\d dev.$table" >> $OUTPUT_FILE
        echo "" >> $OUTPUT_FILE
    fi
done < tables.tmp

# Extract sequences
echo "🔢 Extracting sequences..."
echo "-- Sequences in dev schema:" >> $OUTPUT_FILE
psql "$DB_URL" -c "\ds dev.*" >> $OUTPUT_FILE

# Extract indexes
echo "📇 Extracting indexes..."
echo "-- Indexes in dev schema:" >> $OUTPUT_FILE
psql "$DB_URL" -c "\di dev.*" >> $OUTPUT_FILE

# Clean up
rm -f tables.tmp

echo "✅ Dev schema structure extracted to: $OUTPUT_FILE"
echo "⚠️  This is a READ-ONLY export. Your dev schema was not modified."