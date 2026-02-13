# Deployment Guide

## Production Deployment

This guide covers deploying Bucket Scanner to production environments.

---

## Prerequisites

- Docker & Docker Compose
- Ubuntu 20.04+ or similar Linux distribution
- Minimum 4GB RAM, 2 CPU cores
- 50GB disk space
- Domain name (optional, for HTTPS)

---

## Quick Deploy

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose plugin
sudo apt install docker-compose-plugin -y

# Add user to docker group (optional if not already added)
sudo usermod -aG docker $USER
newgrp docker
```

### 2. Clone Repository

```bash
git clone <repository-url>
cd task001
```

### 3. Configure Environment

```bash
cd docker
cp .env.example .env

# Edit configuration
nano .env
```

**Critical Settings:**
```bash
# Change default passwords
POSTGRES_PASSWORD=<strong-password>
REDIS_PASSWORD=<strong-password>
GRAFANA_PASSWORD=<strong-password>

# Configure credentials (if needed)
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>

# Enable notifications
ENABLE_NOTIFICATIONS=true
SLACK_WEBHOOK=https://hooks.slack.com/services/YOUR/WEBHOOK
```

### 4. Start Services

```bash
docker compose up -d
```

### 5. Verify Deployment

```bash
# Check service status
docker compose ps

# View logs
docker compose logs -f

# Test API
curl http://localhost:8000/health
```

---

## Production Configuration

### Enable HTTPS

Create `docker/nginx.conf`:

```nginx
server {
    listen 80;
    server_name scanner.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name scanner.yourdomain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    location / {
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Add to `docker-compose.yml`:

```yaml
  nginx:
    image: nginx:alpine
    container_name: bucket-scanner-nginx
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - ./ssl:/etc/nginx/ssl
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - api
    networks:
      - scanner-network
```

### Database Backups

Create backup script `backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

docker exec bucket-scanner-postgres pg_dump \
  -U scanner bucket_scanner \
  > "$BACKUP_DIR/backup_$DATE.sql"

# Keep only last 7 days
find $BACKUP_DIR -name "backup_*.sql" -mtime +7 -delete
```

Add to crontab:
```bash
0 2 * * * /path/to/backup.sh
```

### Monitoring Alerts

Configure Alertmanager (`docker/alertmanager.yml`):

```yaml
global:
  slack_api_url: '<your-webhook-url>'

route:
  receiver: 'slack-notifications'

receivers:
  - name: 'slack-notifications'
    slack_configs:
      - channel: '#alerts'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
```

---

## Scaling

### Horizontal Scaling

Scale workers:
```bash
docker compose up -d --scale worker=10
```

### Database Optimization

PostgreSQL tuning in `docker-compose.yml`:

```yaml
  postgres:
    environment:
      POSTGRES_SHARED_BUFFERS: 512MB
      POSTGRES_EFFECTIVE_CACHE_SIZE: 2GB
      POSTGRES_WORK_MEM: 16MB
      POSTGRES_MAINTENANCE_WORK_MEM: 256MB
```

### Redis Optimization

```yaml
  redis:
    command: >
      redis-server
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
      --appendonly yes
```

---

## Security Hardening

### 1. Firewall Configuration

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable
```

### 2. Restrict Database Access

In `docker-compose.yml`, remove postgres port exposure:

```yaml
  postgres:
    # ports:
    #   - "5432:5432"  # Comment out
```

### 3. Enable Authentication

Add API authentication in `src/api/main.py`:

```python
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.middleware("http")
async def verify_token(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        token = request.headers.get("Authorization")
        # Verify token...
    return await call_next(request)
```

### 4. Secrets Management

Use Docker secrets or external secret managers:

```yaml
secrets:
  postgres_password:
    file: ./secrets/postgres_password.txt

services:
  postgres:
    secrets:
      - postgres_password
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
```

---

## Monitoring Setup

### Grafana Dashboards

1. Access Grafana: http://your-server:3000
2. Add Prometheus data source
3. Import dashboards:
   - Dashboard ID: 1860 (Node Exporter)
   - Dashboard ID: 3662 (Prometheus Self)
   - Custom: Bucket Scanner metrics

### Log Aggregation

Add Loki for log aggregation:

```yaml
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    volumes:
      - ./loki-config.yaml:/etc/loki/local-config.yaml
    networks:
      - scanner-network
```

---

## Maintenance

### Update Application

```bash
# Pull latest code
git pull

# Rebuild containers
docker compose build

# Restart with zero downtime
docker compose up -d --no-deps --build api worker
```

### Database Migrations

```bash
# Run migrations
docker compose exec api alembic upgrade head
```

### Log Rotation

Configure in `/etc/docker/daemon.json`:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

---

## Troubleshooting

### High Memory Usage

```bash
# Check memory
docker stats

# Restart services if needed
docker compose restart
```

### Slow Queries

```bash
# Monitor slow queries
docker exec -it bucket-scanner-postgres \
  psql -U scanner -d bucket_scanner \
  -c "SELECT * FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```

### Worker Issues

```bash
# Check worker logs
docker compose logs worker

# Restart workers
docker compose restart worker

# Scale down/up
docker compose up -d --scale worker=0
docker compose up -d --scale worker=5
```

---

## Performance Tuning

### API Workers

Adjust Uvicorn workers:

```yaml
  api:
    command: uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 8
```

### Connection Pooling

PostgreSQL connection pool settings:

```python
# src/database/repository.py
self.engine = create_async_engine(
    db_url,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True
)
```

---

## Disaster Recovery

### Backup Strategy

1. **Database**: Daily backups via pg_dump
2. **Redis**: AOF persistence enabled
3. **Config**: Version controlled

### Recovery Procedure

```bash
# Restore database
docker exec -i bucket-scanner-postgres \
  psql -U scanner bucket_scanner < backup.sql

# Restart services
docker compose restart
```

---

## Cost Optimization

### AWS Costs

- Use anonymous scanning when possible
- Implement exponential backoff
- Cache DNS results

### Infrastructure

- Use spot instances for workers
- Auto-scaling based on queue size
- Schedule scans during off-peak hours

---

## Compliance

### Data Retention

Configure automatic cleanup:

```sql
-- Delete old scan results (>90 days)
DELETE FROM scan_results 
WHERE created_at < NOW() - INTERVAL '90 days';
```

### Audit Logging

Enable comprehensive logging:

```python
# Log all API requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info("api_request", path=request.url.path, method=request.method)
    return await call_next(request)
```

---

## Support

For production issues:
1. Check logs: `docker compose logs -f`
2. Review metrics in Grafana
3. Enable debug mode temporarily
4. Contact support with log excerpts
