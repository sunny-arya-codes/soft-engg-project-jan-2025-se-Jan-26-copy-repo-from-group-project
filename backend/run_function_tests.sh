#!/bin/bash

# Script to run the function calling tests

echo "=============================================="
echo "  Running API Function Calling Tests"
echo "=============================================="

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Set the PYTHONPATH to include the current directory
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Run the tests
echo "Starting tests..."
python test_function_calling.py

# Check the exit code
if [ $? -eq 0 ]; then
    echo "All tests passed successfully!"
else
    echo "Some tests failed. See log for details."
fi

echo "=============================================="
echo "  Test Run Complete"
echo "==============================================" 