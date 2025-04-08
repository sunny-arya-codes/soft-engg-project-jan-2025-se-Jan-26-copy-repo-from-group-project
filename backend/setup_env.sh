#!/bin/bash

# Set up a Python virtual environment and install dependencies

# Create virtual environment
echo "Creating virtual environment in ./venv..."
python -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo "Environment setup complete. To activate, run:"
echo "source venv/bin/activate" 