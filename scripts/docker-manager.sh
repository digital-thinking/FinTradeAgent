#!/bin/bash

# FinTradeAgent Docker Management Script
# Usage: ./scripts/docker-manager.sh [command] [options]

set -e

# Default values
ENVIRONMENT="production"
COMMAND=""
SERVICE=""
FORCE=false
FOLLOW_LOGS=false
TAIL_LINES=50

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Usage information
usage() {
    cat << EOF
Usage: $0 COMMAND [OPTIONS]

COMMANDS:
    start           Start all services
    stop            Stop all services
    restart         Restart all services
    status          Show service status
    logs            Show service logs
    build           Build/rebuild images
    clean           Clean up Docker resources
    scale           Scale services
    exec            Execute command in container
    update          Update and restart services
    backup          Create backup before operations
    health          Run health checks

OPTIONS:
    --environment ENV    Target environment (production, staging, development)
    --service SERVICE    Target specific service
    --force             Force operation (skip confirmations)
    --follow            Follow logs in real-time
    --tail LINES        Number of log lines to show (default: 50)
    --scale REPLICAS    Number of replicas for scaling
    --help              Show this help message

EXAMPLES:
    $0 start --environment production
    $0 logs --service app --follow
    $0 scale --service app --scale 3
    $0 exec --service app --command "python -m pytest"
    $0 clean --force
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        start|stop|restart|status|logs|build|clean|scale|exec|update|backup|health)
            COMMAND="$1"
            shift
            ;;
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --service)
            SERVICE="$2"
            shift 2
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --follow)
            FOLLOW_LOGS=true
            shift
            ;;
        --tail)
            TAIL_LINES="$2"
            shift 2
            ;;
        --scale)
            SCALE_REPLICAS="$2"
            shift 2
            ;;
        --command)
            EXEC_COMMAND="$2"
            shift 2
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

# Validate command
if [ -z "$COMMAND" ]; then
    log_error "No command specified"
    usage
    exit 1
fi

# Set compose file based on environment
case $ENVIRONMENT in
    production)
        COMPOSE_FILES="-f docker-compose.production.yml"
        ;;
    staging)
        COMPOSE_FILES="-f docker-compose.staging.yml"
        ;;
    development)
        COMPOSE_FILES="-f docker-compose.dev.yml"
        ;;
    *)
        log_error "Unknown environment: $ENVIRONMENT"
        exit 1
        ;;
esac

# Add monitoring if available
if [ -f "docker-compose.monitoring.yml" ] && [ "$ENVIRONMENT" != "development" ]; then
    COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.monitoring.yml"
fi

# Service target
SERVICE_TARGET=""
if [ -n "$SERVICE" ]; then
    SERVICE_TARGET="$SERVICE"
fi

# Confirmation prompt
confirm_action() {
    local action="$1"
    if [ "$FORCE" = false ]; then
        log_warning "This will $action in $ENVIRONMENT environment"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Operation cancelled"
            exit 0
        fi
    fi
}

# Check prerequisites
check_prerequisites() {
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v docker-compose >/dev/null 2>&1; then
        log_error "docker-compose is not installed or not in PATH"
        exit 1
    fi
    
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker daemon is not running"
        exit 1
    fi
}

# Start services
start_services() {
    log_info "Starting services in $ENVIRONMENT environment..."
    
    if [ -n "$SERVICE_TARGET" ]; then
        docker-compose $COMPOSE_FILES up -d "$SERVICE_TARGET"
        log_success "Service $SERVICE_TARGET started"
    else
        docker-compose $COMPOSE_FILES up -d
        log_success "All services started"
    fi
    
    # Show status after start
    docker-compose $COMPOSE_FILES ps
}

# Stop services
stop_services() {
    confirm_action "stop services"
    log_info "Stopping services in $ENVIRONMENT environment..."
    
    if [ -n "$SERVICE_TARGET" ]; then
        docker-compose $COMPOSE_FILES stop "$SERVICE_TARGET"
        log_success "Service $SERVICE_TARGET stopped"
    else
        docker-compose $COMPOSE_FILES stop
        log_success "All services stopped"
    fi
}

# Restart services
restart_services() {
    confirm_action "restart services"
    log_info "Restarting services in $ENVIRONMENT environment..."
    
    if [ -n "$SERVICE_TARGET" ]; then
        docker-compose $COMPOSE_FILES restart "$SERVICE_TARGET"
        log_success "Service $SERVICE_TARGET restarted"
    else
        docker-compose $COMPOSE_FILES restart
        log_success "All services restarted"
    fi
}

# Show service status
show_status() {
    log_info "Service status for $ENVIRONMENT environment:"
    docker-compose $COMPOSE_FILES ps
    
    echo
    log_info "Resource usage:"
    docker stats --no-stream
    
    echo
    log_info "Docker system info:"
    docker system df
}

# Show logs
show_logs() {
    log_info "Showing logs for $ENVIRONMENT environment..."
    
    local log_args=""
    if [ "$FOLLOW_LOGS" = true ]; then
        log_args="-f"
    fi
    
    log_args="$log_args --tail=$TAIL_LINES"
    
    if [ -n "$SERVICE_TARGET" ]; then
        docker-compose $COMPOSE_FILES logs $log_args "$SERVICE_TARGET"
    else
        docker-compose $COMPOSE_FILES logs $log_args
    fi
}

# Build images
build_images() {
    confirm_action "build/rebuild images"
    log_info "Building images for $ENVIRONMENT environment..."
    
    local build_args="--pull"
    if [ "$FORCE" = true ]; then
        build_args="$build_args --no-cache"
    fi
    
    if [ -n "$SERVICE_TARGET" ]; then
        docker-compose $COMPOSE_FILES build $build_args "$SERVICE_TARGET"
        log_success "Image for $SERVICE_TARGET built"
    else
        docker-compose $COMPOSE_FILES build $build_args
        log_success "All images built"
    fi
}

# Clean up Docker resources
clean_resources() {
    confirm_action "clean up Docker resources"
    log_info "Cleaning up Docker resources..."
    
    # Remove stopped containers
    log_info "Removing stopped containers..."
    docker container prune -f
    
    # Remove unused images
    log_info "Removing unused images..."
    if [ "$FORCE" = true ]; then
        docker image prune -a -f
    else
        docker image prune -f
    fi
    
    # Remove unused volumes
    log_info "Removing unused volumes..."
    docker volume prune -f
    
    # Remove unused networks
    log_info "Removing unused networks..."
    docker network prune -f
    
    # Remove build cache
    log_info "Removing build cache..."
    docker builder prune -f
    
    log_success "Docker cleanup completed"
    
    # Show remaining resources
    echo
    log_info "Remaining Docker resources:"
    docker system df
}

# Scale services
scale_services() {
    if [ -z "$SERVICE_TARGET" ]; then
        log_error "Service name required for scaling"
        exit 1
    fi
    
    if [ -z "$SCALE_REPLICAS" ]; then
        log_error "Scale replicas required"
        exit 1
    fi
    
    confirm_action "scale $SERVICE_TARGET to $SCALE_REPLICAS replicas"
    log_info "Scaling $SERVICE_TARGET to $SCALE_REPLICAS replicas..."
    
    docker-compose $COMPOSE_FILES up -d --scale "$SERVICE_TARGET=$SCALE_REPLICAS"
    log_success "Service $SERVICE_TARGET scaled to $SCALE_REPLICAS replicas"
    
    # Show updated status
    docker-compose $COMPOSE_FILES ps "$SERVICE_TARGET"
}

# Execute command in container
exec_command() {
    if [ -z "$SERVICE_TARGET" ]; then
        log_error "Service name required for exec"
        exit 1
    fi
    
    if [ -z "$EXEC_COMMAND" ]; then
        log_error "Command required for exec"
        exit 1
    fi
    
    log_info "Executing command in $SERVICE_TARGET: $EXEC_COMMAND"
    docker-compose $COMPOSE_FILES exec "$SERVICE_TARGET" sh -c "$EXEC_COMMAND"
}

# Update services
update_services() {
    confirm_action "update services"
    log_info "Updating services in $ENVIRONMENT environment..."
    
    # Pull latest images
    log_info "Pulling latest images..."
    docker-compose $COMPOSE_FILES pull
    
    # Restart services with new images
    log_info "Restarting services with updated images..."
    if [ -n "$SERVICE_TARGET" ]; then
        docker-compose $COMPOSE_FILES up -d --no-deps "$SERVICE_TARGET"
        log_success "Service $SERVICE_TARGET updated"
    else
        docker-compose $COMPOSE_FILES up -d
        log_success "All services updated"
    fi
    
    # Clean up old images
    log_info "Cleaning up old images..."
    docker image prune -f
}

# Create backup
create_backup() {
    log_info "Creating backup before operation..."
    if [ -x "./scripts/backup.sh" ]; then
        ./scripts/backup.sh --environment "$ENVIRONMENT"
        log_success "Backup created"
    else
        log_warning "Backup script not available"
    fi
}

# Run health checks
run_health_checks() {
    log_info "Running health checks for $ENVIRONMENT environment..."
    if [ -x "./scripts/health-check.sh" ]; then
        ./scripts/health-check.sh --environment "$ENVIRONMENT" --verbose
    else
        log_warning "Health check script not available"
        
        # Basic health checks
        log_info "Running basic health checks..."
        
        # Check if services are running
        local running_services=$(docker-compose $COMPOSE_FILES ps --services --filter "status=running")
        local total_services=$(docker-compose $COMPOSE_FILES ps --services)
        
        echo "Running services: $(echo "$running_services" | wc -l)"
        echo "Total services: $(echo "$total_services" | wc -l)"
        
        # Check application endpoint
        if curl -f http://localhost:8000/health >/dev/null 2>&1; then
            log_success "Application health check passed"
        else
            log_error "Application health check failed"
        fi
    fi
}

# Main execution
main() {
    check_prerequisites
    
    case $COMMAND in
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        build)
            build_images
            ;;
        clean)
            clean_resources
            ;;
        scale)
            scale_services
            ;;
        exec)
            exec_command
            ;;
        update)
            update_services
            ;;
        backup)
            create_backup
            ;;
        health)
            run_health_checks
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            usage
            exit 1
            ;;
    esac
}

# Run the script
main "$@"