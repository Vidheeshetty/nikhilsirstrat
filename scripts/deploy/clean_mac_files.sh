#!/bin/bash

# Clean Mac hidden files from catalog-data to prevent parquet corruption
# These ._* files can corrupt Nautilus Trader's parquet reading

echo "🧹 Cleaning Mac hidden files from catalog-data..."

# Find and remove all Mac resource fork files
find catalog-data -name '._*' -type f -delete 2>/dev/null || true

# Find and remove .DS_Store files
find catalog-data -name '.DS_Store' -type f -delete 2>/dev/null || true

# Count remaining files
REMAINING=$(find catalog-data -name '._*' -o -name '.DS_Store' | wc -l)

if [ "$REMAINING" -eq 0 ]; then
    echo "✅ All Mac hidden files removed successfully"
else
    echo "⚠️  Warning: $REMAINING Mac hidden files still remain"
fi

echo "📊 Catalog data structure:"
find catalog-data -name "*.parquet" | head -5 