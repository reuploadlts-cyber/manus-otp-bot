#!/bin/bash

# Test runner script for ivasms Telegram Bot

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Running ivasms Telegram Bot Tests...${NC}"

# Check if we're in the correct directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: requirements.txt not found. Please run this script from the project root directory.${NC}"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Run tests with different options based on arguments
case "${1:-all}" in
    "unit")
        echo -e "${GREEN}Running unit tests only...${NC}"
        python -m pytest tests/ -m "not integration" -v
        ;;
    "integration")
        echo -e "${GREEN}Running integration tests only...${NC}"
        python -m pytest tests/ -m "integration" -v
        ;;
    "coverage")
        echo -e "${GREEN}Running tests with coverage report...${NC}"
        python -m pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
        echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;
    "fast")
        echo -e "${GREEN}Running fast tests only...${NC}"
        python -m pytest tests/ -m "not slow" -v
        ;;
    "verbose")
        echo -e "${GREEN}Running all tests with verbose output...${NC}"
        python -m pytest tests/ -v -s
        ;;
    "all"|*)
        echo -e "${GREEN}Running all tests...${NC}"
        python -m pytest tests/ -v
        ;;
esac

echo -e "${GREEN}Tests completed!${NC}"
