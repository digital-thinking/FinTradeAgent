#!/bin/bash

# FinTradeAgent Deployment Script
# Usage: ./scripts/deploy.sh [environment] [options]

set -e

# Default values
ENVIRONMENT="production"
COMPOSE_FILES="docker-compose.production.yml"
MONITORING=false
REBUILD=false
BACKUP=true
MIGRATE=true
HEALTH_CHECK=true
LOG_LEVEL="info"

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
Usage: $0 [ENVIRONMENT] [OPTIONS]

ENVIRONMENT:
    production      Deploy production environment (default)
    staging         Deploy staging environment
    development     Deploy development environment

OPTIONS:
    --monitoring    Include monitoring stack (Prometheus, Grafana)
    --rebuild       Force rebuild of all images
    --no-backup     Skip database backup before deployment
    --no-migrate    Skip database migrations
    --no-health     Skip health checks after deployment
    --log-level     Set log level (debug, info, warning, error)
    --help          Show this help message

Examples:
    $0 production --monitoring --rebuild
    $0 staging --no-backup
    $0 development --log-level debug
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        production|staging|development)
            ENVIRONMENT="$1"
            shift
            ;;
        --monitoring)
            MONITORING=true
            shift
            ;;
        --rebuild)
            REBUILD=true
            shift
            ;;
        --no-backup)
            BACKUP=false
            shift
            ;;
        --no-migrate)
            MIGRATE=false
            shift
            ;;
        --no-health)
            HEALTH_CHECK=false
            shift
            ;;
        --log-level)
            LOG_LEVEL="$2"
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

# Set compose files based on environment and options
case $ENVIRONMENT in
    production)
        COMPOSE_FILES="docker-compose.production.yml"
        ;;
    staging)
        COMPOSE_FILES="docker-compose.staging.yml"
        ;;
    development)
        COMPOSE_FILES="docker-compose.dev.yml"
        BACKUP=false  # Don't backup dev environment
        ;;
esac

if [ "$MONITORING" = true ]; then
    COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.monitoring.yml"
fi

log_info "Deploying FinTradeAgent to $ENVIRONMENT environment"
log_info "Compose files: $COMPOSE_FILES"

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    
    # Check if docker-compose is available
    if ! command -v docker-compose >/dev/null 2>&1; then
        log_error "docker-compose is not installed or not in PATH."
        exit 1
    fi
    
    # Check if environment file exists
    ENV_FILE=".env.$ENVIRONMENT"
    if [ ! -f "$ENV_FILE" ]; then
        log_error "Environment file $ENV_FILE not found."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Create backup
create_backup() {
    if [ "$BACKUP" = true ]; then
        log_info "Creating database backup..."
        BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        
        # Backup database
        if docker-compose -f $COMPOSE_FILES ps db >/dev/null 2>&1; then
            docker-compose -f $COMPOSE_FILES exec -T db pg_dump -U fintradeagent fintradeagent_prod > "$BACKUP_DIR/database.sql"
            log_success "Database backup created: $BACKUP_DIR/database.sql"
        else
            log_warning "Database container not running, skipping backup"
        fi
    else
        log_info "Skipping database backup"
    fi
}

# Build images
build_images() {
    log_info "Building Docker images..."
    
    if [ "$REBUILD" = true ]; then
        log_info "Force rebuilding all images..."
        docker-compose -f $COMPOSE_FILES build --no-cache --pull
    else
        docker-compose -f $COMPOSE_FILES build --pull
    fi
    
    log_success "Docker images built successfully"
}

# Start services
start_services() {
    log_info "Starting services..."
    
    # Start database and cache first
    docker-compose -f $COMPOSE_FILES up -d db redis
    
    # Wait for database to be ready
    log_info "Waiting for database to be ready..."
    docker-compose -f $COMPOSE_FILES exec db sh -c 'until pg_isready -U fintradeagent -d fintradeagent_prod; do sleep 1; done'
    
    # Run migrations if enabled
    if [ "$MIGRATE" = true ]; then
        log_info "Running database migrations..."
        docker-compose -f $COMPOSE_FILES run --rm app python -m alembic upgrade head
        log_success "Database migrations completed"
    fi
    
    # Start remaining services
    docker-compose -f $COMPOSE_FILES up -d
    
    log_success "Services started successfully"
}

# Health checks
run_health_checks() {
    if [ "$HEALTH_CHECK" = true ]; then
        log_info "Running health checks..."
        
        # Wait a bit for services to start
        sleep 10
        
        # Check application health
        if curl -f http://localhost:8000/health >/dev/null 2>&1; then
            log_success "Application health check passed"
        else
            log_error "Application health check failed"
            return 1
        fi
        
        # Check database connectivity
        if docker-compose -f $COMPOSE_FILES exec -T app python -c "
from sqlalchemy import create_engine
import os
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    conn.execute('SELECT 1')
print('Database connection successful')
" >/dev/null 2>&1; then
            log_success "Database connectivity check passed"
        else
            log_error "Database connectivity check failed"
            return 1
        fi
        
        log_success "All health checks passed"
    else
        log_info "Skipping health checks"
    fi
}

# Show deployment status
show_status() {
    log_info "Deployment status:"
    docker-compose -f $COMPOSE_FILES ps
    
    log_info "Service endpoints:"
    echo "  Application: http://localhost:8000"
    echo "  API Documentation: http://localhost:8000/docs"
    
    if [ "$MONITORING" = true ]; then
        echo "  Prometheus: http://localhost:9090"
        echo "  Grafana: http://localhost:3001"
    fi
}

# Main deployment flow
main() {
    check_prerequisites
    create_backup
    build_images
    start_services
    run_health_checks
    show_status
    
    log_success "Deployment to $ENVIRONMENT completed successfully!"
}

# Run deployment
main