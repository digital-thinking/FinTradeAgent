# Environment Configuration Guide

This document describes all environment variables used by FinTradeAgent in different deployment environments.

## 📋 Table of Contents

1. [Environment Files](#environment-files)
2. [Application Configuration](#application-configuration)
3. [Database Configuration](#database-configuration)
4. [Security Configuration](#security-configuration)
5. [External APIs](#external-apis)
6. [Performance Settings](#performance-settings)
7. [Logging and Monitoring](#logging-and-monitoring)
8. [Frontend Configuration](#frontend-configuration)
9. [Development vs Production](#development-vs-production)

## Environment Files

### File Structure

```
.env                    # Default environment (development)
.env.local              # Local overrides (not committed)
.env.development        # Development-specific settings
.env.staging            # Staging environment settings
.env.production         # Production environment settings
frontend/.env           # Frontend development settings
frontend/.env.production # Frontend production settings
```

### Loading Priority

Environment variables are loaded in the following order (later overrides earlier):
1. System environment variables
2. `.env.production` (in production)
3. `.env.local` (if exists)
4. `.env` (fallback)

## Application Configuration

### Basic Application Settings

```bash
# Application identification
APP_NAME="FinTradeAgent API"
APP_VERSION="1.0.0"
APP_ENV="production"  # development|staging|production
DEBUG=False           # Enable debug mode (development only)

# Server configuration
HOST="0.0.0.0"       # Bind address
PORT=8000            # Application port
WORKERS=4            # Number of worker processes
RELOAD=False         # Auto-reload on code changes (development only)
```

### Domain and CORS Settings

```bash
# Allowed hosts for Host header validation
ALLOWED_HOSTS="api.fintradeagent.com,fintradeagent.com,localhost,127.0.0.1"

# CORS origins (comma-separated)
CORS_ORIGINS="https://fintradeagent.com,https://www.fintradeagent.com,http://localhost:3000"

# CORS credentials
CORS_ALLOW_CREDENTIALS=True

# CORS headers
CORS_ALLOW_HEADERS="*"

# CORS methods
CORS_ALLOW_METHODS="GET,POST,PUT,DELETE,OPTIONS"
```

## Database Configuration

### PostgreSQL Settings

```bash
# Database connection URL
DATABASE_URL="postgresql://username:password@host:port/database"

# Connection pool settings
DATABASE_POOL_MIN_SIZE=10    # Minimum connections in pool
DATABASE_POOL_MAX_SIZE=20    # Maximum connections in pool
DATABASE_POOL_TIMEOUT=30     # Connection timeout in seconds

# SSL settings
DATABASE_SSL_MODE="require"  # disable|allow|prefer|require|verify-ca|verify-full

# Additional PostgreSQL settings
DATABASE_STATEMENT_TIMEOUT=30000  # Statement timeout in milliseconds
DATABASE_IDLE_TIMEOUT=300         # Idle connection timeout
```

### Database URL Format

```bash
# Local development
DATABASE_URL="postgresql://fintradeagent:password@localhost:5432/fintradeagent_dev"

# Docker environment
DATABASE_URL="postgresql://fintradeagent:password@db:5432/fintradeagent_prod"

# External database
DATABASE_URL="postgresql://user:pass@rds-host.amazonaws.com:5432/dbname"
```

## Security Configuration

### Encryption and JWT

```bash
# Application secret key (32+ characters)
SECRET_KEY="your-very-long-secret-key-here-32-chars-minimum"

# JWT configuration
JWT_SECRET_KEY="your-jwt-secret-key-32-chars-minimum"
JWT_ALGORITHM="HS256"
JWT_EXPIRY_MINUTES=60
JWT_REFRESH_EXPIRY_DAYS=7

# Password hashing
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_UPPERCASE=True
PASSWORD_REQUIRE_LOWERCASE=True
PASSWORD_REQUIRE_DIGITS=True
PASSWORD_REQUIRE_SYMBOLS=False
```

### SSL/TLS Configuration

```bash
# SSL redirect settings
SSL_REDIRECT=True
SECURE_SSL_REDIRECT=True
SECURE_PROXY_SSL_HEADER="HTTP_X_FORWARDED_PROTO,https"

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True

# Cookie security
SECURE_COOKIES=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### Rate Limiting

```bash
# Enable rate limiting
RATE_LIMIT_ENABLED=True
RATE_LIMIT_REQUESTS=100      # Requests per period
RATE_LIMIT_PERIOD=60         # Period in seconds
RATE_LIMIT_BURST=20          # Burst allowance

# Rate limit storage (Redis)
RATE_LIMIT_STORAGE="redis://redis:6379/1"

# IP whitelist (comma-separated)
RATE_LIMIT_WHITELIST="127.0.0.1,10.0.0.0/8,172.16.0.0/12"
```

## External APIs

### AI Service APIs

```bash
# OpenAI Configuration
OPENAI_API_KEY="sk-your-openai-api-key"
OPENAI_ORG_ID="org-your-org-id"  # Optional
OPENAI_MODEL="gpt-4"             # Default model
OPENAI_MAX_TOKENS=4000           # Maximum tokens per request
OPENAI_TIMEOUT=30                # Request timeout in seconds

# Anthropic Configuration
ANTHROPIC_API_KEY="sk-ant-your-anthropic-key"
ANTHROPIC_MODEL="claude-3-opus-20240229"
ANTHROPIC_MAX_TOKENS=4000

# API rate limiting
AI_API_MAX_REQUESTS_PER_MINUTE=60
AI_API_RETRY_ATTEMPTS=3
AI_API_RETRY_DELAY=1
```

### Financial Data APIs

```bash
# Alpha Vantage
ALPHA_VANTAGE_API_KEY="your-alpha-vantage-key"
ALPHA_VANTAGE_BASE_URL="https://www.alphavantage.co/query"

# Yahoo Finance (free tier)
YAHOO_FINANCE_ENABLED=True
YAHOO_FINANCE_TIMEOUT=10

# Financial data settings
MARKET_DATA_CACHE_TTL=300    # Cache for 5 minutes
MARKET_DATA_RETRY_ATTEMPTS=3
```

### Notification Services

```bash
# Email configuration (SMTP)
EMAIL_HOST="smtp.gmail.com"
EMAIL_PORT=587
EMAIL_HOST_USER="your-email@gmail.com"
EMAIL_HOST_PASSWORD="your-app-password"
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
DEFAULT_FROM_EMAIL="FinTradeAgent <noreply@fintradeagent.com>"

# Slack notifications (optional)
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
SLACK_CHANNEL="#alerts"

# Discord notifications (optional)
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
```

## Performance Settings

### Caching Configuration

```bash
# Redis configuration
REDIS_URL="redis://redis:6379/0"
REDIS_POOL_MIN_SIZE=5
REDIS_POOL_MAX_SIZE=10
REDIS_TIMEOUT=5

# Cache settings
CACHE_ENABLED=True
CACHE_DEFAULT_TTL=3600       # Default cache TTL in seconds
CACHE_MAX_KEY_LENGTH=250     # Maximum cache key length

# Application-specific cache TTLs
PORTFOLIO_CACHE_TTL=1800     # 30 minutes
MARKET_DATA_CACHE_TTL=300    # 5 minutes
USER_SESSION_TTL=86400       # 24 hours
```

### Background Tasks

```bash
# Celery configuration
CELERY_BROKER_URL="redis://redis:6379/2"
CELERY_RESULT_BACKEND="redis://redis:6379/3"
CELERY_WORKER_PROCESSES=2
CELERY_WORKER_MAX_TASKS_PER_CHILD=1000

# Task queues
CELERY_DEFAULT_QUEUE="default"
CELERY_HIGH_PRIORITY_QUEUE="high"
CELERY_LOW_PRIORITY_QUEUE="low"

# Task settings
TASK_SOFT_TIME_LIMIT=300     # 5 minutes
TASK_TIME_LIMIT=600          # 10 minutes
TASK_MAX_RETRIES=3
```

### WebSocket Configuration

```bash
# WebSocket settings
WEBSOCKET_HEARTBEAT_INTERVAL=30    # Heartbeat interval in seconds
WEBSOCKET_TIMEOUT=300              # Connection timeout
WEBSOCKET_MAX_CONNECTIONS=1000     # Maximum concurrent connections
WEBSOCKET_MESSAGE_MAX_SIZE=65536   # Maximum message size in bytes

# WebSocket Redis channels
WEBSOCKET_REDIS_CHANNEL_PREFIX="fintradeagent:ws:"
```

## Logging and Monitoring

### Logging Configuration

```bash
# Log level (DEBUG|INFO|WARNING|ERROR|CRITICAL)
LOG_LEVEL="INFO"

# Log format (text|json)
LOG_FORMAT="json"

# Log file settings
LOG_FILE="/var/log/fintradeagent/app.log"
LOG_MAX_SIZE="100MB"
LOG_BACKUP_COUNT=5

# Specific logger levels
DATABASE_LOG_LEVEL="WARNING"
THIRD_PARTY_LOG_LEVEL="ERROR"
```

### Monitoring and Analytics

```bash
# Error tracking (Sentry)
SENTRY_DSN="https://your-sentry-dsn@sentry.io/project"
SENTRY_ENVIRONMENT="production"
SENTRY_SAMPLE_RATE=0.1       # 10% of requests
SENTRY_TRACES_SAMPLE_RATE=0.1

# Performance monitoring
PERFORMANCE_MONITORING=True
METRICS_ENABLED=True
HEALTH_CHECK_ENABLED=True

# Monitoring endpoints
METRICS_PATH="/metrics"
HEALTH_CHECK_PATH="/health"
READY_CHECK_PATH="/ready"
```

### Prometheus Metrics

```bash
# Prometheus configuration
PROMETHEUS_ENABLED=True
PROMETHEUS_PORT=9090
PROMETHEUS_RETENTION_DAYS=15

# Custom metrics
TRACK_REQUEST_DURATION=True
TRACK_DATABASE_QUERIES=True
TRACK_EXTERNAL_API_CALLS=True
TRACK_WEBSOCKET_CONNECTIONS=True
```

## Frontend Configuration

### Vite Environment Variables

Frontend environment variables must be prefixed with `VITE_`:

```bash
# API Configuration
VITE_API_BASE_URL="https://api.fintradeagent.com"
VITE_WS_BASE_URL="wss://api.fintradeagent.com"

# Application settings
VITE_APP_NAME="FinTradeAgent"
VITE_APP_VERSION="1.0.0"
VITE_APP_ENV="production"

# Feature flags
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_DEBUG_TOOLS=false
VITE_ENABLE_PERFORMANCE_MONITORING=true

# CDN configuration
VITE_CDN_BASE_URL="https://cdn.fintradeagent.com"
VITE_STATIC_ASSETS_CDN=true
```

### Security Settings

```bash
# Content Security Policy
VITE_CSP_NONCE_REQUIRED=true
VITE_SECURE_COOKIES=true

# Performance settings
VITE_CACHE_DURATION=3600000
VITE_WEBSOCKET_HEARTBEAT_INTERVAL=30000
VITE_WEBSOCKET_RECONNECT_ATTEMPTS=5

# Monitoring
VITE_LOG_LEVEL="warn"
VITE_SENTRY_DSN="https://your-frontend-sentry-dsn"
VITE_PERFORMANCE_TRACKING=true
```

## Development vs Production

### Development Environment

```bash
# Development-specific settings
APP_ENV="development"
DEBUG=True
RELOAD=True

# Relaxed security
SSL_REDIRECT=False
CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"

# Verbose logging
LOG_LEVEL="DEBUG"
LOG_FORMAT="text"

# Local services
DATABASE_URL="postgresql://fintradeagent:password@localhost:5432/fintradeagent_dev"
REDIS_URL="redis://localhost:6379/0"
```

### Production Environment

```bash
# Production-specific settings
APP_ENV="production"
DEBUG=False
RELOAD=False

# Strict security
SSL_REDIRECT=True
CORS_ORIGINS="https://fintradeagent.com"

# Optimized logging
LOG_LEVEL="INFO"
LOG_FORMAT="json"

# Production services
DATABASE_URL="postgresql://fintradeagent:password@db:5432/fintradeagent_prod"
REDIS_URL="redis://redis:6379/0"
```

## Environment Variable Validation

### Required Variables

The following environment variables are required for the application to start:

#### Backend Required
- `SECRET_KEY`
- `JWT_SECRET_KEY`
- `DATABASE_URL`

#### Frontend Required
- `VITE_API_BASE_URL`
- `VITE_WS_BASE_URL`

### Optional Variables

All other variables have sensible defaults and are optional, but recommended for production use.

### Validation Script

Create a validation script to check environment configuration:

```bash
#!/bin/bash
# validate-env.sh

required_vars=(
    "SECRET_KEY"
    "JWT_SECRET_KEY"
    "DATABASE_URL"
)

echo "Validating environment configuration..."

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "ERROR: Required environment variable $var is not set"
        exit 1
    fi
done

# Check secret key length
if [ ${#SECRET_KEY} -lt 32 ]; then
    echo "ERROR: SECRET_KEY must be at least 32 characters long"
    exit 1
fi

if [ ${#JWT_SECRET_KEY} -lt 32 ]; then
    echo "ERROR: JWT_SECRET_KEY must be at least 32 characters long"
    exit 1
fi

echo "✅ Environment validation passed"
```

## Security Best Practices

### Secret Management

1. **Never commit secrets to version control**
2. **Use strong, randomly generated secrets**
3. **Rotate secrets regularly**
4. **Use environment-specific secrets**
5. **Restrict file permissions on .env files**

```bash
# Set proper permissions
chmod 600 .env.production
chown app:app .env.production
```

### Environment Separation

1. **Use different secrets for each environment**
2. **Use different databases for each environment**
3. **Use different external API keys when possible**
4. **Test configuration in staging before production**

This configuration guide ensures secure and optimal deployment of FinTradeAgent across different environments while maintaining flexibility and security best practices.