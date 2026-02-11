#!/bin/bash

# FinTradeAgent Health Check Script
# Usage: ./scripts/health-check.sh [options]

set -e

# Default values
ENVIRONMENT="production"
TIMEOUT=30
VERBOSE=false
JSON_OUTPUT=false
WEBHOOK_URL=""
EXIT_ON_FAILURE=true

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Health check results
RESULTS=()
OVERALL_STATUS="HEALTHY"

# Logging functions
log_info() {
    if [ "$VERBOSE" = true ] || [ "$JSON_OUTPUT" = false ]; then
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
}

log_success() {
    if [ "$VERBOSE" = true ] || [ "$JSON_OUTPUT" = false ]; then
        echo -e "${GREEN}[SUCCESS]${NC} $1"
    fi
}

log_warning() {
    if [ "$VERBOSE" = true ] || [ "$JSON_OUTPUT" = false ]; then
        echo -e "${YELLOW}[WARNING]${NC} $1"
    fi
}

log_error() {
    if [ "$VERBOSE" = true ] || [ "$JSON_OUTPUT" = false ]; then
        echo -e "${RED}[ERROR]${NC} $1"
    fi
}

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

OPTIONS:
    --environment ENV   Target environment (production, staging, development)
    --timeout SECONDS   HTTP request timeout in seconds (default: 30)
    --verbose           Enable verbose output
    --json              Output results in JSON format
    --webhook URL       Send results to webhook URL
    --no-exit          Don't exit with error code on failure
    --help              Show this help message

Examples:
    $0 --environment production --verbose
    $0 --json --timeout 10
    $0 --webhook https://hooks.slack.com/... --no-exit
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --webhook)
            WEBHOOK_URL="$2"
            shift 2
            ;;
        --no-exit)
            EXIT_ON_FAILURE=false
            shift
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Set environment-specific endpoints
case $ENVIRONMENT in
    production)
        BASE_URL="http://localhost:8000"
        COMPOSE_FILE="docker-compose.production.yml"
        ;;
    staging)
        BASE_URL="http://localhost:8001"
        COMPOSE_FILE="docker-compose.staging.yml"
        ;;
    development)
        BASE_URL="http://localhost:8001"
        COMPOSE_FILE="docker-compose.dev.yml"
        ;;
    *)
        log_error "Unknown environment: $ENVIRONMENT"
        exit 1
        ;;
esac

# Add result to results array
add_result() {
    local service="$1"
    local status="$2"
    local message="$3"
    local response_time="$4"
    
    if [ "$JSON_OUTPUT" = true ]; then
        RESULTS+=("{\"service\":\"$service\",\"status\":\"$status\",\"message\":\"$message\",\"response_time\":\"$response_time\"}")
    else
        RESULTS+=("$service: $status - $message")
    fi
    
    if [ "$status" != "HEALTHY" ]; then
        OVERALL_STATUS="UNHEALTHY"
    fi
}

# Check container status
check_containers() {
    log_info "Checking container status..."
    
    if ! command -v docker >/dev/null 2>&1; then
        add_result "docker" "ERROR" "Docker not available" "N/A"
        return
    fi
    
    # List of expected containers
    local containers=("fintradeagent-app" "fintradeagent-db" "fintradeagent-redis" "fintradeagent-nginx")
    
    for container in "${containers[@]}"; do
        local start_time=$(date +%s.%N)
        
        if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            local status=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "unknown")
            local end_time=$(date +%s.%N)
            local response_time=$(echo "$end_time - $start_time" | bc)
            
            case $status in
                "healthy")
                    add_result "$container" "HEALTHY" "Container running and healthy" "${response_time}s"
                    ;;
                "unhealthy")
                    add_result "$container" "UNHEALTHY" "Container running but unhealthy" "${response_time}s"
                    ;;
                "starting")
                    add_result "$container" "WARNING" "Container starting" "${response_time}s"
                    ;;
                *)
                    add_result "$container" "WARNING" "Container running (health status: $status)" "${response_time}s"
                    ;;
            esac
        else
            add_result "$container" "ERROR" "Container not running" "N/A"
        fi
    done
}

# Check HTTP endpoints
check_http_endpoints() {
    log_info "Checking HTTP endpoints..."
    
    # List of endpoints to check
    local endpoints=(
        "/health:Application Health"
        "/api/health:API Health"
        "/docs:API Documentation"
        "/api/portfolios:Portfolios API"
        "/api/system/health:System Health"
    )
    
    for endpoint_info in "${endpoints[@]}"; do
        local endpoint=$(echo "$endpoint_info" | cut -d: -f1)
        local description=$(echo "$endpoint_info" | cut -d: -f2)
        local url="$BASE_URL$endpoint"
        
        local start_time=$(date +%s.%N)
        local http_code=$(curl -s -w "%{http_code}" -o /dev/null --max-time "$TIMEOUT" "$url" || echo "000")
        local end_time=$(date +%s.%N)
        local response_time=$(echo "$end_time - $start_time" | bc)
        
        case $http_code in
            200)
                add_result "$description" "HEALTHY" "HTTP $http_code" "${response_time}s"
                ;;
            404)
                add_result "$description" "WARNING" "HTTP $http_code - Endpoint not found" "${response_time}s"
                ;;
            500|502|503|504)
                add_result "$description" "ERROR" "HTTP $http_code - Server error" "${response_time}s"
                ;;
            000)
                add_result "$description" "ERROR" "Connection failed or timeout" "${response_time}s"
                ;;
            *)
                add_result "$description" "WARNING" "HTTP $http_code" "${response_time}s"
                ;;
        esac
    done
}

# Check database connectivity
check_database() {
    log_info "Checking database connectivity..."
    
    local start_time=$(date +%s.%N)
    
    if docker exec fintradeagent-app python -c "
import os
from sqlalchemy import create_engine, text
try:
    engine = create_engine(os.getenv('DATABASE_URL'))
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1'))
        print('SUCCESS')
except Exception as e:
    print(f'ERROR: {e}')
" 2>/dev/null | grep -q "SUCCESS"; then
        local end_time=$(date +%s.%N)
        local response_time=$(echo "$end_time - $start_time" | bc)
        add_result "database" "HEALTHY" "Database connection successful" "${response_time}s"
    else
        local end_time=$(date +%s.%N)
        local response_time=$(echo "$end_time - $start_time" | bc)
        add_result "database" "ERROR" "Database connection failed" "${response_time}s"
    fi
}

# Check Redis connectivity
check_redis() {
    log_info "Checking Redis connectivity..."
    
    local start_time=$(date +%s.%N)
    
    if docker exec fintradeagent-redis redis-cli --pass "${REDIS_PASSWORD:-dev_redis_123}" ping 2>/dev/null | grep -q "PONG"; then
        local end_time=$(date +%s.%N)
        local response_time=$(echo "$end_time - $start_time" | bc)
        add_result "redis" "HEALTHY" "Redis connection successful" "${response_time}s"
    else
        local end_time=$(date +%s.%N)
        local response_time=$(echo "$end_time - $start_time" | bc)
        add_result "redis" "ERROR" "Redis connection failed" "${response_time}s"
    fi
}

# Check disk space
check_disk_space() {
    log_info "Checking disk space..."
    
    local start_time=$(date +%s.%N)
    local disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    local end_time=$(date +%s.%N)
    local response_time=$(echo "$end_time - $start_time" | bc)
    
    if [ "$disk_usage" -lt 80 ]; then
        add_result "disk_space" "HEALTHY" "Disk usage: ${disk_usage}%" "${response_time}s"
    elif [ "$disk_usage" -lt 90 ]; then
        add_result "disk_space" "WARNING" "Disk usage: ${disk_usage}%" "${response_time}s"
    else
        add_result "disk_space" "ERROR" "Disk usage: ${disk_usage}%" "${response_time}s"
    fi
}

# Check memory usage
check_memory() {
    log_info "Checking memory usage..."
    
    local start_time=$(date +%s.%N)
    local memory_usage=$(free | grep Mem | awk '{printf("%.0f", ($3/$2)*100)}')
    local end_time=$(date +%s.%N)
    local response_time=$(echo "$end_time - $start_time" | bc)
    
    if [ "$memory_usage" -lt 80 ]; then
        add_result "memory" "HEALTHY" "Memory usage: ${memory_usage}%" "${response_time}s"
    elif [ "$memory_usage" -lt 90 ]; then
        add_result "memory" "WARNING" "Memory usage: ${memory_usage}%" "${response_time}s"
    else
        add_result "memory" "ERROR" "Memory usage: ${memory_usage}%" "${response_time}s"
    fi
}

# Send webhook notification
send_webhook() {
    if [ -n "$WEBHOOK_URL" ]; then
        log_info "Sending webhook notification..."
        
        local payload
        if [ "$JSON_OUTPUT" = true ]; then
            payload="{\"status\":\"$OVERALL_STATUS\",\"environment\":\"$ENVIRONMENT\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"results\":[$(IFS=','; echo "${RESULTS[*]}")]}"
        else
            local message="FinTradeAgent Health Check - $ENVIRONMENT\nOverall Status: $OVERALL_STATUS\n\nResults:\n$(printf '%s\n' "${RESULTS[@]}")"
            payload="{\"text\":\"$message\"}"
        fi
        
        curl -X POST "$WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "$payload" \
            >/dev/null 2>&1 || log_warning "Failed to send webhook"
    fi
}

# Output results
output_results() {
    if [ "$JSON_OUTPUT" = true ]; then
        echo "{\"status\":\"$OVERALL_STATUS\",\"environment\":\"$ENVIRONMENT\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"results\":[$(IFS=','; echo "${RESULTS[*]}")]}"
    else
        echo ""
        echo "FinTradeAgent Health Check Results - $ENVIRONMENT"
        echo "================================================"
        echo "Overall Status: $OVERALL_STATUS"
        echo "Timestamp: $(date)"
        echo ""
        printf '%s\n' "${RESULTS[@]}"
        echo ""
    fi
}

# Main health check process
main() {
    log_info "Starting health check for $ENVIRONMENT environment"
    
    # Run all checks
    check_containers
    check_http_endpoints
    check_database
    check_redis
    check_disk_space
    check_memory
    
    # Output results
    output_results
    
    # Send webhook if configured
    send_webhook
    
    # Exit with appropriate code
    if [ "$OVERALL_STATUS" != "HEALTHY" ] && [ "$EXIT_ON_FAILURE" = true ]; then
        exit 1
    fi
    
    exit 0
}

# Run health check
main "$@"