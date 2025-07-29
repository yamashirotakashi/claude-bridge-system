#!/bin/bash
# Claude Bridge System - Health Check Script
# Production health monitoring for Docker containers

set -e

# Configuration
HEALTH_TIMEOUT=10
API_PORT=${BRIDGE_PORT:-8080}
METRICS_PORT=${METRICS_PORT:-9090}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Health check functions
check_api_health() {
    echo "Checking API health..."
    if curl -f -s --max-time $HEALTH_TIMEOUT "http://localhost:$API_PORT/health" > /dev/null; then
        echo -e "${GREEN}✓ API health check passed${NC}"
        return 0
    else
        echo -e "${RED}✗ API health check failed${NC}"
        return 1
    fi
}

check_metrics_endpoint() {
    echo "Checking metrics endpoint..."
    if curl -f -s --max-time $HEALTH_TIMEOUT "http://localhost:$METRICS_PORT/metrics" > /dev/null; then
        echo -e "${GREEN}✓ Metrics endpoint accessible${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ Metrics endpoint not accessible${NC}"
        return 0  # Non-critical
    fi
}

check_database_connection() {
    echo "Checking database connectivity..."
    if python3 -c "
import os
import psycopg2
import sys

try:
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'postgres'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        database=os.getenv('POSTGRES_DB', 'claude_bridge'),
        user=os.getenv('POSTGRES_USER', 'claude'),
        password=os.getenv('POSTGRES_PASSWORD', ''),
        connect_timeout=5
    )
    conn.close()
    print('✓ Database connection successful')
    sys.exit(0)
except Exception as e:
    print(f'✗ Database connection failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
        echo -e "${GREEN}✓ Database connection healthy${NC}"
        return 0
    else
        echo -e "${RED}✗ Database connection failed${NC}"
        return 1
    fi
}

check_redis_connection() {
    echo "Checking Redis connectivity..."
    if python3 -c "
import os
import redis
import sys

try:
    r = redis.Redis(
        host=os.getenv('REDIS_HOST', 'redis'),
        port=int(os.getenv('REDIS_PORT', '6379')),
        password=os.getenv('REDIS_PASSWORD', ''),
        socket_timeout=5,
        socket_connect_timeout=5
    )
    r.ping()
    print('✓ Redis connection successful')
    sys.exit(0)
except Exception as e:
    print(f'✗ Redis connection failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
        echo -e "${GREEN}✓ Redis connection healthy${NC}"
        return 0
    else
        echo -e "${RED}✗ Redis connection failed${NC}"
        return 1
    fi
}

check_disk_space() {
    echo "Checking disk space..."
    DISK_USAGE=$(df /app | tail -1 | awk '{print $5}' | sed 's/%//')
    
    if [ "$DISK_USAGE" -lt 80 ]; then
        echo -e "${GREEN}✓ Disk space healthy (${DISK_USAGE}% used)${NC}"
        return 0
    elif [ "$DISK_USAGE" -lt 90 ]; then
        echo -e "${YELLOW}⚠ Disk space warning (${DISK_USAGE}% used)${NC}"
        return 0  # Warning but not critical
    else
        echo -e "${RED}✗ Disk space critical (${DISK_USAGE}% used)${NC}"
        return 1
    fi
}

check_memory_usage() {
    echo "Checking memory usage..."
    MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    
    if [ "$MEMORY_USAGE" -lt 80 ]; then
        echo -e "${GREEN}✓ Memory usage healthy (${MEMORY_USAGE}% used)${NC}"
        return 0
    elif [ "$MEMORY_USAGE" -lt 90 ]; then
        echo -e "${YELLOW}⚠ Memory usage warning (${MEMORY_USAGE}% used)${NC}"
        return 0  # Warning but not critical
    else
        echo -e "${RED}✗ Memory usage critical (${MEMORY_USAGE}% used)${NC}"
        return 1
    fi
}

check_process_status() {
    echo "Checking application processes..."
    if pgrep -f "claude_bridge" > /dev/null; then
        echo -e "${GREEN}✓ Application processes running${NC}"
        return 0
    else
        echo -e "${RED}✗ Application processes not found${NC}"
        return 1
    fi
}

check_log_files() {
    echo "Checking log file accessibility..."
    LOG_DIR="/app/logs"
    
    if [ -d "$LOG_DIR" ] && [ -w "$LOG_DIR" ]; then
        echo -e "${GREEN}✓ Log directory accessible${NC}"
        return 0
    else
        echo -e "${RED}✗ Log directory not accessible${NC}"
        return 1
    fi
}

# Main health check execution
main() {
    echo "================================================"
    echo "Claude Bridge System - Health Check"
    echo "================================================"
    echo "Timestamp: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
    echo ""
    
    FAILED_CHECKS=0
    TOTAL_CHECKS=0
    
    # Critical health checks
    CRITICAL_CHECKS=(
        "check_api_health"
        "check_database_connection"
        "check_redis_connection"
        "check_process_status"
    )
    
    # Non-critical health checks
    NON_CRITICAL_CHECKS=(
        "check_metrics_endpoint"
        "check_disk_space"
        "check_memory_usage"
        "check_log_files"
    )
    
    # Run critical checks
    echo "Running critical health checks..."
    for check in "${CRITICAL_CHECKS[@]}"; do
        TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
        if ! $check; then
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
        fi
        echo ""
    done
    
    # Run non-critical checks
    echo "Running non-critical health checks..."
    for check in "${NON_CRITICAL_CHECKS[@]}"; do
        TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
        $check || true  # Don't fail on non-critical checks
        echo ""
    done
    
    # Summary
    echo "================================================"
    if [ $FAILED_CHECKS -eq 0 ]; then
        echo -e "${GREEN}✓ All critical health checks passed${NC}"
        echo "Status: HEALTHY"
        exit 0
    else
        echo -e "${RED}✗ $FAILED_CHECKS critical health check(s) failed${NC}"
        echo "Status: UNHEALTHY"
        exit 1
    fi
}

# Execute main function
main "$@"