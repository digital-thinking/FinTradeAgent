# FinTradeAgent Production Deployment Guide

This guide covers the complete production deployment process for FinTradeAgent, including security configurations, monitoring setup, and operational procedures.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Security Setup](#security-setup)
4. [Database Configuration](#database-configuration)
5. [Application Deployment](#application-deployment)
6. [Monitoring and Logging](#monitoring-and-logging)
7. [SSL/TLS Configuration](#ssltls-configuration)
8. [Performance Optimization](#performance-optimization)
9. [Backup and Recovery](#backup-and-recovery)
10. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Operating System**: Ubuntu 20.04+ / CentOS 8+ / RHEL 8+
- **Memory**: Minimum 8GB RAM (16GB recommended)
- **CPU**: Minimum 4 cores (8 cores recommended)
- **Disk**: Minimum 50GB SSD storage (100GB recommended)
- **Network**: Stable internet connection with static IP

### Software Dependencies

```bash
# Docker and Docker Compose
sudo apt update
sudo apt install -y docker.io docker-compose

# Enable and start Docker
sudo systemctl enable docker
sudo systemctl start docker

# Add user to docker group
sudo usermod -aG docker $USER

# PostgreSQL client tools (for management)
sudo apt install -y postgresql-client

# SSL certificate tools
sudo apt install -y certbot

# System monitoring tools
sudo apt install -y htop iotop netstat-nat
```

### Domain and DNS Setup

1. Configure DNS records for your domain:
   ```
   A     fintradeagent.com        → YOUR_SERVER_IP
   A     www.fintradeagent.com    → YOUR_SERVER_IP
   CNAME api.fintradeagent.com    → fintradeagent.com
   ```

2. Verify DNS propagation:
   ```bash
   nslookup fintradeagent.com
   nslookup www.fintradeagent.com
   ```

## Environment Configuration

### 1. Create Production Environment File

Copy the template and customize:

```bash
cp .env.production .env.prod
chmod 600 .env.prod  # Restrict access
```

### 2. Generate Security Keys

```bash
# Generate secret keys
export SECRET_KEY=$(openssl rand -hex 32)
export JWT_SECRET_KEY=$(openssl rand -hex 32)
export DATABASE_PASSWORD=$(openssl rand -hex 16)
export REDIS_PASSWORD=$(openssl rand -hex 16)

# Add to environment file
echo "SECRET_KEY=${SECRET_KEY}" >> .env.prod
echo "JWT_SECRET_KEY=${JWT_SECRET_KEY}" >> .env.prod
echo "DATABASE_PASSWORD=${DATABASE_PASSWORD}" >> .env.prod
echo "REDIS_PASSWORD=${REDIS_PASSWORD}" >> .env.prod
```

### 3. Configure External APIs

Add your API keys to the environment file:

```bash
# OpenAI API Key
echo "OPENAI_API_KEY=your_openai_api_key" >> .env.prod

# Anthropic API Key
echo "ANTHROPIC_API_KEY=your_anthropic_api_key" >> .env.prod

# Alpha Vantage API Key
echo "ALPHA_VANTAGE_API_KEY=your_alphavantage_api_key" >> .env.prod

# Sentry DSN (optional, for error tracking)
echo "SENTRY_DSN=your_sentry_dsn" >> .env.prod

# Grafana admin password
echo "GRAFANA_ADMIN_PASSWORD=$(openssl rand -hex 12)" >> .env.prod
```

## Security Setup

### 1. Firewall Configuration

```bash
# Enable UFW firewall
sudo ufw enable

# Allow SSH (adjust port as needed)
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow specific ports for monitoring (optional)
sudo ufw allow from 10.0.0.0/8 to any port 9090  # Prometheus
sudo ufw allow from 10.0.0.0/8 to any port 3001  # Grafana

# Check firewall status
sudo ufw status verbose
```

### 2. SSL Certificate Setup

#### Option A: Let's Encrypt (Free)

```bash
# Install certbot
sudo apt install certbot

# Generate certificate
sudo certbot certonly --standalone \
  -d fintradeagent.com \
  -d www.fintradeagent.com \
  --email your-email@example.com \
  --agree-tos \
  --no-eff-email

# Copy certificates to project directory
sudo mkdir -p ./ssl
sudo cp /etc/letsencrypt/live/fintradeagent.com/fullchain.pem ./ssl/server.crt
sudo cp /etc/letsencrypt/live/fintradeagent.com/privkey.pem ./ssl/server.key
sudo chown $USER:$USER ./ssl/*
chmod 600 ./ssl/server.key
```

#### Option B: Custom Certificate

```bash
# Generate private key and certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ./ssl/server.key \
  -out ./ssl/server.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=fintradeagent.com"

chmod 600 ./ssl/server.key
```

### 3. System Security Hardening

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Configure automatic security updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# Disable unnecessary services
sudo systemctl disable bluetooth
sudo systemctl disable cups
sudo systemctl disable avahi-daemon

# Configure fail2ban (optional but recommended)
sudo apt install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

## Database Configuration

### 1. Database Initialization

The PostgreSQL database will be automatically initialized when Docker containers start. However, you can perform additional setup:

```bash
# Connect to database (after containers are running)
docker-compose -f docker-compose.production.yml exec db psql -U fintradeagent -d fintradeagent_prod

# Create additional users or configurations as needed
```

### 2. Database Backup Setup

```bash
# Create backup directory
sudo mkdir -p /var/backups/fintradeagent
sudo chown $USER:$USER /var/backups/fintradeagent

# Create backup script
cat > backup-database.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/var/backups/fintradeagent"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/fintradeagent_backup_$DATE.sql"

# Create backup
docker-compose -f docker-compose.production.yml exec -T db \
  pg_dump -U fintradeagent fintradeagent_prod > "$BACKUP_FILE"

# Compress backup
gzip "$BACKUP_FILE"

# Remove backups older than 30 days
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: ${BACKUP_FILE}.gz"
EOF

chmod +x backup-database.sh

# Setup cron job for daily backups
(crontab -l 2>/dev/null; echo "0 2 * * * $(pwd)/backup-database.sh") | crontab -
```

## Application Deployment

### 1. Build Production Images

```bash
# Build the application
./scripts/build-production.sh

# Or build directly with Docker Compose
docker-compose -f docker-compose.production.yml build
```

### 2. Deploy Services

```bash
# Load environment variables
export $(cat .env.prod | xargs)

# Start all services
docker-compose -f docker-compose.production.yml up -d

# Check service status
docker-compose -f docker-compose.production.yml ps

# View logs
docker-compose -f docker-compose.production.yml logs -f
```

### 3. Verify Deployment

```bash
# Test health endpoint
curl -k https://your-domain.com/health

# Test API endpoint
curl -k https://your-domain.com/api/system/health

# Check application logs
docker-compose -f docker-compose.production.yml logs app

# Monitor resource usage
docker stats
```

### 4. Database Migrations

```bash
# Run database migrations (if needed)
docker-compose -f docker-compose.production.yml exec app \
  python -m alembic upgrade head
```

## Monitoring and Logging

### 1. Log Management

Logs are stored in Docker volumes and can be accessed:

```bash
# Application logs
docker-compose -f docker-compose.production.yml logs -f app

# Database logs
docker-compose -f docker-compose.production.yml logs -f db

# Nginx logs
docker-compose -f docker-compose.production.yml logs -f nginx

# Export logs to host system (optional)
docker-compose -f docker-compose.production.yml exec app \
  cat /var/log/fintradeagent/app.log > ./logs/app.log
```

### 2. Monitoring Setup

Access monitoring dashboards:

- **Prometheus**: http://your-domain.com:9090
- **Grafana**: http://your-domain.com:3001
  - Username: `admin`
  - Password: See `GRAFANA_ADMIN_PASSWORD` in `.env.prod`

### 3. Alerting Configuration

Configure alerts in Grafana:

1. Go to Alerting → Notification channels
2. Add notification channels (email, Slack, etc.)
3. Create alert rules for critical metrics:
   - High error rate (>5%)
   - High response time (>2s)
   - High memory usage (>90%)
   - Database connection issues

## SSL/TLS Configuration

### 1. Certificate Renewal

For Let's Encrypt certificates:

```bash
# Test renewal
sudo certbot renew --dry-run

# Setup automatic renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet --post-hook "docker-compose -f /path/to/docker-compose.production.yml restart nginx"
```

### 2. SSL Testing

Test SSL configuration:

```bash
# Test SSL setup
openssl s_client -connect your-domain.com:443 -servername your-domain.com

# Check certificate expiration
openssl s_client -connect your-domain.com:443 -servername your-domain.com 2>/dev/null | openssl x509 -noout -dates
```

## Performance Optimization

### 1. System Tuning

```bash
# Increase file descriptor limits
echo "fs.file-max = 65536" | sudo tee -a /etc/sysctl.conf
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# Optimize network settings
echo "net.core.somaxconn = 65536" | sudo tee -a /etc/sysctl.conf
echo "net.ipv4.tcp_max_syn_backlog = 65536" | sudo tee -a /etc/sysctl.conf

# Apply changes
sudo sysctl -p
```

### 2. Container Resource Limits

Resource limits are configured in `docker-compose.production.yml`:

- **App**: 1GB memory, 1 CPU
- **Database**: 512MB memory, 0.5 CPU
- **Redis**: 256MB memory, 0.25 CPU
- **Nginx**: 128MB memory, 0.25 CPU

Adjust based on your server specifications.

### 3. Database Tuning

```sql
-- Connect to PostgreSQL and run:
-- Increase shared_buffers (25% of total RAM)
ALTER SYSTEM SET shared_buffers = '2GB';

-- Increase effective_cache_size (75% of total RAM)
ALTER SYSTEM SET effective_cache_size = '6GB';

-- Optimize for write-heavy workloads
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;

-- Restart PostgreSQL
SELECT pg_reload_conf();
```

## Backup and Recovery

### 1. Full System Backup

```bash
# Create backup script
cat > full-backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/var/backups/fintradeagent-full"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Stop services
docker-compose -f docker-compose.production.yml stop

# Backup Docker volumes
docker run --rm -v fintradeagent_postgres_data:/data -v "$BACKUP_DIR":/backup alpine tar czf /backup/postgres_data_$DATE.tar.gz -C /data .
docker run --rm -v fintradeagent_redis_data:/data -v "$BACKUP_DIR":/backup alpine tar czf /backup/redis_data_$DATE.tar.gz -C /data .
docker run --rm -v fintradeagent_app_data:/data -v "$BACKUP_DIR":/backup alpine tar czf /backup/app_data_$DATE.tar.gz -C /data .

# Backup configuration files
tar czf "$BACKUP_DIR/config_$DATE.tar.gz" .env.prod nginx/ ssl/

# Start services
docker-compose -f docker-compose.production.yml start

echo "Full backup completed: $BACKUP_DIR"
EOF

chmod +x full-backup.sh
```

### 2. Disaster Recovery

```bash
# Restore from backup (example)
BACKUP_DATE="20240101_120000"
BACKUP_DIR="/var/backups/fintradeagent-full"

# Stop services
docker-compose -f docker-compose.production.yml down

# Restore volumes
docker volume create fintradeagent_postgres_data
docker run --rm -v fintradeagent_postgres_data:/data -v "$BACKUP_DIR":/backup alpine tar xzf /backup/postgres_data_$BACKUP_DATE.tar.gz -C /data

docker volume create fintradeagent_redis_data
docker run --rm -v fintradeagent_redis_data:/data -v "$BACKUP_DIR":/backup alpine tar xzf /backup/redis_data_$BACKUP_DATE.tar.gz -C /data

# Restore configuration
tar xzf "$BACKUP_DIR/config_$BACKUP_DATE.tar.gz"

# Start services
docker-compose -f docker-compose.production.yml up -d
```

## Troubleshooting

### Common Issues

#### 1. Application Won't Start

```bash
# Check logs
docker-compose -f docker-compose.production.yml logs app

# Common fixes:
# - Verify environment variables are set
# - Check database connection
# - Ensure SSL certificates exist
# - Verify port availability
```

#### 2. Database Connection Issues

```bash
# Test database connectivity
docker-compose -f docker-compose.production.yml exec app python -c "
import os
import psycopg2
conn = psycopg2.connect(os.environ['DATABASE_URL'])
print('Database connection successful')
conn.close()
"

# Check database logs
docker-compose -f docker-compose.production.yml logs db
```

#### 3. SSL Certificate Issues

```bash
# Verify certificate files
ls -la ssl/
openssl x509 -in ssl/server.crt -text -noout

# Test SSL handshake
openssl s_client -connect localhost:443 -servername your-domain.com
```

#### 4. High Memory Usage

```bash
# Monitor container resources
docker stats

# Check for memory leaks in application logs
docker-compose -f docker-compose.production.yml logs app | grep -i memory

# Restart services if needed
docker-compose -f docker-compose.production.yml restart
```

#### 5. Performance Issues

```bash
# Check system resources
htop
iotop

# Monitor application metrics
curl -s https://your-domain.com/metrics

# Check database performance
docker-compose -f docker-compose.production.yml exec db \
  psql -U fintradeagent -d fintradeagent_prod -c "
  SELECT query, calls, total_time, mean_time
  FROM pg_stat_statements
  ORDER BY total_time DESC
  LIMIT 10;"
```

### Maintenance Tasks

#### Daily Tasks
- [ ] Check application logs for errors
- [ ] Verify backup completion
- [ ] Monitor resource usage
- [ ] Check SSL certificate validity

#### Weekly Tasks
- [ ] Review security alerts
- [ ] Update system packages
- [ ] Analyze performance metrics
- [ ] Test disaster recovery procedures

#### Monthly Tasks
- [ ] Security audit
- [ ] Capacity planning review
- [ ] Update documentation
- [ ] Review and rotate logs

## Support and Resources

- **Documentation**: Located in `/docs/` directory
- **Configuration**: All config files in repository
- **Monitoring**: Access Grafana dashboards for real-time metrics
- **Logs**: Centralized logging in Docker containers
- **Backups**: Automated daily backups with 30-day retention

For additional support or questions, refer to the troubleshooting section or check application logs for specific error messages.