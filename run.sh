#!/bin/bash

# OTP Forwarder Bot startup script
# This script handles bot startup, restart on failure, and graceful shutdown

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BOT_SCRIPT="run.py"
MAX_RESTARTS=5
RESTART_DELAY=10
LOG_FILE="logs/bot.log"

# Create logs directory if it doesn't exist
mkdir -p logs

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

# Function to check if bot is running
is_bot_running() {
    pgrep -f "$BOT_SCRIPT" > /dev/null
}

# Function to start the bot
start_bot() {
    log "Starting OTP Forwarder Bot..."
    
    # Check if .env file exists
    if [ ! -f ".env" ]; then
        log_error ".env file not found. Please create it from .env.example"
        exit 1
    fi
    
    # Check if config.yaml exists
    if [ ! -f "config.yaml" ]; then
        log_error "config.yaml not found. Please create it from config.yaml.example"
        exit 1
    fi
    
    # Start the bot
    python "$BOT_SCRIPT" 2>&1 | tee -a "$LOG_FILE" &
    BOT_PID=$!
    
    # Wait a moment to see if it starts successfully
    sleep 5
    
    if is_bot_running; then
        log "Bot started successfully (PID: $BOT_PID)"
        return 0
    else
        log_error "Bot failed to start"
        return 1
    fi
}

# Function to stop the bot
stop_bot() {
    log "Stopping bot..."
    
    if is_bot_running; then
        # Try graceful shutdown first
        pkill -TERM -f "$BOT_SCRIPT"
        
        # Wait for graceful shutdown
        sleep 5
        
        # Force kill if still running
        if is_bot_running; then
            log_warning "Bot didn't stop gracefully, forcing shutdown..."
            pkill -KILL -f "$BOT_SCRIPT"
        fi
        
        log "Bot stopped"
    else
        log "Bot is not running"
    fi
}

# Function to restart the bot
restart_bot() {
    log "Restarting bot..."
    stop_bot
    sleep 2
    start_bot
}

# Function to handle signals
cleanup() {
    log "Received shutdown signal, cleaning up..."
    stop_bot
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Main execution
main() {
    log "OTP Forwarder Bot Manager starting..."
    
    # Check if bot is already running
    if is_bot_running; then
        log_warning "Bot is already running"
        exit 1
    fi
    
    # Start the bot
    if ! start_bot; then
        log_error "Failed to start bot"
        exit 1
    fi
    
    # Monitor the bot
    restart_count=0
    while true; do
        sleep 10
        
        if ! is_bot_running; then
            log_error "Bot stopped unexpectedly"
            
            if [ $restart_count -lt $MAX_RESTARTS ]; then
                restart_count=$((restart_count + 1))
                log_warning "Restarting bot (attempt $restart_count/$MAX_RESTARTS)..."
                sleep $RESTART_DELAY
                
                if start_bot; then
                    restart_count=0  # Reset counter on successful restart
                else
                    log_error "Failed to restart bot"
                fi
            else
                log_error "Max restart attempts reached, giving up"
                exit 1
            fi
        fi
    done
}

# Run main function
main "$@"
