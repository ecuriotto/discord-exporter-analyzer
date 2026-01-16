#!/bin/bash
# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Go to that directory
cd "$DIR"

# Check if .venv exists
if [ -d ".venv" ]; then
    echo "✅ Activating virtual environment..."
    source .venv/bin/activate
else
    echo "❌ Error: .venv not found!"
    exit 1
fi

# Run the server
echo "🚀 Starting Web Server..."
python -m uvicorn src.web.app:app --reload
