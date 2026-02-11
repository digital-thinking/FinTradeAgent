#!/bin/bash

# FinTradeAgent Backup Script
# Usage: ./scripts/backup.sh [options]

set -e

# Default values
BACKUP_DIR="backups"
ENVIRONMENT="production"
RETENTION_DAYS=30
COMPRESS=true
REMOTE_BACKUP=false
S3_BUCKET=""
NOTIFICATION_WEBHOOK=""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

OPTIONS:
    --environment ENV   Target environment (production, staging, development)
    --backup-dir DIR    Backup directory (default: backups)
    --retention DAYS    Number of days to keep backups (default: 30)
    --no-compress       Do not compress backup files
    --s3-bucket BUCKET  Upload backups to S3 bucket
    --webhook URL       Send notification to webhook URL
    --help              Show this help message

Examples:
    $0 --environment production
    $0 --backup-dir /data/backups --retention 14
    $0 --s3-bucket my-backup-bucket --webhook https://hooks.slack.com/...
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --backup-dir)
            BACKUP_DIR="$2"
            shift 2
            ;;
        --retention)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        --no-compress)
            COMPRESS=false
            shift
            ;;
        --s3-bucket)
            S3_BUCKET="$2"
            REMOTE_BACKUP=true
            shift 2
            ;;
        --webhook)
            NOTIFICATION_WEBHOOK="$2"
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

# Set compose file based on environment
case $ENVIRONMENT in
    production)
        COMPOSE_FILE="docker-compose.production.yml"
        DB_CONTAINER="fintradeagent-db"
        DB_NAME="fintradeagent_prod"
        DB_USER="fintradeagent"
        ;;
    staging)
        COMPOSE_FILE="docker-compose.staging.yml"
        DB_CONTAINER="fintradeagent-db-staging"
        DB_NAME="fintradeagent_staging"
        DB_USER="fintradeagent_staging"
        ;;
    development)
        COMPOSE_FILE="docker-compose.dev.yml"
        DB_CONTAINER="fintradeagent-db-dev"
        DB_NAME="fintradeagent_dev"
        DB_USER="fintradeagent_dev"
        ;;
    *)
        log_error "Unknown environment: $ENVIRONMENT"
        exit 1
        ;;
esac

# Create timestamp for backup
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_PATH="$BACKUP_DIR/$ENVIRONMENT/$TIMESTAMP"

# Send notification
send_notification() {
    local message="$1"
    local status="$2"
    
    if [ -n "$NOTIFICATION_WEBHOOK" ]; then
        curl -X POST "$NOTIFICATION_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{\"text\":\"FinTradeAgent Backup [$status]: $message\"}" \
            >/dev/null 2>&1 || log_warning "Failed to send notification"
    fi
}

# Create backup directory
create_backup_dir() {
    log_info "Creating backup directory: $BACKUP_PATH"
    mkdir -p "$BACKUP_PATH"
}

# Backup database
backup_database() {
    log_info "Backing up database..."
    
    # Check if database container is running
    if ! docker ps --format 'table {{.Names}}' | grep -q "$DB_CONTAINER"; then
        log_error "Database container $DB_CONTAINER is not running"
        return 1
    fi
    
    # Create database dump
    local db_backup_file="$BACKUP_PATH/database.sql"
    docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" > "$db_backup_file"
    
    if [ -s "$db_backup_file" ]; then
        log_success "Database backup created: $db_backup_file"
        
        # Compress if enabled
        if [ "$COMPRESS" = true ]; then
            gzip "$db_backup_file"
            log_success "Database backup compressed: ${db_backup_file}.gz"
        fi
    else
        log_error "Database backup failed - file is empty"
        return 1
    fi
}

# Backup application data
backup_app_data() {
    log_info "Backing up application data..."
    
    # Backup volume data if containers are running
    if docker ps --format 'table {{.Names}}' | grep -q "fintradeagent-app"; then
        # Create tar archive of important volumes
        docker run --rm \
            -v fintradeagent_app_data:/data:ro \
            -v "$(pwd)/$BACKUP_PATH":/backup \
            alpine tar czf /backup/app_data.tar.gz -C /data .
        
        log_success "Application data backup created: $BACKUP_PATH/app_data.tar.gz"
    else
        log_warning "Application container not running, skipping app data backup"
    fi
}

# Backup configuration files
backup_config() {
    log_info "Backing up configuration files..."
    
    # Copy important configuration files
    local config_backup_dir="$BACKUP_PATH/config"
    mkdir -p "$config_backup_dir"
    
    # Copy environment files (without sensitive data)
    if [ -f ".env.$ENVIRONMENT" ]; then
        grep -v -E '^(PASSWORD|SECRET|KEY|TOKEN)=' ".env.$ENVIRONMENT" > "$config_backup_dir/env_template.txt"
    fi
    
    # Copy docker compose files
    cp "$COMPOSE_FILE" "$config_backup_dir/" 2>/dev/null || true
    cp docker-compose.monitoring.yml "$config_backup_dir/" 2>/dev/null || true
    
    # Copy nginx configuration
    if [ -d "nginx" ]; then
        cp -r nginx "$config_backup_dir/"
    fi
    
    # Copy monitoring configuration
    if [ -d "monitoring" ]; then
        cp -r monitoring "$config_backup_dir/"
    fi
    
    log_success "Configuration backup created: $config_backup_dir"
}

# Upload to S3 if configured
upload_to_s3() {
    if [ "$REMOTE_BACKUP" = true ] && [ -n "$S3_BUCKET" ]; then
        log_info "Uploading backup to S3 bucket: $S3_BUCKET"
        
        # Check if AWS CLI is available
        if command -v aws >/dev/null 2>&1; then
            # Create tar archive of entire backup
            tar czf "$BACKUP_PATH.tar.gz" -C "$BACKUP_DIR/$ENVIRONMENT" "$TIMESTAMP"
            
            # Upload to S3
            aws s3 cp "$BACKUP_PATH.tar.gz" "s3://$S3_BUCKET/fintradeagent-backups/$ENVIRONMENT/"
            
            # Clean up local tar file
            rm "$BACKUP_PATH.tar.gz"
            
            log_success "Backup uploaded to S3 successfully"
        else
            log_warning "AWS CLI not available, skipping S3 upload"
        fi
    fi
}

# Clean up old backups
cleanup_old_backups() {
    log_info "Cleaning up backups older than $RETENTION_DAYS days..."
    
    # Find and remove old backup directories
    if [ -d "$BACKUP_DIR/$ENVIRONMENT" ]; then
        find "$BACKUP_DIR/$ENVIRONMENT" -type d -mtime +$RETENTION_DAYS -exec rm -rf {} + 2>/dev/null || true
        log_success "Old backups cleaned up"
    fi
    
    # Clean up old S3 backups if configured
    if [ "$REMOTE_BACKUP" = true ] && [ -n "$S3_BUCKET" ] && command -v aws >/dev/null 2>&1; then
        local cutoff_date=$(date -d "$RETENTION_DAYS days ago" '+%Y-%m-%d')
        aws s3 ls "s3://$S3_BUCKET/fintradeagent-backups/$ENVIRONMENT/" --recursive | \
        awk '$1 <= "'$cutoff_date'" {print $4}' | \
        xargs -r -I {} aws s3 rm "s3://$S3_BUCKET/{}"
    fi
}

# Generate backup report
generate_report() {
    local report_file="$BACKUP_PATH/backup_report.txt"
    
    {
        echo "FinTradeAgent Backup Report"
        echo "=========================="
        echo "Timestamp: $(date)"
        echo "Environment: $ENVIRONMENT"
        echo "Backup Location: $BACKUP_PATH"
        echo ""
        echo "Files Created:"
        ls -lah "$BACKUP_PATH"
        echo ""
        echo "Disk Usage:"
        du -sh "$BACKUP_PATH"
    } > "$report_file"
    
    log_success "Backup report created: $report_file"
}

# Main backup process
main() {
    local start_time=$(date)
    log_info "Starting backup process for $ENVIRONMENT environment"
    
    # Create notification
    send_notification "Backup started for $ENVIRONMENT environment" "INFO"
    
    # Run backup steps
    create_backup_dir
    
    if backup_database && backup_app_data && backup_config; then
        upload_to_s3
        cleanup_old_backups
        generate_report
        
        local end_time=$(date)
        log_success "Backup completed successfully"
        log_info "Start time: $start_time"
        log_info "End time: $end_time"
        
        send_notification "Backup completed successfully for $ENVIRONMENT environment" "SUCCESS"
    else
        log_error "Backup failed"
        send_notification "Backup failed for $ENVIRONMENT environment" "ERROR"
        exit 1
    fi
}

# Run backup
main "$@"