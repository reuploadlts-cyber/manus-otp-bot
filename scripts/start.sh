#!/bin/bash

# ivasms Telegram Bot Start Script
# This script sets up the environment and starts the bot

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting ivasms Telegram Bot...${NC}"

# Check if we're in the correct directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: requirements.txt not found. Please run this script from the project root directory.${NC}"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found. Make sure environment variables are set.${NC}"
    echo -e "${YELLOW}You can copy .env.example to .env and fill in your values.${NC}"
fi

# Create data directory if it doesn't exist
mkdir -p data

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Install/upgrade dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers if not already installed
echo -e "${GREEN}Installing Playwright browsers...${NC}"
playwright install

# Check if required environment variables are set
echo -e "${GREEN}Checking configuration...${NC}"
python3 -c "
import sys
sys.path.append('src')
from config import Config

errors = Config.validate()
if errors:
    print('Configuration errors:')
    for error in errors:
        print(f'  - {error}')
    sys.exit(1)
else:
    print('Configuration is valid!')
"

if [ $? -ne 0 ]; then
    echo -e "${RED}Configuration validation failed. Please check your environment variables.${NC}"
    exit 1
fi

# Start the bot
echo -e "${GREEN}Starting the bot...${NC}"
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Run the bot with proper error handling
python3 -m src.main "$@"
