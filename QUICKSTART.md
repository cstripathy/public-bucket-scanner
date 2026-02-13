# Bucket Scanner - Quick Reference

## 🚀 Quick Start (1 minute)

```bash
# From project root
cp .env.example .env
docker compose up -d --build
```

Access: http://localhost:8000/docs

---

## 📌 Common Commands

### Docker Operations
```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# View logs
docker compose logs -f

# Restart service
docker compose restart api

# Scale workers
docker compose up -d --scale worker=5
```

### API Calls
```bash
# Immediate scan (all providers)
curl -X POST http://localhost:8000/api/v1/scan/immediate \
  -H "Content-Type: application/json" \
  -d '{"bucket_name": "example-bucket"}'

# Scan specific provider
curl -X POST http://localhost:8000/api/v1/scan/immediate \
  -H "Content-Type: application/json" \
  -d '{"bucket_name": "example-bucket", "provider": "aws_s3"}'

# Queue scan
curl -X POST http://localhost:8000/api/v1/scan/queue \
  -H "Content-Type: application/json" \
  -d '{"bucket_name": "example-bucket", "priority": 10}'

# Get results
curl http://localhost:8000/api/v1/results/example-bucket

# Get all public buckets
curl http://localhost:8000/api/v1/public-buckets

# Get statistics
curl http://localhost:8000/api/v1/statistics

# Get findings (critical only)
curl http://localhost:8000/api/v1/findings?severity=critical
```

---

## 🎯 Supported Providers

| Provider | Code | Pattern |
|----------|------|---------|
| AWS S3 | `aws_s3` | bucket-name.s3.amazonaws.com |
| GCP Cloud Storage | `gcp_gcs` | storage.googleapis.com/bucket-name |
| Azure Blob Storage | `azure_blob` | account.blob.core.windows.net/container |

---

## 🔍 Detection Methods

### AWS S3
- ✅ Anonymous LIST operation
- ✅ Bucket ACL analysis (AllUsers, AuthenticatedUsers)
- ✅ Bucket policy parsing
- ✅ Public Access Block settings

### GCP Cloud Storage
- ✅ Anonymous GET/LIST operations
- ✅ IAM policy analysis (allUsers, allAuthenticatedUsers)
- ✅ Bucket permissions

### Azure Blob Storage
- ✅ Anonymous container listing
- ✅ Public Access Level check
- ✅ Blob-level access tests

---

## 📊 Risk Levels

| Level | Description |
|-------|-------------|
| 🔴 **Critical** | Public write access or sensitive data exposed |
| 🟠 **High** | Public bucket with sensitive files |
| 🟡 **Medium** | Public read-only bucket with files |
| 🟢 **Low** | Private bucket or public but empty |

---

## 🔧 Configuration Quick Reference

### Rate Limiting
```bash
MAX_REQUESTS_PER_SECOND=10  # Requests per second
MAX_CONCURRENT_WORKERS=50   # Max parallel workers
```

### Providers
```bash
# AWS
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1

# GCP
GCP_PROJECT_ID=your_project
GCP_CREDENTIALS_PATH=/path/to/creds.json

# Azure
AZURE_ACCOUNT_NAME=your_account
AZURE_ACCOUNT_KEY=your_key
```

### Notifications
```bash
ENABLE_NOTIFICATIONS=true
SLACK_WEBHOOK=https://hooks.slack.com/services/YOUR/WEBHOOK
WEBHOOK_URL=https://your-webhook.com/endpoint
```

---

## 📁 Project Structure

```
task001/
├── src/                    # Source code
│   ├── scanner/           # Cloud scanners (AWS/GCP/Azure)
│   ├── workers/           # DNS, HTTP, Permission, Content workers
│   ├── queue/             # Producer/Consumer
│   ├── api/               # FastAPI REST API
│   ├── database/          # PostgreSQL models
│   ├── utils/             # Rate limiter, IP rotator, Notifier
│   └── config/            # Settings
├── docker/                # Docker Compose setup
├── docs/                  # Documentation
├── tests/                 # Test suite
└── requirements.txt       # Python dependencies
```

---

## 🐛 Troubleshooting

### Services won't start
```bash
docker compose down -v
docker compose up -d
```

### Worker not processing
```bash
docker compose logs worker
docker compose restart worker
```

### Database issues
```bash
docker compose restart postgres
sleep 10
docker compose restart api worker
```

### Check queue size
```bash
curl http://localhost:8000/api/v1/queue/size
```

### Clear Redis queue
```bash
docker exec bucket-scanner-redis redis-cli FLUSHALL
```

---

## 📈 Monitoring

- **API Docs**: http://localhost:8000/docs
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

---

## 🔐 Security Best Practices

1. ✅ Change default passwords in `.env`
2. ✅ Use readonly credentials when possible
3. ✅ Enable rate limiting
4. ✅ Respect cloud provider ToS
5. ✅ Only scan authorized targets
6. ✅ Secure API with authentication (production)
7. ✅ Use HTTPS with SSL certificates

---

## 🎓 Learning Resources

- [AWS S3 Permissions](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-overview.html)
- [GCP IAM](https://cloud.google.com/storage/docs/access-control/iam)
- [Azure Blob Security](https://docs.microsoft.com/en-us/azure/storage/blobs/security-recommendations)

---

## 📞 Getting Help

1. Check logs: `docker compose logs -f`
2. Review [API.md](docs/API.md) for API details
3. See [DEVELOPMENT.md](docs/DEVELOPMENT.md) for dev setup
4. Check [DEPLOYMENT.md](docs/DEPLOYMENT.md) for production

---

## 💡 Pro Tips

- Use `priority` in queue scans for urgent buckets
- Scale workers dynamically based on queue size
- Enable notifications for critical findings only
- Use provider-specific scans when you know the cloud
- Configure IP rotation for large-scale scanning
- Set up Grafana alerts for monitoring

---

## 📝 License

MIT License - See LICENSE file for details

---

## ⚠️ Legal Disclaimer

This tool is for authorized security testing only. Always obtain proper authorization before scanning systems. The authors are not responsible for misuse.
