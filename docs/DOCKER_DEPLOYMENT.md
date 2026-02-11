# Docker Deployment Guide

This guide covers Docker containerization and deployment for FinTradeAgent.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Container Architecture](#container-architecture)
- [Environment Setup](#environment-setup)
- [Development Deployment](#development-deployment)
- [Production Deployment](#production-deployment)
- [Monitoring Stack](#monitoring-stack)
- [Backup and Recovery](#backup-and-recovery)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)

## Overview

FinTradeAgent uses a multi-container Docker setup with the following components:

- **Application Container**: FastAPI backend + Vue.js frontend
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Reverse Proxy**: Nginx
- **Background Tasks**: Celery worker and beat
- **Monitoring**: Prometheus, Grafana, and various exporters

## Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- At least 4GB RAM and 20GB disk space
- Linux/macOS/Windows with WSL2

### Installation

```bash
# Install Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## Container Architecture

### Multi-Stage Production Build

The production Dockerfile uses a multi-stage build:

1. **Frontend Builder**: Node.js 18 Alpine for Vue.js build
2. **Backend Builder**: Python 3.11 for dependency installation
3. **Production Runtime**: Minimal Python 3.11 slim with built assets

### Network Architecture

```
Internet
    ↓
┌─────────────┐
│    Nginx    │ :80, :443
│ (Reverse    │
│  Proxy)     │
└─────────────┘
    ↓
┌─────────────┐
│ FastAPI App │ :8000
│ (Backend +  │
│  Frontend)  │
└─────────────┘
    ↓ ↓
┌──────────┐  ┌─────────┐
│PostgreSQL│  │  Redis  │
│   :5432  │  │  :6379  │
└──────────┘  └─────────┘
```

## Environment Setup

### Environment Files

Create environment files for each environment:

#### Production (`.env.production`)
```env
# Database
DATABASE_PASSWORD=your_secure_password
DATABASE_URL=postgresql://fintradeagent:${DATABASE_PASSWORD}@db:5432/fintradeagent_prod

# Redis
REDIS_PASSWORD=your_redis_password
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

# Application
SECRET_KEY=your_very_secure_secret_key_here
JWT_SECRET_KEY=your_jwt_secret_key_here
APP_ENV=production

# API Keys
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
ALPHA_VANTAGE_API_KEY=your_alphavantage_key

# Monitoring
GRAFANA_ADMIN_PASSWORD=your_grafana_password
SENTRY_DSN=your_sentry_dsn

# SSL (if using)
SSL_CERT_PATH=/etc/nginx/ssl/cert.pem
SSL_KEY_PATH=/etc/nginx/ssl/key.pem
```

#### Development (`.env.development`)
```env
# Database
DATABASE_URL=postgresql://fintradeagent_dev:dev_password_123@db-dev:5432/fintradeagent_dev

# Redis
REDIS_URL=redis://:dev_redis_123@redis-dev:6379/0

# Application
SECRET_KEY=dev-secret-key-do-not-use-in-production
JWT_SECRET_KEY=dev-jwt-secret-do-not-use-in-production
APP_ENV=development
DEBUG=true

# API Keys (optional for development)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
ALPHA_VANTAGE_API_KEY=your_alphavantage_key
```

### SSL Certificates (Production)

For HTTPS in production, place certificates in the `ssl/` directory:

```bash
mkdir -p ssl
# Copy your certificates
cp your-cert.pem ssl/cert.pem
cp your-key.pem ssl/key.pem
```

Or use Let's Encrypt:

```bash
# Install certbot
sudo apt install certbot

# Generate certificate
sudo certbot certonly --standalone -d your-domain.com
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/key.pem
```

## Development Deployment

### Quick Start

```bash
# Clone the repository
git clone <repo-url>
cd FinTradeAgent

# Create environment file
cp .env.development .env.development

# Start development services
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f
```

### Development Services

The development environment includes:

- **Frontend**: http://localhost:3000 (Hot reload enabled)
- **Backend**: http://localhost:8001 (Auto-reload enabled)
- **Database Admin**: http://localhost:8080 (Adminer)
- **Redis Admin**: http://localhost:8081 (Redis Commander)
- **Mail Testing**: http://localhost:8025 (MailHog)

### Development Features

- **Hot Reload**: Both frontend and backend auto-reload on changes
- **Debug Ports**: Backend debug port 5678 for IDE attachment
- **Sample Data**: Development database includes sample portfolios and trades
- **Admin Tools**: Adminer for database, Redis Commander for cache
- **Email Testing**: MailHog captures outbound emails

### Development Commands

```bash
# Start services
docker-compose -f docker-compose.dev.yml up -d

# View logs for specific service
docker-compose -f docker-compose.dev.yml logs -f backend-dev

# Execute commands in container
docker-compose -f docker-compose.dev.yml exec backend-dev python -m pytest

# Rebuild specific service
docker-compose -f docker-compose.dev.yml build --no-cache backend-dev

# Stop and remove all containers
docker-compose -f docker-compose.dev.yml down -v
```

## Production Deployment

### Automated Deployment

Use the deployment script for production:

```bash
# Deploy with monitoring
./scripts/deploy.sh production --monitoring

# Deploy with rebuild
./scripts/deploy.sh production --rebuild --monitoring

# Deploy without backup
./scripts/deploy.sh production --no-backup
```

### Manual Deployment

```bash
# Create environment file
cp .env.production .env.production
# Edit with your values

# Build and start services
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d

# Run database migrations
docker-compose -f docker-compose.production.yml exec app python -m alembic upgrade head

# Check status
docker-compose -f docker-compose.production.yml ps
```

### Production Services

- **Application**: http://localhost:8000 or https://your-domain.com
- **API Docs**: https://your-domain.com/docs
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001

### Production Security

The production setup includes:

- **Non-root containers**: All services run as non-privileged users
- **Security hardening**: no-new-privileges, resource limits
- **Network isolation**: Services communicate via internal network
- **SSL/TLS encryption**: HTTPS with proper certificates
- **Secrets management**: Environment variables for sensitive data

## Monitoring Stack

### Enable Monitoring

```bash
# Deploy with monitoring
docker-compose -f docker-compose.production.yml -f docker-compose.monitoring.yml up -d

# Or use deployment script
./scripts/deploy.sh production --monitoring
```

### Monitoring Components

1. **Prometheus**: Metrics collection and alerting
2. **Grafana**: Dashboards and visualization
3. **Node Exporter**: System metrics
4. **PostgreSQL Exporter**: Database metrics
5. **Redis Exporter**: Cache metrics
6. **cAdvisor**: Container metrics
7. **Nginx Exporter**: Web server metrics

### Grafana Dashboards

Access Grafana at http://localhost:3001 with admin credentials from environment.

Pre-configured dashboards:
- **FinTradeAgent Overview**: Application metrics and health
- **System Metrics**: CPU, memory, disk, network
- **Database Performance**: PostgreSQL statistics
- **Container Metrics**: Docker container resource usage

### Alerts Configuration

Prometheus alerts are configured in `monitoring/alert_rules.yml`:

```yaml
groups:
  - name: fintradeagent
    rules:
      - alert: HighErrorRate
        expr: rate(fastapi_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: High error rate detected
```

## Backup and Recovery

### Automated Backups

```bash
# Create backup
./scripts/backup.sh --environment production

# Create backup with S3 upload
./scripts/backup.sh --environment production --s3-bucket my-backups

# Schedule daily backups (crontab)
0 2 * * * /path/to/FinTradeAgent/scripts/backup.sh --environment production
```

### Manual Backup

```bash
# Database backup
docker exec fintradeagent-db pg_dump -U fintradeagent fintradeagent_prod > backup.sql

# Application data backup
docker run --rm -v fintradeagent_app_data:/data:ro -v $(pwd):/backup alpine tar czf /backup/app_data.tar.gz -C /data .
```

### Recovery Process

```bash
# Restore database
docker exec -i fintradeagent-db psql -U fintradeagent -d fintradeagent_prod < backup.sql

# Restore application data
docker run --rm -v fintradeagent_app_data:/data -v $(pwd):/backup alpine tar xzf /backup/app_data.tar.gz -C /data
```

## Health Checks

### Automated Health Monitoring

```bash
# Run health check
./scripts/health-check.sh --environment production --verbose

# Run with webhook notification
./scripts/health-check.sh --environment production --webhook https://hooks.slack.com/...

# JSON output for monitoring systems
./scripts/health-check.sh --environment production --json
```

### Manual Health Checks

```bash
# Application health
curl http://localhost:8000/health

# Container status
docker-compose -f docker-compose.production.yml ps

# Service logs
docker-compose -f docker-compose.production.yml logs -f --tail=100 app
```

## Troubleshooting

### Common Issues

#### 1. Container Won't Start

```bash
# Check logs
docker-compose logs service-name

# Check resource usage
docker stats

# Check disk space
df -h
```

#### 2. Database Connection Issues

```bash
# Check database health
docker exec fintradeagent-db pg_isready -U fintradeagent

# Check connection from app
docker exec fintradeagent-app python -c "
from sqlalchemy import create_engine
import os
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    print(conn.execute('SELECT version()').fetchone())
"
```

#### 3. Performance Issues

```bash
# Check container resources
docker stats --no-stream

# Check disk I/O
iostat -x 1

# Check database performance
docker exec fintradeagent-db psql -U fintradeagent -d fintradeagent_prod -c "
SELECT query, calls, mean_time, total_time
FROM pg_stat_statements
ORDER BY total_time DESC LIMIT 10;
"
```

#### 4. Network Issues

```bash
# Check network connectivity
docker network ls
docker network inspect fintradeagent-network

# Test connectivity between containers
docker exec fintradeagent-app curl -f http://db:5432
```

### Log Analysis

```bash
# View all logs
docker-compose -f docker-compose.production.yml logs

# Filter by service
docker-compose -f docker-compose.production.yml logs app

# Follow logs in real-time
docker-compose -f docker-compose.production.yml logs -f --tail=100

# Search logs for errors
docker-compose -f docker-compose.production.yml logs | grep -i error
```

### Performance Tuning

#### Database Optimization

```sql
-- Monitor slow queries
SELECT query, calls, mean_time, total_time, rows
FROM pg_stat_statements
WHERE mean_time > 100
ORDER BY mean_time DESC LIMIT 20;

-- Check index usage
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE tablename = 'your_table_name';
```

#### Container Resource Limits

```yaml
# docker-compose.yml
services:
  app:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
```

## Security Considerations

### Container Security

1. **Use minimal base images** (Alpine Linux)
2. **Run as non-root user**
3. **Apply security updates regularly**
4. **Limit container privileges**
5. **Use secrets management**

### Network Security

1. **Internal networks only** for inter-service communication
2. **TLS encryption** for external connections
3. **Firewall rules** to restrict access
4. **Regular security scanning**

### Data Security

1. **Encrypt data at rest** (database encryption)
2. **Secure backup storage**
3. **Rotate secrets regularly**
4. **Monitor for unauthorized access**

### Security Scanning

```bash
# Scan images for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd):/tmp anchore/syft fintradeagent:latest

# Check for secrets in images
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  trufflesecurity/trufflehog:latest docker --image fintradeagent:latest
```

## Scaling and Orchestration

### Horizontal Scaling

```bash
# Scale application containers
docker-compose -f docker-compose.production.yml up -d --scale app=3

# Scale worker containers
docker-compose -f docker-compose.production.yml up -d --scale celery-worker=2
```

### Kubernetes Migration

For production at scale, consider migrating to Kubernetes:

```yaml
# Example deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fintradeagent-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fintradeagent-app
  template:
    metadata:
      labels:
        app: fintradeagent-app
    spec:
      containers:
      - name: app
        image: fintradeagent:latest
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

## Maintenance

### Regular Tasks

1. **Update base images** monthly
2. **Rotate secrets** quarterly
3. **Review logs** weekly
4. **Performance tuning** as needed
5. **Backup verification** monthly

### Update Process

```bash
# Update to latest images
docker-compose -f docker-compose.production.yml pull

# Restart services with new images
docker-compose -f docker-compose.production.yml up -d

# Clean up old images
docker image prune -f
```

### Monitoring Maintenance

```bash
# Clean up old metrics
docker exec fintradeagent-prometheus prometheus --storage.tsdb.retention.time=30d

# Restart Grafana to apply config changes
docker-compose restart grafana
```

This deployment guide provides comprehensive coverage of Docker containerization for FinTradeAgent, from development to production deployment with monitoring, security, and maintenance considerations.