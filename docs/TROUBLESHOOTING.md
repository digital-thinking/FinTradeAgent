# FinTradeAgent Production Troubleshooting Guide

This guide covers common issues, diagnostic procedures, and solutions for production deployment problems.

## 📋 Table of Contents

1. [Quick Diagnostic Commands](#quick-diagnostic-commands)
2. [Application Issues](#application-issues)
3. [Database Issues](#database-issues)
4. [Network and SSL Issues](#network-and-ssl-issues)
5. [Performance Issues](#performance-issues)
6. [Container Issues](#container-issues)
7. [Monitoring and Logging Issues](#monitoring-and-logging-issues)
8. [Security Issues](#security-issues)
9. [Emergency Procedures](#emergency-procedures)

## Quick Diagnostic Commands

### System Health Check

```bash
# Check all services status
docker-compose -f docker-compose.production.yml ps

# Check system resources
docker stats --no-stream

# Check disk space
df -h

# Check memory usage
free -h

# Check network connectivity
netstat -tulpn | grep -E ':(80|443|8000|5432|6379)'
```

### Application Health Check

```bash
# Test application health endpoint
curl -k -s https://localhost/health | jq .

# Test API endpoints
curl -k -s https://localhost/api/system/health | jq .

# Check application logs
docker-compose -f docker-compose.production.yml logs --tail=50 app

# Check all container logs
docker-compose -f docker-compose.production.yml logs --tail=20
```

### Quick Service Restart

```bash
# Restart specific service
docker-compose -f docker-compose.production.yml restart app

# Restart all services
docker-compose -f docker-compose.production.yml restart

# Full recreation of services
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d
```

## Application Issues

### Issue: Application Won't Start

**Symptoms:**
- Container exits immediately
- "Application failed to start" in logs
- Health check fails

**Diagnostic Steps:**

```bash
# Check application logs
docker-compose -f docker-compose.production.yml logs app

# Check environment variables
docker-compose -f docker-compose.production.yml exec app env | grep -E '(SECRET_KEY|DATABASE_URL|JWT)'

# Test configuration loading
docker-compose -f docker-compose.production.yml exec app python -c "
from backend.config.production import production_settings
print('Configuration loaded successfully')
print(f'Database URL: {production_settings.database_url[:20]}...')
"
```

**Common Solutions:**

1. **Missing Environment Variables:**
   ```bash
   # Check required variables are set
   grep -E '^(SECRET_KEY|JWT_SECRET_KEY|DATABASE_URL)' .env.production
   
   # Generate missing secrets
   echo "SECRET_KEY=$(openssl rand -hex 32)" >> .env.production
   echo "JWT_SECRET_KEY=$(openssl rand -hex 32)" >> .env.production
   ```

2. **Invalid Configuration:**
   ```bash
   # Validate configuration syntax
   python -c "
   import os
   from pathlib import Path
   env_file = Path('.env.production')
   if env_file.exists():
       for line in env_file.read_text().split('\n'):
           if line.strip() and not line.startswith('#'):
               if '=' not in line:
                   print(f'Invalid line: {line}')
   "
   ```

3. **Permission Issues:**
   ```bash
   # Fix file permissions
   chmod 600 .env.production
   chown $USER:$USER .env.production
   ```

### Issue: High Memory Usage

**Symptoms:**
- Application consuming excessive memory
- Out of memory errors
- Container restarts

**Diagnostic Steps:**

```bash
# Monitor memory usage by container
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Check memory usage inside container
docker-compose -f docker-compose.production.yml exec app python -c "
import psutil
print(f'Memory usage: {psutil.virtual_memory().percent}%')
print(f'Available: {psutil.virtual_memory().available / (1024**3):.2f} GB')
"

# Check for memory leaks in application logs
docker-compose -f docker-compose.production.yml logs app | grep -i -E '(memory|leak|oom)'
```

**Solutions:**

1. **Increase Memory Limits:**
   ```yaml
   # In docker-compose.production.yml
   services:
     app:
       mem_limit: 2g  # Increase from 1g
   ```

2. **Optimize Application:**
   ```bash
   # Enable memory optimization
   echo "MEMORY_OPTIMIZATION_ENABLED=True" >> .env.production
   
   # Restart with optimizations
   docker-compose -f docker-compose.production.yml restart app
   ```

3. **Garbage Collection Tuning:**
   ```bash
   # Add to .env.production
   echo "PYTHONMALLOC=malloc" >> .env.production
   echo "MALLOC_TRIM_THRESHOLD_=100000" >> .env.production
   ```

### Issue: Slow Response Times

**Symptoms:**
- API responses taking >2 seconds
- Frontend loading slowly
- Timeout errors

**Diagnostic Steps:**

```bash
# Test response times
curl -w "@curl-format.txt" -s -o /dev/null https://localhost/api/system/health

# Create curl timing format file
cat > curl-format.txt << 'EOF'
     time_namelookup:  %{time_namelookup}\n
        time_connect:  %{time_connect}\n
     time_appconnect:  %{time_appconnect}\n
    time_pretransfer:  %{time_pretransfer}\n
       time_redirect:  %{time_redirect}\n
  time_starttransfer:  %{time_starttransfer}\n
                     ----------\n
          time_total:  %{time_total}\n
EOF

# Check database query performance
docker-compose -f docker-compose.production.yml exec db psql -U fintradeagent -d fintradeagent_prod -c "
SELECT query, calls, total_time, mean_time, rows 
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;"
```

**Solutions:**

1. **Database Optimization:**
   ```sql
   -- Connect to database and run:
   -- Add missing indexes
   CREATE INDEX CONCURRENTLY idx_portfolio_user_id ON portfolios(user_id);
   CREATE INDEX CONCURRENTLY idx_trades_created_at ON trades(created_at);
   
   -- Update statistics
   ANALYZE;
   ```

2. **Enable Caching:**
   ```bash
   # Ensure Redis is working
   docker-compose -f docker-compose.production.yml exec redis redis-cli ping
   
   # Enable application caching
   echo "CACHE_ENABLED=True" >> .env.production
   echo "CACHE_DEFAULT_TTL=3600" >> .env.production
   ```

3. **Increase Worker Processes:**
   ```bash
   # Increase workers in .env.production
   sed -i 's/WORKERS=4/WORKERS=8/' .env.production
   docker-compose -f docker-compose.production.yml restart app
   ```

## Database Issues

### Issue: Database Connection Failed

**Symptoms:**
- "Connection refused" errors
- "Database is unavailable"
- Application can't connect to PostgreSQL

**Diagnostic Steps:**

```bash
# Check database container status
docker-compose -f docker-compose.production.yml ps db

# Test database connectivity
docker-compose -f docker-compose.production.yml exec db pg_isready -U fintradeagent

# Check database logs
docker-compose -f docker-compose.production.yml logs db

# Test connection from application container
docker-compose -f docker-compose.production.yml exec app python -c "
import os, psycopg2
try:
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    print('Database connection successful')
    conn.close()
except Exception as e:
    print(f'Database connection failed: {e}')
"
```

**Solutions:**

1. **Restart Database:**
   ```bash
   docker-compose -f docker-compose.production.yml restart db
   ```

2. **Check Database Credentials:**
   ```bash
   # Verify credentials in environment
   echo $DATABASE_PASSWORD
   
   # Reset database password if needed
   docker-compose -f docker-compose.production.yml exec db psql -U postgres -c "
   ALTER USER fintradeagent WITH PASSWORD 'new-password';"
   ```

3. **Recreate Database:**
   ```bash
   # Backup data first!
   docker-compose -f docker-compose.production.yml exec db pg_dump -U fintradeagent fintradeagent_prod > backup.sql
   
   # Recreate database
   docker-compose -f docker-compose.production.yml down
   docker volume rm fintradeagent_postgres_data
   docker-compose -f docker-compose.production.yml up -d db
   
   # Restore data
   cat backup.sql | docker-compose -f docker-compose.production.yml exec -T db psql -U fintradeagent fintradeagent_prod
   ```

### Issue: Database Performance Issues

**Symptoms:**
- Slow query execution
- High database CPU usage
- Connection pool exhaustion

**Diagnostic Steps:**

```bash
# Check database performance
docker-compose -f docker-compose.production.yml exec db psql -U fintradeagent -d fintradeagent_prod -c "
SELECT * FROM pg_stat_activity WHERE state = 'active';
"

# Check slow queries
docker-compose -f docker-compose.production.yml exec db psql -U fintradeagent -d fintradeagent_prod -c "
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
WHERE mean_time > 1000 
ORDER BY mean_time DESC;
"

# Check connection count
docker-compose -f docker-compose.production.yml exec db psql -U fintradeagent -d fintradeagent_prod -c "
SELECT count(*) as connections FROM pg_stat_activity;
"
```

**Solutions:**

1. **Tune Database Configuration:**
   ```sql
   -- Increase connection limits
   ALTER SYSTEM SET max_connections = 200;
   
   -- Optimize memory settings
   ALTER SYSTEM SET shared_buffers = '256MB';
   ALTER SYSTEM SET effective_cache_size = '1GB';
   ALTER SYSTEM SET work_mem = '4MB';
   
   -- Restart database
   SELECT pg_reload_conf();
   ```

2. **Optimize Queries:**
   ```sql
   -- Add missing indexes
   CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_table_column ON table(column);
   
   -- Update table statistics
   ANALYZE;
   ```

3. **Connection Pool Tuning:**
   ```bash
   # Increase pool size in .env.production
   echo "DATABASE_POOL_MAX_SIZE=50" >> .env.production
   echo "DATABASE_POOL_MIN_SIZE=20" >> .env.production
   ```

## Network and SSL Issues

### Issue: SSL Certificate Problems

**Symptoms:**
- "Certificate expired" errors
- "SSL handshake failed"
- Browser security warnings

**Diagnostic Steps:**

```bash
# Check certificate validity
openssl x509 -in ssl/server.crt -text -noout | grep -A 2 "Validity"

# Test SSL handshake
openssl s_client -connect localhost:443 -servername fintradeagent.com

# Check certificate files
ls -la ssl/
```

**Solutions:**

1. **Renew Let's Encrypt Certificate:**
   ```bash
   # Renew certificate
   sudo certbot renew --dry-run
   sudo certbot renew
   
   # Update certificate files
   sudo cp /etc/letsencrypt/live/fintradeagent.com/fullchain.pem ssl/server.crt
   sudo cp /etc/letsencrypt/live/fintradeagent.com/privkey.pem ssl/server.key
   sudo chown $USER:$USER ssl/*
   
   # Restart nginx
   docker-compose -f docker-compose.production.yml restart nginx
   ```

2. **Generate New Self-Signed Certificate:**
   ```bash
   # Generate new certificate
   openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
     -keyout ssl/server.key \
     -out ssl/server.crt \
     -subj "/C=US/ST=State/L=City/O=Org/CN=fintradeagent.com"
   ```

### Issue: CORS Errors

**Symptoms:**
- "CORS policy" errors in browser
- Frontend can't connect to API
- Preflight request failures

**Diagnostic Steps:**

```bash
# Test CORS headers
curl -H "Origin: https://fintradeagent.com" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: X-Requested-With" \
     -X OPTIONS \
     https://localhost/api/portfolios/

# Check CORS configuration
grep CORS .env.production
```

**Solutions:**

1. **Update CORS Settings:**
   ```bash
   # Add your domain to CORS origins
   echo "CORS_ORIGINS=https://fintradeagent.com,https://www.fintradeagent.com" >> .env.production
   
   # Restart application
   docker-compose -f docker-compose.production.yml restart app
   ```

2. **Verify Nginx Configuration:**
   ```bash
   # Check nginx CORS headers
   docker-compose -f docker-compose.production.yml exec nginx nginx -t
   
   # Reload nginx configuration
   docker-compose -f docker-compose.production.yml restart nginx
   ```

## Performance Issues

### Issue: High CPU Usage

**Symptoms:**
- CPU usage consistently >80%
- Slow response times
- System unresponsive

**Diagnostic Steps:**

```bash
# Monitor CPU usage by container
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Check system load
uptime
cat /proc/loadavg

# Identify CPU-intensive processes
top -c
```

**Solutions:**

1. **Scale Services:**
   ```bash
   # Increase worker count
   echo "WORKERS=8" >> .env.production
   docker-compose -f docker-compose.production.yml restart app
   ```

2. **Optimize Code:**
   ```bash
   # Enable performance optimizations
   echo "PERFORMANCE_OPTIMIZATION_ENABLED=True" >> .env.production
   echo "ASYNC_WORKER_POOL_SIZE=50" >> .env.production
   ```

3. **Add Resource Limits:**
   ```yaml
   # In docker-compose.production.yml
   services:
     app:
       cpus: '2.0'  # Limit CPU usage
   ```

### Issue: Disk Space Full

**Symptoms:**
- "No space left on device" errors
- Application crashes
- Database write failures

**Diagnostic Steps:**

```bash
# Check disk usage
df -h

# Find large files
du -sh /* | sort -hr | head -10

# Check Docker disk usage
docker system df
```

**Solutions:**

1. **Clean Up Docker:**
   ```bash
   # Remove unused containers and images
   docker system prune -a
   
   # Remove unused volumes
   docker volume prune
   ```

2. **Clean Up Logs:**
   ```bash
   # Rotate application logs
   docker-compose -f docker-compose.production.yml exec app \
     logrotate -f /etc/logrotate.conf
   
   # Clean old log files
   find /var/log -name "*.log.*" -mtime +7 -delete
   ```

3. **Expand Storage:**
   ```bash
   # Add disk space or move to larger instance
   # Configure log rotation in docker-compose.yml
   logging:
     driver: "json-file"
     options:
       max-size: "10m"
       max-file: "3"
   ```

## Container Issues

### Issue: Container Keeps Restarting

**Symptoms:**
- Container in restart loop
- Service unavailable intermittently
- Health check failures

**Diagnostic Steps:**

```bash
# Check container status
docker-compose -f docker-compose.production.yml ps

# Check restart count
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Check container logs
docker-compose -f docker-compose.production.yml logs --tail=100 app

# Check health check logs
docker inspect $(docker-compose -f docker-compose.production.yml ps -q app) | jq '.[0].State.Health'
```

**Solutions:**

1. **Fix Health Check:**
   ```bash
   # Test health check manually
   docker-compose -f docker-compose.production.yml exec app curl -f http://localhost:8000/health
   
   # Adjust health check in docker-compose.yml
   healthcheck:
     test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
     interval: 30s
     timeout: 10s
     retries: 5
     start_period: 60s  # Increase start period
   ```

2. **Increase Memory/CPU Limits:**
   ```yaml
   services:
     app:
       mem_limit: 2g
       cpus: '2.0'
   ```

3. **Fix Application Issues:**
   ```bash
   # Check for application errors
   docker-compose -f docker-compose.production.yml logs app | grep -i error
   
   # Run application directly to debug
   docker-compose -f docker-compose.production.yml run --rm app python -c "
   from backend.main_production import app
   print('Application imports successfully')
   "
   ```

## Monitoring and Logging Issues

### Issue: Logs Not Appearing

**Symptoms:**
- Empty log files
- Missing application logs
- Monitoring gaps

**Diagnostic Steps:**

```bash
# Check log volume mounts
docker-compose -f docker-compose.production.yml exec app ls -la /var/log/fintradeagent/

# Check logging configuration
docker-compose -f docker-compose.production.yml exec app python -c "
import logging
logger = logging.getLogger()
print(f'Log level: {logger.level}')
print(f'Handlers: {logger.handlers}')
"

# Test logging
docker-compose -f docker-compose.production.yml exec app python -c "
import logging
logging.info('Test log message')
"
```

**Solutions:**

1. **Fix Log Directory Permissions:**
   ```bash
   # Create log directory
   docker-compose -f docker-compose.production.yml exec app mkdir -p /var/log/fintradeagent
   
   # Fix permissions
   docker-compose -f docker-compose.production.yml exec app chown -R appuser:appgroup /var/log/fintradeagent
   ```

2. **Configure Logging:**
   ```bash
   # Set appropriate log level
   echo "LOG_LEVEL=INFO" >> .env.production
   
   # Enable file logging
   echo "LOG_FILE=/var/log/fintradeagent/app.log" >> .env.production
   ```

### Issue: Monitoring Services Down

**Symptoms:**
- Prometheus/Grafana unreachable
- No metrics data
- Monitoring dashboards empty

**Diagnostic Steps:**

```bash
# Check monitoring services
docker-compose -f docker-compose.production.yml ps prometheus grafana

# Check monitoring logs
docker-compose -f docker-compose.production.yml logs prometheus grafana

# Test Prometheus targets
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
```

**Solutions:**

1. **Restart Monitoring Services:**
   ```bash
   docker-compose -f docker-compose.production.yml restart prometheus grafana
   ```

2. **Check Configuration:**
   ```bash
   # Verify Prometheus config
   docker-compose -f docker-compose.production.yml exec prometheus promtool check config /etc/prometheus/prometheus.yml
   
   # Check Grafana datasource
   curl -s -u admin:$GRAFANA_ADMIN_PASSWORD http://localhost:3001/api/datasources
   ```

## Emergency Procedures

### Complete System Recovery

```bash
#!/bin/bash
# emergency-recovery.sh

echo "Starting emergency recovery procedure..."

# 1. Stop all services
docker-compose -f docker-compose.production.yml down

# 2. Backup current state
mkdir -p emergency-backup-$(date +%Y%m%d_%H%M%S)
docker volume ls | grep fintradeagent | awk '{print $2}' | while read volume; do
    docker run --rm -v $volume:/data -v $(pwd)/emergency-backup-$(date +%Y%m%d_%H%M%S):/backup alpine tar czf /backup/${volume}.tar.gz -C /data .
done

# 3. Clean up problematic containers
docker system prune -f

# 4. Restore from last known good backup (if available)
# RESTORE_DATE="20240101_120000"
# docker volume create fintradeagent_postgres_data
# docker run --rm -v fintradeagent_postgres_data:/data -v $(pwd)/backups:/backup alpine tar xzf /backup/postgres_data_$RESTORE_DATE.tar.gz -C /data

# 5. Start services with fresh state
docker-compose -f docker-compose.production.yml up -d

# 6. Verify services
sleep 30
docker-compose -f docker-compose.production.yml ps

echo "Emergency recovery completed. Check service status."
```

### Rollback Procedure

```bash
#!/bin/bash
# rollback.sh

echo "Starting rollback procedure..."

# Stop current services
docker-compose -f docker-compose.production.yml down

# Switch to previous version
git checkout HEAD~1

# Rebuild with previous version
docker-compose -f docker-compose.production.yml build

# Start services
docker-compose -f docker-compose.production.yml up -d

echo "Rollback completed"
```

### Health Check Script

```bash
#!/bin/bash
# health-check.sh

echo "=== FinTradeAgent Health Check ==="

# Check services
echo "Checking services..."
docker-compose -f docker-compose.production.yml ps

# Check endpoints
echo "Checking endpoints..."
curl -s -o /dev/null -w "%{http_code}" https://localhost/health
echo " - Health endpoint"

curl -s -o /dev/null -w "%{http_code}" https://localhost/api/system/health
echo " - API health endpoint"

# Check resources
echo "Checking resources..."
df -h | grep -E '/$|/var'
free -h
uptime

# Check logs for errors
echo "Checking for recent errors..."
docker-compose -f docker-compose.production.yml logs --since="1h" | grep -i error | tail -5

echo "Health check completed"
```

This troubleshooting guide provides comprehensive solutions for common production issues. Always backup your data before making significant changes, and test solutions in a staging environment when possible.