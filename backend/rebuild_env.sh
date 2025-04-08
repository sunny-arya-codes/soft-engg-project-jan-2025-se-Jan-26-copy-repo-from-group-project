#!/bin/bash

# This script rebuilds the virtual environment from scratch, 
# installs all dependencies, and starts the application

set -e

echo "Removing old virtual environment..."
rm -rf .venv

echo "Creating new virtual environment..."
python -m venv .venv

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Environment setup complete!"
echo "Starting application..."
python -m uvicorn main:app --reload

# To run this script: 
# chmod +x rebuild_env.sh
# ./rebuild_env.sh 