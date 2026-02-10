#!/bin/bash
# Run FastAPI endpoint tests

set -e

echo "Running FinTradeAgent API Tests..."
echo "=================================="

# Change to project directory
cd "$(dirname "$0")/.."

# Activate virtual environment if available
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Install test dependencies if needed
echo "Installing test dependencies..."
poetry install --with dev

# Run API tests specifically
echo "Running API endpoint tests..."
poetry run pytest tests/test_*_api.py -v --tb=short

echo "Running coverage report for API tests..."
poetry run pytest tests/test_*_api.py --cov=backend --cov-report=html --cov-report=term

echo "=================================="
echo "API tests completed!"
echo "Coverage report available in htmlcov/index.html"