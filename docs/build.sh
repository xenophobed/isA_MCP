#!/bin/bash

# isA_MCP Documentation Build Script
# This script builds the GitBook documentation

set -e

echo "🚀 Building isA_MCP Documentation"
echo "================================="

# Check if GitBook CLI is installed
if ! command -v gitbook &> /dev/null; then
    echo "❌ GitBook CLI not found. Installing..."
    npm install -g gitbook-cli
fi

# Navigate to docs directory
cd "$(dirname "$0")"

echo "📦 Installing GitBook plugins..."
gitbook install

echo "🔧 Building documentation..."
gitbook build

echo "📄 Generating PDF documentation..."
gitbook pdf . ./isA_MCP_Documentation.pdf

echo "✅ Documentation build completed!"
echo ""
echo "📚 Documentation locations:"
echo "   - HTML: ./_book/index.html"
echo "   - PDF:  ./isA_MCP_Documentation.pdf"
echo ""
echo "🌐 To serve locally:"
echo "   gitbook serve"
echo ""
echo "🚀 To deploy:"
echo "   - GitHub Pages: Copy _book/ contents to gh-pages branch"
echo "   - Netlify: Deploy _book/ directory"
echo "   - Vercel: Deploy _book/ directory"