#!/bin/bash
# Quick start script for web dashboard

echo "🚀 Starting Kalshi Trading Bot Web Dashboard..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create .env file from .env.example"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d .venv ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt
pip install -q -r webapp/requirements.txt

# Create necessary directories
mkdir -p logs data

# Start web application
echo "🌐 Starting web dashboard on http://localhost:5000"
echo "Press Ctrl+C to stop"
echo ""

python -m webapp.app

