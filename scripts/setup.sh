#!/bin/bash

# OTP Forwarder Bot Setup Script
# This script sets up the development environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log with timestamp
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Function to log errors
log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

# Function to log warnings
log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Function to log info
log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

log "Starting OTP Forwarder Bot setup..."

# Check if Python 3.11+ is installed
log_info "Checking Python version..."
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    log_error "Python 3.11+ is required. Found: $python_version"
    exit 1
fi

log "Python version check passed: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    log_info "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
log_info "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
log_info "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
log_info "Installing Python dependencies..."
pip install -r requirements.txt

# Install Playwright browsers
log_info "Installing Playwright browsers..."
playwright install --with-deps chromium

# Create necessary directories
log_info "Creating directories..."
mkdir -p logs
mkdir -p screenshots

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    log_info "Creating .env file from template..."
    cp .env.example .env
    log_warning "Please edit .env file with your credentials before running the bot"
fi

# Create config.yaml if it doesn't exist
if [ ! -f "config.yaml" ]; then
    log_error "config.yaml not found. Please create it from the template in the repository"
    exit 1
fi

# Set up pre-commit hooks (if available)
if command -v pre-commit &> /dev/null; then
    log_info "Setting up pre-commit hooks..."
    pre-commit install
fi

# Run tests
log_info "Running tests..."
python -m pytest tests/ -v

log "Setup completed successfully!"
log_info "Next steps:"
log_info "1. Edit .env file with your credentials"
log_info "2. Run the bot with: python run.py"
log_info "3. Or use the startup script: ./run.sh"

log "Happy coding! 🚀"
