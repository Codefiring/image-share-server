#!/bin/bash

# Image Share Server Startup Script

echo "Starting Image Share Server..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -q -r requirements.txt

# Run the server
echo "Server starting at http://0.0.0.0:5000"
echo "Press Ctrl+C to stop"
python app.py
