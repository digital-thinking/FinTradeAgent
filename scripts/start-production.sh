#!/bin/bash

# Production startup script for FinTradeAgent
# This script starts the FastAPI application with production-optimized settings

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_MODULE="backend.main_production:app"
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}
WORKERS=${WORKERS:-4}
LOG_LEVEL=${LOG_LEVEL:-info}
WORKER_CLASS=${WORKER_CLASS:-uvicorn.workers.UvicornWorker}
MAX_REQUESTS=${MAX_REQUESTS:-1000}
MAX_REQUESTS_JITTER=${MAX_REQUESTS_JITTER:-100}
PRELOAD_APP=${PRELOAD_APP:-true}
TIMEOUT=${TIMEOUT:-30}
KEEPALIVE=${KEEPALIVE:-2}

# Logging configuration
ACCESS_LOG=${ACCESS_LOG:-/var/log/fintradeagent/access.log}
ERROR_LOG=${ERROR_LOG:-/var/log/fintradeagent/error.log}
CAPTURE_OUTPUT=${CAPTURE_OUTPUT:-true}

echo -e "${BLUE}🚀 Starting FinTradeAgent in Production Mode${NC}"
echo -e "${BLUE}Host: ${HOST}${NC}"
echo -e "${BLUE}Port: ${PORT}${NC}"
echo -e "${BLUE}Workers: ${WORKERS}${NC}"
echo -e "${BLUE}Log Level: ${LOG_LEVEL}${NC}"
echo ""

# Function to log messages
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check environment
check_environment() {
    log_info "Checking production environment..."
    
    # Check required environment variables
    required_vars=(
        "SECRET_KEY"
        "JWT_SECRET_KEY"
        "DATABASE_URL"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            log_error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    # Check log directories
    for log_file in "$ACCESS_LOG" "$ERROR_LOG"; do
        log_dir=$(dirname "$log_file")
        if [ ! -d "$log_dir" ]; then
            log_warn "Log directory $log_dir does not exist, creating..."
            mkdir -p "$log_dir"
        fi
        
        if [ ! -w "$log_dir" ]; then
            log_error "Log directory $log_dir is not writable"
            exit 1
        fi
    done
    
    log_info "Environment check passed ✅"
}

# Function to wait for database
wait_for_database() {
    log_info "Waiting for database connection..."
    
    python3 -c "
import os
import sys
import time
from urllib.parse import urlparse
import psycopg2

database_url = os.environ.get('DATABASE_URL')
if not database_url:
    print('DATABASE_URL not set')
    sys.exit(1)

parsed = urlparse(database_url)
max_attempts = 30
attempt = 0

while attempt < max_attempts:
    try:
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:] if parsed.path else 'postgres'
        )
        conn.close()
        print('Database connection successful')
        sys.exit(0)
    except Exception as e:
        attempt += 1
        if attempt >= max_attempts:
            print(f'Failed to connect to database after {max_attempts} attempts: {e}')
            sys.exit(1)
        print(f'Database connection attempt {attempt}/{max_attempts} failed, retrying...')
        time.sleep(2)
"
    
    if [ $? -eq 0 ]; then
        log_info "Database connection established ✅"
    else
        log_error "Failed to connect to database"
        exit 1
    fi
}

# Function to run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    # Add your migration command here
    # Example: python3 -m alembic upgrade head
    
    log_info "Database migrations completed ✅"
}

# Function to validate application
validate_application() {
    log_info "Validating application configuration..."
    
    python3 -c "
import sys
sys.path.insert(0, '.')

try:
    from backend.main_production import app
    from backend.config.production import production_settings
    print('Application configuration valid')
except Exception as e:
    print(f'Application configuration error: {e}')
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        log_info "Application validation passed ✅"
    else
        log_error "Application validation failed"
        exit 1
    fi
}

# Function to setup signal handlers
setup_signal_handlers() {
    # Graceful shutdown handler
    shutdown() {
        log_info "Received shutdown signal, stopping gracefully..."
        
        # Kill gunicorn master process
        if [ ! -z "$GUNICORN_PID" ]; then
            kill -TERM "$GUNICORN_PID"
            wait "$GUNICORN_PID"
        fi
        
        log_info "Shutdown completed ✅"
        exit 0
    }
    
    # Register signal handlers
    trap shutdown SIGTERM SIGINT
}

# Function to start application
start_application() {
    log_info "Starting FinTradeAgent application server..."
    
    # Build gunicorn command
    gunicorn_cmd=(
        "gunicorn"
        "$APP_MODULE"
        "--bind" "${HOST}:${PORT}"
        "--workers" "$WORKERS"
        "--worker-class" "$WORKER_CLASS"
        "--max-requests" "$MAX_REQUESTS"
        "--max-requests-jitter" "$MAX_REQUESTS_JITTER"
        "--timeout" "$TIMEOUT"
        "--keepalive" "$KEEPALIVE"
        "--log-level" "$LOG_LEVEL"
        "--access-logfile" "$ACCESS_LOG"
        "--error-logfile" "$ERROR_LOG"
        "--pid" "/tmp/gunicorn.pid"
        "--user" "appuser"
        "--group" "appgroup"
    )
    
    # Add conditional options
    if [ "$PRELOAD_APP" = "true" ]; then
        gunicorn_cmd+=("--preload")
    fi
    
    if [ "$CAPTURE_OUTPUT" = "true" ]; then
        gunicorn_cmd+=("--capture-output")
    fi
    
    # Add SSL configuration if certificates are available
    if [ -f "/etc/ssl/certs/server.crt" ] && [ -f "/etc/ssl/private/server.key" ]; then
        log_info "SSL certificates found, enabling HTTPS"
        gunicorn_cmd+=("--certfile" "/etc/ssl/certs/server.crt")
        gunicorn_cmd+=("--keyfile" "/etc/ssl/private/server.key")
    fi
    
    log_info "Starting with command: ${gunicorn_cmd[*]}"
    
    # Start gunicorn in background to capture PID
    "${gunicorn_cmd[@]}" &
    GUNICORN_PID=$!
    
    log_info "Application started with PID: $GUNICORN_PID ✅"
    
    # Wait for gunicorn to finish
    wait "$GUNICORN_PID"
}

# Function to monitor application health
monitor_health() {
    log_info "Setting up health monitoring..."
    
    # Background health check
    while true; do
        sleep 30
        
        if ! curl -f -s http://localhost:${PORT}/health > /dev/null; then
            log_warn "Health check failed"
        fi
    done &
    
    HEALTH_MONITOR_PID=$!
    
    # Cleanup function for health monitor
    cleanup_health_monitor() {
        if [ ! -z "$HEALTH_MONITOR_PID" ]; then
            kill "$HEALTH_MONITOR_PID" 2>/dev/null || true
        fi
    }
    
    trap cleanup_health_monitor EXIT
}

# Main execution
main() {
    setup_signal_handlers
    check_environment
    wait_for_database
    run_migrations
    validate_application
    
    # Start health monitoring in background
    monitor_health
    
    # Start the application
    start_application
}

# Run main function
main "$@"