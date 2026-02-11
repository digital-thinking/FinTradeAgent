# Docker Troubleshooting Guide

This guide covers common Docker-related issues and their solutions for FinTradeAgent.

## Table of Contents

- [General Troubleshooting](#general-troubleshooting)
- [Container Issues](#container-issues)
- [Database Problems](#database-problems)
- [Network Connectivity](#network-connectivity)
- [Performance Issues](#performance-issues)
- [Storage and Volumes](#storage-and-volumes)
- [Security and Permissions](#security-and-permissions)
- [Monitoring and Logging](#monitoring-and-logging)
- [Development Environment](#development-environment)
- [Production Issues](#production-issues)

## General Troubleshooting

### Basic Diagnostic Commands

```bash
# Check Docker daemon status
sudo systemctl status docker

# Check container status
docker-compose -f docker-compose.production.yml ps

# View container logs
docker-compose -f docker-compose.production.yml logs service-name

# Check resource usage
docker stats --no-stream

# Check disk space
df -h

# Check available memory
free -h

# List all containers
docker ps -a

# Inspect container configuration
docker inspect container-name
```

### Health Check Commands

```bash
# Run comprehensive health check
./scripts/health-check.sh --environment production --verbose

# Check individual services
curl -f http://localhost:8000/health
curl -f http://localhost:8000/api/health

# Check database connectivity
docker exec fintradeagent-db pg_isready -U fintradeagent

# Check Redis connectivity
docker exec fintradeagent-redis redis-cli --pass $REDIS_PASSWORD ping
```

## Container Issues

### Container Won't Start

#### Symptom
Container exits immediately or fails to start

#### Diagnosis
```bash
# Check container logs
docker-compose logs service-name

# Check if image exists
docker images | grep fintradeagent

# Check for port conflicts
netstat -tulpn | grep :8000

# Check resource limits
docker system df
docker system events
```

#### Common Solutions

1. **Port already in use**
   ```bash
   # Find process using port
   lsof -i :8000
   
   # Kill process or change port
   sudo kill -9 PID
   # or modify docker-compose.yml ports
   ```

2. **Insufficient resources**
   ```bash
   # Check available resources
   docker system df
   docker system prune -f
   
   # Free up disk space
   docker volume prune -f
   docker image prune -a -f
   ```

3. **Environment variable issues**
   ```bash
   # Check environment file
   cat .env.production
   
   # Verify variables in container
   docker-compose exec app env | grep DATABASE_URL
   ```

### Container Keeps Restarting

#### Symptom
Container starts but crashes repeatedly

#### Diagnosis
```bash
# Check restart policy
docker inspect container-name | grep -A 5 RestartPolicy

# Monitor restart events
docker events --filter container=container-name

# Check exit codes
docker ps -a
```

#### Solutions

1. **Application crashes**
   ```bash
   # Check application logs
   docker-compose logs -f --tail=100 app
   
   # Check for Python errors
   docker-compose logs app | grep -i traceback
   
   # Run container in debug mode
   docker-compose run --rm app python -c "import backend.main"
   ```

2. **Health check failures**
   ```bash
   # Disable health check temporarily
   docker-compose -f docker-compose.production.yml up -d --no-healthcheck
   
   # Test health check manually
   docker exec app curl -f http://localhost:8000/health
   ```

3. **Database connection issues**
   ```bash
   # Check database is ready
   docker-compose exec db pg_isready -U fintradeagent
   
   # Test connection from app container
   docker-compose exec app python -c "
   import os
   from sqlalchemy import create_engine
   engine = create_engine(os.getenv('DATABASE_URL'))
   with engine.connect():
       print('Connection successful')
   "
   ```

### Container Performance Issues

#### Symptom
Slow response times or high resource usage

#### Diagnosis
```bash
# Check container resource usage
docker stats container-name

# Check container processes
docker exec container-name top

# Check memory usage inside container
docker exec container-name cat /proc/meminfo

# Check disk I/O
iostat -x 1
```

#### Solutions

1. **Memory issues**
   ```bash
   # Increase memory limit
   # In docker-compose.yml:
   services:
     app:
       deploy:
         resources:
           limits:
             memory: 2G
   ```

2. **CPU bottlenecks**
   ```bash
   # Check CPU usage
   docker exec app htop
   
   # Scale horizontally
   docker-compose up -d --scale app=3
   ```

## Database Problems

### Database Won't Start

#### Symptom
PostgreSQL container fails to start

#### Diagnosis
```bash
# Check PostgreSQL logs
docker-compose logs db

# Check data directory permissions
docker exec db ls -la /var/lib/postgresql/data

# Check disk space
df -h
```

#### Solutions

1. **Permission issues**
   ```bash
   # Fix data directory permissions
   docker-compose down
   sudo chown -R 999:999 postgres_data/
   docker-compose up -d db
   ```

2. **Corrupted data**
   ```bash
   # Backup and recreate volume
   docker-compose down
   docker volume ls | grep postgres
   docker volume rm fintradeagent_postgres_data
   docker-compose up -d db
   ```

3. **Port conflicts**
   ```bash
   # Check if PostgreSQL is running locally
   sudo lsof -i :5432
   sudo systemctl stop postgresql
   ```

### Database Connection Issues

#### Symptom
Application can't connect to database

#### Diagnosis
```bash
# Test connection from app container
docker-compose exec app python -c "
import psycopg2
conn = psycopg2.connect(
    host='db',
    database='fintradeagent_prod',
    user='fintradeagent',
    password='$DATABASE_PASSWORD'
)
print('Connection successful')
conn.close()
"

# Check network connectivity
docker-compose exec app ping db

# Check database is accepting connections
docker-compose exec db pg_isready -U fintradeagent
```

#### Solutions

1. **Network issues**
   ```bash
   # Recreate network
   docker-compose down
   docker network prune
   docker-compose up -d
   ```

2. **Authentication problems**
   ```bash
   # Check database user
   docker-compose exec db psql -U fintradeagent -c "\\du"
   
   # Reset password
   docker-compose exec db psql -U postgres -c "
   ALTER USER fintradeagent WITH PASSWORD 'new_password';
   "
   ```

### Database Performance Issues

#### Symptom
Slow database queries

#### Diagnosis
```sql
-- Check slow queries
SELECT query, calls, mean_time, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC LIMIT 10;

-- Check active connections
SELECT count(*) FROM pg_stat_activity;

-- Check table sizes
SELECT schemaname,tablename,pg_size_pretty(pg_total_relation_size(tablename::text)) AS size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(tablename::text) DESC;
```

#### Solutions

1. **Connection pooling**
   ```python
   # In backend configuration
   SQLALCHEMY_ENGINE_OPTIONS = {
       "pool_size": 10,
       "max_overflow": 20,
       "pool_pre_ping": True,
       "pool_recycle": 300,
   }
   ```

2. **Query optimization**
   ```sql
   -- Add missing indexes
   CREATE INDEX CONCURRENTLY idx_portfolio_name ON portfolios(name);
   
   -- Analyze tables
   ANALYZE;
   ```

## Network Connectivity

### Service Discovery Issues

#### Symptom
Services can't communicate with each other

#### Diagnosis
```bash
# Check network configuration
docker network ls
docker network inspect fintradeagent-network

# Test connectivity between containers
docker-compose exec app ping db
docker-compose exec app nslookup db

# Check port binding
docker-compose port app 8000
```

#### Solutions

1. **Network recreation**
   ```bash
   docker-compose down
   docker network prune
   docker-compose up -d
   ```

2. **DNS resolution**
   ```bash
   # Check /etc/hosts in container
   docker-compose exec app cat /etc/hosts
   
   # Check Docker daemon DNS
   docker exec app nslookup db
   ```

### External Connectivity Issues

#### Symptom
Can't access services from outside containers

#### Diagnosis
```bash
# Check port mappings
docker-compose ps

# Test from host
curl -f http://localhost:8000/health

# Check firewall
sudo ufw status
sudo iptables -L -n
```

#### Solutions

1. **Port mapping issues**
   ```yaml
   # In docker-compose.yml
   services:
     app:
       ports:
         - "8000:8000"  # host:container
   ```

2. **Firewall blocking**
   ```bash
   # Allow port through firewall
   sudo ufw allow 8000/tcp
   
   # Or disable firewall temporarily
   sudo ufw disable
   ```

## Performance Issues

### High Memory Usage

#### Symptom
System runs out of memory

#### Diagnosis
```bash
# Check memory usage by container
docker stats --no-stream

# Check host memory
free -h

# Check for memory leaks
docker exec app ps aux --sort=-%mem | head
```

#### Solutions

1. **Set memory limits**
   ```yaml
   services:
     app:
       deploy:
         resources:
           limits:
             memory: 1G
   ```

2. **Optimize application**
   ```python
   # Add to FastAPI app
   import gc
   gc.collect()  # Force garbage collection
   
   # Use connection pooling
   # Implement caching
   ```

### High CPU Usage

#### Symptom
CPU usage consistently high

#### Diagnosis
```bash
# Check CPU usage
docker stats --no-stream

# Check processes inside container
docker exec app top

# Profile Python application
docker exec app python -m cProfile -s cumtime your_script.py
```

#### Solutions

1. **Scale horizontally**
   ```bash
   docker-compose up -d --scale app=3
   ```

2. **Optimize code**
   ```python
   # Use async/await
   # Implement caching
   # Optimize database queries
   ```

### Disk I/O Issues

#### Symptom
Slow disk operations

#### Diagnosis
```bash
# Check disk usage
df -h

# Check I/O statistics
iostat -x 1

# Check container disk usage
docker system df
```

#### Solutions

1. **Clean up disk space**
   ```bash
   # Clean Docker resources
   docker system prune -a -f
   
   # Clean volumes
   docker volume prune -f
   ```

2. **Optimize logging**
   ```yaml
   services:
     app:
       logging:
         driver: "json-file"
         options:
           max-size: "10m"
           max-file: "3"
   ```

## Storage and Volumes

### Volume Mount Issues

#### Symptom
Data not persisting or files not accessible

#### Diagnosis
```bash
# Check volume mounts
docker inspect container-name | grep -A 10 Mounts

# Check volume content
docker volume ls
docker volume inspect volume-name

# Check permissions
docker exec container-name ls -la /mounted/path
```

#### Solutions

1. **Permission issues**
   ```bash
   # Fix ownership
   sudo chown -R $USER:$USER ./data/
   
   # Or change in Dockerfile
   RUN chown -R appuser:appgroup /data
   ```

2. **Volume recreation**
   ```bash
   # Backup data first
   docker run --rm -v volume-name:/data -v $(pwd):/backup alpine tar czf /backup/backup.tar.gz /data
   
   # Recreate volume
   docker volume rm volume-name
   docker-compose up -d
   ```

### Database Volume Issues

#### Symptom
Database data lost or corrupted

#### Diagnosis
```bash
# Check PostgreSQL data directory
docker exec db ls -la /var/lib/postgresql/data

# Check volume integrity
docker exec db pg_controldata /var/lib/postgresql/data
```

#### Solutions

1. **Restore from backup**
   ```bash
   ./scripts/backup.sh --environment production
   # Follow recovery procedures in DOCKER_DEPLOYMENT.md
   ```

2. **Reinitialize database**
   ```bash
   docker-compose down
   docker volume rm postgres_data
   docker-compose up -d db
   # Restore from backup or run migrations
   ```

## Security and Permissions

### Permission Denied Errors

#### Symptom
Cannot access files or execute commands

#### Diagnosis
```bash
# Check file permissions
docker exec container-name ls -la /path/to/file

# Check user context
docker exec container-name id

# Check SELinux context (if applicable)
ls -Z /host/path/
```

#### Solutions

1. **Fix file permissions**
   ```bash
   sudo chown -R 999:999 ./data/
   sudo chmod -R 755 ./data/
   ```

2. **Update Dockerfile**
   ```dockerfile
   # Create user with specific UID/GID
   RUN groupadd -r -g 1000 appgroup && \
       useradd -r -u 1000 -g appgroup appuser
   ```

### Container Security Issues

#### Symptom
Security warnings or vulnerabilities

#### Diagnosis
```bash
# Scan image for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image fintradeagent:latest

# Check container privileges
docker inspect container-name | grep -i privilege
```

#### Solutions

1. **Update base images**
   ```bash
   docker pull python:3.11-slim
   docker-compose build --no-cache
   ```

2. **Apply security hardening**
   ```yaml
   services:
     app:
       security_opt:
         - no-new-privileges:true
       user: "1000:1000"
       read_only: true
   ```

## Monitoring and Logging

### Log Collection Issues

#### Symptom
Logs not appearing or being truncated

#### Diagnosis
```bash
# Check log driver
docker inspect container-name | grep LogConfig

# Check log files
docker-compose logs --no-color service-name > logs.txt

# Check disk space for logs
du -sh /var/lib/docker/containers/*
```

#### Solutions

1. **Configure log rotation**
   ```yaml
   services:
     app:
       logging:
         driver: "json-file"
         options:
           max-size: "10m"
           max-file: "3"
   ```

2. **External log collection**
   ```yaml
   services:
     app:
       logging:
         driver: "syslog"
         options:
           syslog-address: "tcp://logstash:5000"
   ```

### Monitoring Stack Issues

#### Symptom
Prometheus or Grafana not collecting metrics

#### Diagnosis
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check Grafana data source
curl -u admin:password http://localhost:3001/api/datasources

# Check exporter endpoints
curl http://localhost:9187/metrics  # PostgreSQL
curl http://localhost:9121/metrics  # Redis
```

#### Solutions

1. **Restart monitoring services**
   ```bash
   docker-compose -f docker-compose.production.yml -f docker-compose.monitoring.yml restart prometheus grafana
   ```

2. **Check configuration files**
   ```bash
   # Validate Prometheus config
   docker exec prometheus promtool check config /etc/prometheus/prometheus.yml
   
   # Check Grafana logs
   docker-compose logs grafana
   ```

## Development Environment

### Hot Reload Not Working

#### Symptom
Changes not reflected automatically

#### Diagnosis
```bash
# Check volume mounts
docker-compose -f docker-compose.dev.yml config | grep -A 5 volumes

# Check if files are being watched
docker-compose -f docker-compose.dev.yml exec backend-dev ls -la /app
```

#### Solutions

1. **Fix volume mounts**
   ```yaml
   services:
     backend-dev:
       volumes:
         - .:/app
         - /app/node_modules  # Exclude node_modules
   ```

2. **Check file permissions**
   ```bash
   # Ensure files are writable
   chmod -R 755 ./backend/
   ```

### Development Dependencies Issues

#### Symptom
Missing development tools or packages

#### Diagnosis
```bash
# Check installed packages
docker-compose -f docker-compose.dev.yml exec backend-dev pip list

# Check Node.js packages
docker-compose -f docker-compose.dev.yml exec frontend-dev npm list
```

#### Solutions

1. **Rebuild development images**
   ```bash
   docker-compose -f docker-compose.dev.yml build --no-cache
   ```

2. **Install missing packages**
   ```bash
   docker-compose -f docker-compose.dev.yml exec backend-dev pip install package-name
   docker-compose -f docker-compose.dev.yml exec frontend-dev npm install package-name
   ```

## Production Issues

### SSL Certificate Problems

#### Symptom
HTTPS not working or certificate errors

#### Diagnosis
```bash
# Check certificate files
ls -la ssl/

# Test certificate
openssl x509 -in ssl/cert.pem -text -noout

# Check Nginx configuration
docker exec nginx nginx -t
```

#### Solutions

1. **Renew certificates**
   ```bash
   # Let's Encrypt renewal
   sudo certbot renew
   cp /etc/letsencrypt/live/domain/fullchain.pem ssl/cert.pem
   cp /etc/letsencrypt/live/domain/privkey.pem ssl/key.pem
   docker-compose restart nginx
   ```

2. **Fix certificate permissions**
   ```bash
   sudo chown root:docker ssl/*.pem
   sudo chmod 640 ssl/*.pem
   ```

### Load Balancer Issues

#### Symptom
Uneven load distribution or connection failures

#### Diagnosis
```bash
# Check Nginx upstream status
docker exec nginx curl http://localhost/nginx_status

# Check backend health
for i in {1..3}; do
  curl -I http://localhost:800$i/health
done
```

#### Solutions

1. **Restart unhealthy backends**
   ```bash
   docker-compose restart app
   ```

2. **Update load balancer configuration**
   ```nginx
   upstream backend {
       least_conn;
       server app1:8000 max_fails=3 fail_timeout=30s;
       server app2:8000 max_fails=3 fail_timeout=30s;
       server app3:8000 max_fails=3 fail_timeout=30s;
   }
   ```

### Backup and Recovery Issues

#### Symptom
Backups failing or restoration problems

#### Diagnosis
```bash
# Check backup script logs
./scripts/backup.sh --environment production --verbose

# Verify backup files
ls -la backups/production/latest/
gunzip -t backups/production/latest/database.sql.gz
```

#### Solutions

1. **Fix backup permissions**
   ```bash
   mkdir -p backups/production
   chmod 755 backups/
   chown -R $USER:$USER backups/
   ```

2. **Test restoration process**
   ```bash
   # Test in development environment
   docker-compose -f docker-compose.dev.yml exec db-dev psql -U postgres -c "CREATE DATABASE test_restore;"
   gunzip -c backup.sql.gz | docker-compose -f docker-compose.dev.yml exec -T db-dev psql -U postgres -d test_restore
   ```

## Emergency Procedures

### Complete System Recovery

```bash
# 1. Stop all services
docker-compose -f docker-compose.production.yml down

# 2. Backup current state (if possible)
docker system df
./scripts/backup.sh --environment production

# 3. Clean up system
docker system prune -a -f
docker volume prune -f

# 4. Rebuild from scratch
git pull
docker-compose -f docker-compose.production.yml build --no-cache
docker-compose -f docker-compose.production.yml up -d

# 5. Restore data if needed
# Follow restoration procedures
```

### Data Recovery

```bash
# If volumes are corrupted but backups exist
docker-compose down
docker volume rm postgres_data app_data
docker-compose up -d db
# Wait for database to initialize
docker exec -i fintradeagent-db psql -U fintradeagent -d fintradeagent_prod < backup.sql
```

This troubleshooting guide covers the most common Docker-related issues you might encounter with FinTradeAgent. Always start with basic diagnostics and work your way through the solutions systematically.