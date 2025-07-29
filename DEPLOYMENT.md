# Claude Bridge System - Deployment Guide
Production deployment documentation and procedures

## 📋 Overview

This guide covers the deployment procedures for the Claude Bridge System, including both staging and production environments. The system is designed for containerized deployment using Docker Compose with comprehensive monitoring and security features.

## 🏗️ Architecture Overview

### Production Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │     Nginx       │    │ Claude Bridge   │
│    (External)   │───▶│  Reverse Proxy  │───▶│   Application   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                       ┌─────────────────┐             │
                       │   PostgreSQL    │◀────────────┤
                       │    Database     │             │
                       └─────────────────┘             │
                                                        │
                       ┌─────────────────┐             │
                       │     Redis       │◀────────────┘
                       │     Cache       │
                       └─────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Prometheus    │    │     Grafana     │    │    Fluentd      │
│   Monitoring    │    │   Dashboard     │    │   Log Aggreg.   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Docker Engine 20.10+ 
- Docker Compose 2.0+
- Git
- Minimum 4GB RAM, 2 CPU cores
- 20GB available disk space

### 1. Clone Repository
```bash
git clone https://github.com/your-org/claude-bridge-system.git
cd claude-bridge-system
```

### 2. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit configuration (REQUIRED)
nano .env
```

**Critical Environment Variables:**
```bash
# Security (MUST CHANGE)
POSTGRES_PASSWORD=your_secure_postgres_password
REDIS_PASSWORD=your_secure_redis_password
JWT_SECRET=your_jwt_secret_key_minimum_32_characters
GRAFANA_PASSWORD=your_secure_grafana_password

# Application
ENVIRONMENT=production
LOG_LEVEL=INFO

# Network (adjust as needed)
HTTP_PORT=80
HTTPS_PORT=443
```

### 3. SSL Certificate Setup
```bash
# Create certificate directory
mkdir -p docker/ssl

# Option A: Self-signed certificate (development)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout docker/ssl/server.key \
  -out docker/ssl/server.crt

# Option B: Use your own certificates
cp your-certificate.crt docker/ssl/server.crt
cp your-private-key.key docker/ssl/server.key
```

### 4. Deploy
```bash
# Build and start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f claude-bridge
```

## 🔧 Detailed Configuration

### Database Setup
The PostgreSQL database is automatically initialized with the required schema. For custom initialization:

```sql
-- docker/init-db.sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Custom schemas, users, permissions here
```

### Monitoring Setup
The system includes comprehensive monitoring with Prometheus and Grafana:

**Prometheus Metrics:**
- Application metrics: `http://localhost:9091`
- System metrics: `http://localhost:9090/metrics`

**Grafana Dashboard:**
- URL: `http://localhost:3000`
- Default credentials: `admin` / `${GRAFANA_PASSWORD}`

### Backup Configuration
Automated backups are configured via environment variables:

```bash
# Local backup
BACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=365

# S3 backup (optional)
BACKUP_S3_BUCKET=your-backup-bucket
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
```

## 🔒 Security Configuration

### SSL/TLS Configuration
The system supports multiple SSL configurations:

1. **Self-signed certificates** (development)
2. **CA-signed certificates** (production)
3. **Let's Encrypt** (with manual setup)

### Access Control
Configure CORS and rate limiting in `config/production.yaml`:

```yaml
security:
  cors:
    origins: ["https://yourdomain.com"]
    credentials: true
  
  rate_limiting:
    enabled: true
    requests_per_minute: 100
```

### Authentication
The system supports multiple authentication methods:
- JWT tokens
- API keys
- Session-based authentication

## 📊 Monitoring and Alerting

### Health Checks
The system includes comprehensive health checks:

```bash
# Manual health check
curl https://your-domain.com/health

# Docker health check
docker-compose exec claude-bridge /usr/local/bin/healthcheck.sh
```

### Monitoring Endpoints
- **Application metrics**: `/metrics`
- **Health status**: `/health`
- **API status**: `/api/status`

### Log Management
Logs are structured and aggregated using Fluentd:

- **Application logs**: `/app/logs/claude_bridge.log`
- **Audit logs**: `/app/logs/audit/`
- **Nginx logs**: `/var/log/nginx/`

## 🚀 Deployment Environments

### Staging Deployment
```bash
# Use staging configuration
cp .env.staging .env

# Deploy to staging
docker-compose -f docker-compose.yml -f docker-compose.staging.yml up -d

# Run smoke tests
python scripts/smoke_tests.py --environment staging
```

### Production Deployment
```bash
# Production environment
export ENVIRONMENT=production

# Deploy with production overrides
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Verify deployment
python scripts/health_check.py --environment production
```

## 🔄 CI/CD Integration

### GitHub Actions
The repository includes a complete CI/CD pipeline:

```yaml
# .github/workflows/ci-cd.yml
# - Code quality checks
# - Security scanning
# - Automated testing
# - Docker image building
# - Deployment automation
```

### Manual Deployment
For manual deployments:

```bash
# Build image
docker build -t claude-bridge:latest .

# Tag for registry
docker tag claude-bridge:latest ghcr.io/your-org/claude-bridge:latest

# Push to registry
docker push ghcr.io/your-org/claude-bridge:latest

# Deploy
docker-compose pull
docker-compose up -d
```

## 🛠️ Maintenance

### Regular Maintenance Tasks

#### Daily
```bash
# Check service status
docker-compose ps

# Check logs for errors
docker-compose logs --tail=100 claude-bridge | grep ERROR

# Verify backups
ls -la backups/
```

#### Weekly
```bash
# Update system packages (if applicable)
docker-compose pull

# Clean up old containers
docker system prune

# Review monitoring alerts
curl http://localhost:9091/api/v1/alerts
```

#### Monthly
```bash
# Security scan
docker-compose exec claude-bridge python -m claude_bridge.security.scanner

# Performance analysis
docker-compose exec claude-bridge python -m claude_bridge.performance.profiler

# Backup verification
python scripts/verify_backups.py
```

### Database Maintenance
```bash
# Database backup
docker-compose exec postgres pg_dump -U claude claude_bridge > backup.sql

# Database restore
cat backup.sql | docker-compose exec -T postgres psql -U claude claude_bridge

# Vacuum and analyze
docker-compose exec postgres psql -U claude -d claude_bridge -c "VACUUM ANALYZE;"
```

## 🚨 Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check logs
docker-compose logs claude-bridge

# Check resource usage
docker stats

# Verify configuration
docker-compose config
```

#### Database Connection Issues
```bash
# Check PostgreSQL status
docker-compose exec postgres pg_isready -U claude

# Check connection from application
docker-compose exec claude-bridge python -c "
import psycopg2
conn = psycopg2.connect('postgresql://claude:password@postgres:5432/claude_bridge')
print('Connection successful')
"
```

#### Performance Issues
```bash
# Check system resources
docker-compose exec claude-bridge python -m claude_bridge.monitoring.health_checker

# Analyze performance
docker-compose exec claude-bridge python -m claude_bridge.performance.profiler --analyze

# Check database performance
docker-compose exec postgres psql -U claude -d claude_bridge -c "
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;
"
```

### Emergency Procedures

#### System Recovery
```bash
# Stop all services
docker-compose down

# Restore from backup
./scripts/restore_from_backup.sh latest

# Restart services
docker-compose up -d

# Verify system health
./scripts/health_check.sh
```

#### Rollback Deployment
```bash
# Rollback to previous image
docker-compose down
docker-compose pull previous-tag
docker-compose up -d
```

## 📞 Support

### Getting Help
- **Documentation**: Check this file and inline code documentation
- **Logs**: Review application and system logs
- **Monitoring**: Check Grafana dashboards for system status
- **Issues**: Create GitHub issues for bugs or feature requests

### Emergency Contacts
- **System Administrator**: admin@yourdomain.com
- **DevOps Team**: devops@yourdomain.com
- **On-call Engineer**: oncall@yourdomain.com

## 📈 Performance Tuning

### Application Tuning
```yaml
# config/production.yaml
server:
  workers: 4  # Adjust based on CPU cores
  max_connections: 1000  # Adjust based on load

database:
  pool_size: 20  # Adjust based on concurrent users
  max_overflow: 30
```

### Infrastructure Tuning
```bash
# Increase file descriptor limits
echo "fs.file-max = 65536" >> /etc/sysctl.conf

# Optimize Docker
echo '{"log-driver": "json-file", "log-opts": {"max-size": "10m", "max-file": "3"}}' > /etc/docker/daemon.json
```

## 🔐 Security Hardening

### Container Security
```bash
# Run security scan
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image claude-bridge:latest

# Update base images regularly
docker-compose pull
docker-compose up -d
```

### Network Security
```bash
# Configure firewall (example for Ubuntu)
ufw allow 80/tcp
ufw allow 443/tcp
ufw deny 5432/tcp  # Block direct database access
ufw enable
```

This deployment guide provides comprehensive instructions for production deployment of the Claude Bridge System. Follow the procedures carefully and refer to the troubleshooting section for common issues.