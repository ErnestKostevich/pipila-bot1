#!/bin/bash
# 🚀 PIPILA - Start Script
# This script GUARANTEES documents download before bot starts

set -e  # Exit on any error

echo "========================================================================"
echo "🚀 PIPILA START SCRIPT"
echo "========================================================================"
echo ""

# Step 1: Download documents
echo "📥 Step 1: Downloading documents from Dropbox..."
python download_gdrive_recursive.py

# Check if documents exist
if [ ! -d "./documents" ]; then
    echo "❌ ERROR: Documents folder not created!"
    exit 1
fi

# Count files
FILE_COUNT=$(find ./documents -type f \( -name "*.pdf" -o -name "*.docx" -o -name "*.txt" \) | wc -l)
echo "✅ Documents ready: $FILE_COUNT files"

if [ "$FILE_COUNT" -eq 0 ]; then
    echo "⚠️ WARNING: No documents found, but continuing..."
fi

echo ""
echo "========================================================================"
echo "🤖 Step 2: Starting PIPILA bot..."
echo "========================================================================"
echo ""

# Step 2: Start bot
exec python pipila_bot.py
