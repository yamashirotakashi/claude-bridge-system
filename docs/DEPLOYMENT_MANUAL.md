# Claude Bridge System - Production Deployment Manual
Ultimate guide for deploying and operating the Claude Bridge System in production

## 📚 Table of Contents
1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Environment Setup](#environment-setup)
3. [Security Configuration](#security-configuration)
4. [Database Setup](#database-setup)
5. [Container Deployment](#container-deployment)
6. [Monitoring Setup](#monitoring-setup)
7. [SSL Certificate Management](#ssl-certificate-management)
8. [Backup and Recovery](#backup-and-recovery)
9. [Performance Tuning](#performance-tuning)
10. [Troubleshooting Guide](#troubleshooting-guide)
11. [Maintenance Procedures](#maintenance-procedures)
12. [Emergency Procedures](#emergency-procedures)

## 🏗️ Pre-Deployment Checklist

### Infrastructure Requirements
- [ ] **Server Specifications**
  - Minimum: 4 CPU cores, 8GB RAM, 50GB SSD
  - Recommended: 8 CPU cores, 16GB RAM, 100GB SSD
  - Network: 1Gbps connection with static IP

- [ ] **Operating System**
  - Ubuntu 20.04+ LTS or CentOS 8+
  - Docker Engine 20.10+
  - Docker Compose 2.0+
  - Python 3.11+

- [ ] **Network Configuration**
  - Ports 80, 443 open for HTTP/HTTPS
  - Firewall configured for Docker network
  - DNS records configured for domain

- [ ] **Security Prerequisites**
  - SSL/TLS certificates obtained
  - Strong passwords generated for all services
  - Security scanning completed
  - Backup storage configured

### Dependencies Check
```bash
# Verify Docker installation
docker --version
docker-compose --version

# Check system resources
free -h
df -h
nproc

# Verify network connectivity
curl -I https://github.com
```

## 🔧 Environment Setup

### 1. Clone Repository
```bash
git clone https://github.com/your-org/claude-bridge-system.git
cd claude-bridge-system
```

### 2. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Generate secure passwords
openssl rand -base64 32  # For JWT_SECRET
openssl rand -base64 16  # For database passwords
```

### 3. Environment Variables
Edit `.env` with your specific configuration:

```bash
# Security (CRITICAL - Change all defaults)
POSTGRES_PASSWORD=your_secure_postgres_password_here
REDIS_PASSWORD=your_secure_redis_password_here
JWT_SECRET=your_jwt_secret_minimum_32_characters_here
GRAFANA_PASSWORD=your_secure_grafana_password_here

# Application Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=false

# Network Configuration
HTTP_PORT=80
HTTPS_PORT=443
BRIDGE_PORT=8080
BRIDGE_SECURE_PORT=8443
METRICS_PORT=9090

# Database Configuration
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=claude_bridge
POSTGRES_USER=claude

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Monitoring Configuration
PROMETHEUS_RETENTION=365d
GRAFANA_SECURITY_ADMIN_USER=admin

# Backup Configuration
BACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=365
BACKUP_SCHEDULE="0 2 * * *"  # Daily at 2 AM

# SSL Configuration
SSL_CERT_PATH=/etc/nginx/ssl/server.crt
SSL_KEY_PATH=/etc/nginx/ssl/server.key

# External Services (Optional)
SLACK_WEBHOOK_URL=your_slack_webhook_for_alerts
EMAIL_SMTP_HOST=your_smtp_server
EMAIL_SMTP_PORT=587
EMAIL_FROM=alerts@yourdomain.com
```

## 🔒 Security Configuration

### 1. SSL Certificate Setup
Choose one of the following options:

#### Option A: Self-Signed Certificate (Development/Testing)
```bash
mkdir -p docker/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout docker/ssl/server.key \
  -out docker/ssl/server.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

#### Option B: Let's Encrypt Certificate (Production)
```bash
# Install certbot
sudo apt-get update
sudo apt-get install certbot

# Obtain certificate (ensure domain points to your server)
sudo certbot certonly --standalone -d yourdomain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem docker/ssl/server.crt
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem docker/ssl/server.key
sudo chown $USER:$USER docker/ssl/*

# Set up auto-renewal
echo "0 12 * * * /usr/bin/certbot renew --quiet && docker-compose restart nginx" | crontab -
```

#### Option C: Commercial Certificate
```bash
# Copy your commercial certificates
cp your-certificate.crt docker/ssl/server.crt
cp your-private-key.key docker/ssl/server.key
chmod 600 docker/ssl/server.key
```

### 2. Security Hardening
```bash
# Set proper file permissions
chmod 600 .env
chmod 600 docker/ssl/server.key
chmod 644 docker/ssl/server.crt

# Secure docker socket (if applicable)
sudo usermod -aG docker $USER
newgrp docker

# Configure firewall
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 5432/tcp   # PostgreSQL (block external access)
sudo ufw deny 6379/tcp   # Redis (block external access)
sudo ufw --force enable
```

## 🗄️ Database Setup

### 1. Initialize Database Schema
```bash
# Create initialization script
cat > docker/init-db.sql << 'EOF'
-- Create required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create application user with limited privileges
CREATE USER claude_app WITH PASSWORD 'your_app_password';

-- Create database with proper collation
CREATE DATABASE claude_bridge 
  WITH OWNER = claude 
  ENCODING = 'UTF8' 
  LC_COLLATE = 'en_US.UTF-8' 
  LC_CTYPE = 'en_US.UTF-8'
  TEMPLATE = template0;

-- Grant necessary permissions
GRANT CONNECT ON DATABASE claude_bridge TO claude_app;
GRANT USAGE ON SCHEMA public TO claude_app;
GRANT CREATE ON SCHEMA public TO claude_app;

-- Performance tuning settings
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET max_connections = 100;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
EOF
```

### 2. Database Backup Configuration
```bash
# Create backup script
cat > scripts/backup_database.sh << 'EOF'
#!/bin/bash
set -e

BACKUP_DIR="/app/backups/database"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="claude_bridge_${TIMESTAMP}.sql"

mkdir -p "$BACKUP_DIR"

# Create database backup
docker-compose exec -T postgres pg_dump \
  -U claude \
  -h postgres \
  -d claude_bridge \
  --no-password \
  --verbose \
  --clean \
  --create > "$BACKUP_DIR/$BACKUP_FILE"

# Compress backup
gzip "$BACKUP_DIR/$BACKUP_FILE"

# Remove backups older than retention period
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +${BACKUP_RETENTION_DAYS:-30} -delete

echo "Database backup completed: $BACKUP_FILE.gz"
EOF

chmod +x scripts/backup_database.sh
```

## 🐳 Container Deployment

### 1. Pre-deployment Validation
```bash
# Validate Docker Compose configuration
docker-compose config

# Test environment variables
docker-compose run --rm claude-bridge python -c "
import os, sys
required_vars = ['POSTGRES_PASSWORD', 'JWT_SECRET', 'REDIS_PASSWORD']
missing = [v for v in required_vars if not os.getenv(v)]
if missing:
    print(f'Missing required environment variables: {missing}')
    sys.exit(1)
print('Environment validation passed')
"
```

### 2. Initial Deployment
```bash
# Pull latest images
docker-compose pull

# Build application image
docker-compose build --no-cache

# Start services
docker-compose up -d

# Wait for services to be ready
sleep 30

# Verify deployment
docker-compose ps
docker-compose logs --tail=50
```

### 3. Service Health Verification
```bash
# Check service health
curl -f http://localhost/health || echo "Health check failed"

# Verify SSL
curl -k https://localhost/health || echo "SSL health check failed"

# Test API endpoints
curl -f http://localhost/api/status || echo "API status check failed"

# Check database connectivity
docker-compose exec claude-bridge python -c "
import psycopg2
conn = psycopg2.connect(
    host='postgres',
    database='claude_bridge',
    user='claude',
    password='$POSTGRES_PASSWORD'
)
print('Database connection successful')
conn.close()
"
```

## 📊 Monitoring Setup

### 1. Prometheus Configuration
The system includes pre-configured Prometheus monitoring:
```bash
# Verify Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check metrics endpoints
curl http://localhost:9090/metrics
curl http://localhost:9091/metrics  # Application metrics
```

### 2. Grafana Dashboard Setup
```bash
# Access Grafana dashboard
echo "Grafana URL: http://localhost:3000"
echo "Username: admin"
echo "Password: $GRAFANA_PASSWORD"

# Import pre-configured dashboards
# Dashboards are automatically loaded from docker/grafana/dashboards/
```

### 3. Alerting Configuration
```bash
# Verify Alertmanager
curl http://localhost:9093/api/v1/status

# Test alert rules
docker-compose exec prometheus promtool check rules /etc/prometheus/alert_rules.yml
```

## 🔐 SSL Certificate Management

### 1. Certificate Monitoring
```bash
# Check certificate expiration
openssl x509 -in docker/ssl/server.crt -noout -dates

# Set up certificate expiration monitoring
cat > scripts/check_ssl_expiry.sh << 'EOF'
#!/bin/bash
CERT_FILE="docker/ssl/server.crt"
DAYS_WARN=30

if [ -f "$CERT_FILE" ]; then
    EXPIRY=$(openssl x509 -in "$CERT_FILE" -noout -enddate | cut -d= -f2)
    EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s)
    CURRENT_EPOCH=$(date +%s)
    DAYS_LEFT=$(( (EXPIRY_EPOCH - CURRENT_EPOCH) / 86400 ))
    
    if [ $DAYS_LEFT -lt $DAYS_WARN ]; then
        echo "WARNING: SSL certificate expires in $DAYS_LEFT days"
        # Send alert (configure your notification method)
    else
        echo "SSL certificate valid for $DAYS_LEFT days"
    fi
fi
EOF

chmod +x scripts/check_ssl_expiry.sh

# Add to crontab for daily checks
echo "0 9 * * * /path/to/claude-bridge-system/scripts/check_ssl_expiry.sh" | crontab -
```

### 2. Certificate Renewal
```bash
# For Let's Encrypt certificates
sudo certbot renew --dry-run

# For commercial certificates, update manually and restart
cp new-certificate.crt docker/ssl/server.crt
cp new-private-key.key docker/ssl/server.key
docker-compose restart nginx
```

## 💾 Backup and Recovery

### 1. Automated Backup Setup
```bash
# Create comprehensive backup script
cat > scripts/full_backup.sh << 'EOF'
#!/bin/bash
set -e

BACKUP_DIR="/app/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="claude_bridge_full_${TIMESTAMP}"

mkdir -p "$BACKUP_DIR"

echo "Starting full system backup..."

# Database backup
echo "Backing up database..."
docker-compose exec -T postgres pg_dump \
  -U claude -d claude_bridge \
  --clean --create > "$BACKUP_DIR/${BACKUP_NAME}_database.sql"

# Application data backup
echo "Backing up application data..."
docker-compose exec -T claude-bridge tar czf - /app/data > "$BACKUP_DIR/${BACKUP_NAME}_appdata.tar.gz"

# Configuration backup
echo "Backing up configuration..."
tar czf "$BACKUP_DIR/${BACKUP_NAME}_config.tar.gz" \
  .env docker-compose.yml docker/ config/

# Redis backup (if persistent)
echo "Backing up Redis data..."
docker-compose exec -T redis redis-cli BGSAVE
sleep 5
docker cp $(docker-compose ps -q redis):/data/dump.rdb "$BACKUP_DIR/${BACKUP_NAME}_redis.rdb"

# Create backup manifest
cat > "$BACKUP_DIR/${BACKUP_NAME}_manifest.txt" << MANIFEST
Backup Name: $BACKUP_NAME
Timestamp: $(date)
Components:
- Database: ${BACKUP_NAME}_database.sql
- Application Data: ${BACKUP_NAME}_appdata.tar.gz
- Configuration: ${BACKUP_NAME}_config.tar.gz
- Redis Data: ${BACKUP_NAME}_redis.rdb
MANIFEST

echo "Full backup completed: $BACKUP_NAME"

# Clean up old backups
find "$BACKUP_DIR" -name "claude_bridge_full_*" -mtime +${BACKUP_RETENTION_DAYS:-30} -delete
EOF

chmod +x scripts/full_backup.sh

# Set up automated backups
echo "0 2 * * * /path/to/claude-bridge-system/scripts/full_backup.sh" | crontab -
```

### 2. Recovery Procedures
```bash
# Create recovery script
cat > scripts/restore_backup.sh << 'EOF'
#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "Usage: $0 BACKUP_TIMESTAMP"
    echo "Available backups:"
    ls -1 /app/backups/claude_bridge_full_*_manifest.txt | sed 's/.*full_\(.*\)_manifest.txt/\1/'
    exit 1
fi

BACKUP_NAME="claude_bridge_full_$1"
BACKUP_DIR="/app/backups"

echo "Restoring from backup: $BACKUP_NAME"

# Stop services
docker-compose down

# Restore database
echo "Restoring database..."
docker-compose up -d postgres
sleep 10
cat "$BACKUP_DIR/${BACKUP_NAME}_database.sql" | \
  docker-compose exec -T postgres psql -U claude

# Restore application data
echo "Restoring application data..."
docker-compose up -d claude-bridge
sleep 10
docker-compose exec -T claude-bridge tar xzf - -C / < "$BACKUP_DIR/${BACKUP_NAME}_appdata.tar.gz"

# Restore Redis data
echo "Restoring Redis data..."
docker-compose up -d redis
sleep 5
docker cp "$BACKUP_DIR/${BACKUP_NAME}_redis.rdb" $(docker-compose ps -q redis):/data/dump.rdb
docker-compose restart redis

# Restore configuration (manual verification recommended)
echo "Configuration backup available at: $BACKUP_DIR/${BACKUP_NAME}_config.tar.gz"
echo "Please verify and manually restore configuration files if needed"

# Start all services
docker-compose up -d

echo "Restore completed. Please verify system functionality."
EOF

chmod +x scripts/restore_backup.sh
```

## ⚡ Performance Tuning

### 1. System-Level Optimization
```bash
# Optimize system parameters
cat > /etc/sysctl.d/99-claude-bridge.conf << 'EOF'
# Network optimization
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout = 10

# Memory optimization
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5

# File system optimization
fs.file-max = 65535
EOF

sysctl -p /etc/sysctl.d/99-claude-bridge.conf
```

### 2. Docker Optimization
```bash
# Optimize Docker daemon
cat > /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "live-restore": true,
  "userland-proxy": false,
  "experimental": false
}
EOF

systemctl restart docker
```

### 3. Application Tuning
Edit `config/production.yaml`:
```yaml
server:
  workers: 8  # Number of CPU cores
  max_connections: 1000
  keepalive_timeout: 65
  
database:
  pool_size: 20
  max_overflow: 30
  pool_timeout: 30
  pool_recycle: 3600

cache:
  redis_max_connections: 50
  default_timeout: 300

security:
  rate_limiting:
    enabled: true
    requests_per_minute: 1000
    burst_size: 100
```

## 🔧 Troubleshooting Guide

### Common Issues and Solutions

#### 1. Service Won't Start
```bash
# Check logs
docker-compose logs claude-bridge --tail=100

# Common causes and fixes:
# - Port already in use
sudo netstat -tulpn | grep :8080
sudo kill -9 $(sudo lsof -t -i:8080)

# - Permission issues
sudo chown -R $USER:$USER .
chmod 600 .env

# - Memory issues
free -h
docker system prune -a
```

#### 2. Database Connection Issues
```bash
# Check PostgreSQL status
docker-compose exec postgres pg_isready -U claude

# Test connection from application
docker-compose exec claude-bridge python -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='postgres',
        database='claude_bridge',
        user='claude',
        password='$POSTGRES_PASSWORD'
    )
    print('Connection successful')
    conn.close()
except Exception as e:
    print(f'Connection failed: {e}')
"

# Check PostgreSQL logs
docker-compose logs postgres --tail=50
```

#### 3. SSL/HTTPS Issues
```bash
# Verify certificate
openssl x509 -in docker/ssl/server.crt -text -noout

# Check certificate chain
openssl verify -CAfile docker/ssl/ca-bundle.crt docker/ssl/server.crt

# Test SSL connection
openssl s_client -connect localhost:443 -verify_return_error
```

#### 4. Performance Issues
```bash
# Check system resources
docker stats

# Analyze application performance
docker-compose exec claude-bridge python -m claude_bridge.performance.profiler --analyze

# Database performance analysis
docker-compose exec postgres psql -U claude -d claude_bridge -c "
SELECT query, calls, total_time, mean_time, rows
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;
"
```

#### 5. Monitoring Issues
```bash
# Check Prometheus targets
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'

# Verify metrics collection
curl -s http://localhost:9091/metrics | grep -E "^claude_bridge_"

# Check Grafana datasource
curl -u admin:$GRAFANA_PASSWORD http://localhost:3000/api/datasources
```

## 🔄 Maintenance Procedures

### Daily Maintenance
```bash
#!/bin/bash
# Daily maintenance script

echo "=== Daily Maintenance - $(date) ==="

# Check service status
echo "Checking service status..."
docker-compose ps

# Check disk space
echo "Checking disk space..."
df -h

# Check logs for errors
echo "Checking for errors in logs..."
docker-compose logs --since=24h | grep -i error | tail -20

# Check SSL certificate expiry
scripts/check_ssl_expiry.sh

# Basic health check
curl -f http://localhost/health || echo "Health check failed"

echo "Daily maintenance completed"
```

### Weekly Maintenance
```bash
#!/bin/bash
# Weekly maintenance script

echo "=== Weekly Maintenance - $(date) ==="

# Update system packages (if applicable)
echo "Pulling latest images..."
docker-compose pull

# Clean up Docker system
echo "Cleaning up Docker system..."
docker system prune -f

# Analyze database performance
echo "Database maintenance..."
docker-compose exec postgres psql -U claude -d claude_bridge -c "VACUUM ANALYZE;"

# Check backup integrity
echo "Verifying latest backup..."
LATEST_BACKUP=$(ls -1t /app/backups/claude_bridge_full_*_manifest.txt | head -1)
if [ -f "$LATEST_BACKUP" ]; then
    echo "Latest backup: $(basename $LATEST_BACKUP)"
else
    echo "WARNING: No recent backups found"
fi

# Review monitoring alerts
echo "Checking for active alerts..."
curl -s http://localhost:9093/api/v1/alerts | jq '.data[] | select(.state == "firing")'

echo "Weekly maintenance completed"
```

### Monthly Maintenance
```bash
#!/bin/bash
# Monthly maintenance script

echo "=== Monthly Maintenance - $(date) ==="

# Security scan
echo "Running security scan..."
docker-compose exec claude-bridge python -m claude_bridge.security.scanner

# Performance analysis
echo "Running performance analysis..."
docker-compose exec claude-bridge python -m claude_bridge.performance.profiler --full-report

# Update SSL certificates (if needed)
scripts/check_ssl_expiry.sh

# Database optimization
echo "Database optimization..."
docker-compose exec postgres psql -U claude -d claude_bridge -c "
REINDEX DATABASE claude_bridge;
VACUUM FULL;
"

# Backup verification and cleanup
echo "Backup maintenance..."
scripts/full_backup.sh
find /app/backups -name "claude_bridge_full_*" -mtime +90 -delete

# Review and rotate logs
echo "Log rotation..."
docker-compose exec claude-bridge find /app/logs -name "*.log" -size +100M -delete

echo "Monthly maintenance completed"
```

## 🚨 Emergency Procedures

### System Recovery
```bash
#!/bin/bash
# Emergency recovery script

echo "=== EMERGENCY RECOVERY INITIATED ==="

# Stop all services
echo "Stopping all services..."
docker-compose down

# Check system resources
echo "Checking system resources..."
df -h
free -h

# Restore from latest backup
echo "Available backups:"
ls -1t /app/backups/claude_bridge_full_*_manifest.txt | head -5

read -p "Enter backup timestamp to restore from (or 'skip'): " BACKUP_TS
if [ "$BACKUP_TS" != "skip" ]; then
    scripts/restore_backup.sh "$BACKUP_TS"
fi

# Start services with health checks
echo "Starting services..."
docker-compose up -d

# Wait and verify
sleep 30
for service in postgres redis claude-bridge nginx; do
    if docker-compose ps $service | grep -q "Up"; then
        echo "✓ $service is running"
    else
        echo "✗ $service failed to start"
    fi
done

# Verify application health
if curl -f http://localhost/health > /dev/null 2>&1; then
    echo "✓ Application health check passed"
else
    echo "✗ Application health check failed"
fi

echo "Emergency recovery completed. Review logs and system status."
```

### Rollback Deployment
```bash
#!/bin/bash
# Rollback to previous version

echo "=== DEPLOYMENT ROLLBACK ==="

# Stop current deployment
docker-compose down

# Pull previous image version
read -p "Enter previous image tag to rollback to: " PREV_TAG
docker pull your-registry/claude-bridge:$PREV_TAG

# Update docker-compose to use previous version
sed -i "s|image: your-registry/claude-bridge:.*|image: your-registry/claude-bridge:$PREV_TAG|" docker-compose.yml

# Start with previous version
docker-compose up -d

# Verify rollback
sleep 30
curl -f http://localhost/health && echo "Rollback successful" || echo "Rollback failed"
```

## 📞 Support and Escalation

### Log Collection for Support
```bash
#!/bin/bash
# Collect comprehensive logs for support

SUPPORT_DIR="support_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$SUPPORT_DIR"

# System information
uname -a > "$SUPPORT_DIR/system_info.txt"
docker --version >> "$SUPPORT_DIR/system_info.txt"
docker-compose --version >> "$SUPPORT_DIR/system_info.txt"

# Service status
docker-compose ps > "$SUPPORT_DIR/service_status.txt"

# Logs
docker-compose logs > "$SUPPORT_DIR/application_logs.txt"
journalctl -u docker > "$SUPPORT_DIR/docker_logs.txt"

# Configuration (sanitized)
cp docker-compose.yml "$SUPPORT_DIR/"
sed 's/password=.*/password=***REDACTED***/g' .env > "$SUPPORT_DIR/env_sanitized.txt"

# System resources
df -h > "$SUPPORT_DIR/disk_usage.txt"
free -h > "$SUPPORT_DIR/memory_usage.txt"
ps aux > "$SUPPORT_DIR/processes.txt"

# Network information
netstat -tulpn > "$SUPPORT_DIR/network_ports.txt"

# Create archive
tar czf "${SUPPORT_DIR}.tar.gz" "$SUPPORT_DIR"
rm -rf "$SUPPORT_DIR"

echo "Support package created: ${SUPPORT_DIR}.tar.gz"
echo "Please send this file to the support team"
```

### Contact Information
- **System Administrator**: admin@yourdomain.com
- **DevOps Team**: devops@yourdomain.com  
- **Emergency Contact**: +1-XXX-XXX-XXXX
- **Support Portal**: https://support.yourdomain.com

---

## 📋 Deployment Checklist

### Pre-Production Checklist
- [ ] Environment variables configured
- [ ] SSL certificates installed and verified  
- [ ] Database initialized and accessible
- [ ] Security hardening completed
- [ ] Backup system configured and tested
- [ ] Monitoring dashboard accessible
- [ ] Performance tuning applied
- [ ] Firewall rules configured
- [ ] DNS records configured
- [ ] Load balancer configured (if applicable)

### Post-Deployment Checklist
- [ ] All services running and healthy
- [ ] Application responding to requests
- [ ] HTTPS working correctly
- [ ] Database connections working
- [ ] Monitoring collecting metrics
- [ ] Alerts configured and tested
- [ ] Backup job scheduled and working
- [ ] Log rotation configured
- [ ] Performance baseline established
- [ ] Documentation updated

### Go-Live Checklist
- [ ] Smoke tests passed
- [ ] Performance tests passed
- [ ] Security scan completed
- [ ] Team trained on operations procedures
- [ ] Runbooks updated
- [ ] Emergency contacts notified
- [ ] Change management approval
- [ ] Rollback plan tested
- [ ] Monitoring alerts active
- [ ] Support team ready

---

This deployment manual provides comprehensive guidance for successfully deploying and operating the Claude Bridge System in production. Follow each section carefully and customize the procedures for your specific environment.