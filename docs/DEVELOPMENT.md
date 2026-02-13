# Development Guide

## Local Development Setup

This guide covers setting up a local development environment for Bucket Scanner.

---

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git
- VS Code or PyCharm (recommended)

---

## Initial Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd task001
```

### 2. Create Virtual Environment

```bash
# Create venv
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt

# Install dev dependencies
pip install pytest pytest-asyncio pytest-cov black flake8 mypy
```

### 4. Start Infrastructure

```bash
cd docker
docker compose up -d postgres redis

# Wait for services to be healthy
docker compose ps
```

### 5. Configure Environment

Create `.env` in project root:

```bash
# Development settings
DEBUG=true

# Database
POSTGRES_USER=scanner
POSTGRES_PASSWORD=scanner_pass
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=bucket_scanner

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Test credentials (use test accounts)
AWS_ACCESS_KEY_ID=test_key
AWS_SECRET_ACCESS_KEY=test_secret
```

### 6. Initialize Database

```bash
python -c "
from src.database import DatabaseRepository
import asyncio

async def init():
    db = DatabaseRepository()
    await db.init_db()

asyncio.run(init())
"
```

---

## Running Locally

### API Server

```bash
# Development mode with auto-reload
uvicorn src.api.main:app --reload --port 8000

# Or with environment
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

Access at: http://localhost:8000/docs

### Worker Service

```bash
python -m src.worker_service
```

### Interactive Testing

```bash
# Python REPL
python

>>> from src.scanner import AWSS3Scanner
>>> scanner = AWSS3Scanner()
>>> import asyncio
>>> result = asyncio.run(scanner.scan_bucket("example-bucket"))
>>> print(result)
```

---

## Project Structure

```
task001/
├── src/                    # Source code
│   ├── scanner/           # Scanner implementations
│   │   ├── base_scanner.py      # Base class
│   │   ├── aws_scanner.py       # AWS S3 scanner
│   │   ├── gcp_scanner.py       # GCP scanner
│   │   ├── azure_scanner.py     # Azure scanner
│   │   └── orchestrator.py      # Multi-cloud orchestrator
│   ├── workers/           # Worker components
│   │   ├── dns_resolver.py      # DNS resolution
│   │   ├── http_probe.py        # HTTP probing
│   │   ├── permission_checker.py # Permission analysis
│   │   └── content_analyzer.py   # Content analysis
│   ├── queue/             # Queue system
│   │   ├── producer.py          # Task producer
│   │   └── consumer.py          # Task consumer
│   ├── api/               # REST API
│   │   ├── main.py              # FastAPI app
│   │   └── routes.py            # API routes
│   ├── database/          # Database
│   │   ├── models.py            # SQLAlchemy models
│   │   └── repository.py        # Database operations
│   ├── utils/             # Utilities
│   │   ├── rate_limiter.py      # Rate limiting
│   │   ├── ip_rotator.py        # IP rotation
│   │   └── notifier.py          # Notifications
│   └── config/            # Configuration
│       └── settings.py          # Settings management
├── tests/                 # Test suite
├── docs/                  # Documentation
├── docker/                # Docker configuration
└── requirements.txt       # Python dependencies
```

---

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/new-scanner
```

### 2. Make Changes

Edit files, add features, fix bugs...

### 3. Run Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific test
pytest tests/test_scanner/test_aws_scanner.py -v
```

### 4. Code Quality

```bash
# Format code
black src/

# Lint
flake8 src/

# Type checking
mypy src/
```

### 5. Commit and Push

```bash
git add .
git commit -m "Add new scanner feature"
git push origin feature/new-scanner
```

---

## Testing

### Unit Tests

```python
# tests/test_scanner/test_aws_scanner.py
import pytest
from src.scanner import AWSS3Scanner

@pytest.mark.asyncio
async def test_bucket_exists():
    scanner = AWSS3Scanner()
    result = await scanner.check_bucket_exists("test-bucket")
    assert isinstance(result, bool)
```

### Integration Tests

```python
# tests/test_integration/test_api.py
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_scan_endpoint():
    response = client.post(
        "/api/v1/scan/immediate",
        json={"bucket_name": "test-bucket"}
    )
    assert response.status_code == 200
```

### Running Tests

```bash
# All tests
pytest

# Specific module
pytest tests/test_scanner/

# With markers
pytest -m "not slow"

# Verbose
pytest -v -s
```

---

## Debugging

### VS Code Configuration

`.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "src.api.main:app",
        "--reload"
      ],
      "jinja": true,
      "justMyCode": false
    },
    {
      "name": "Python: Worker",
      "type": "python",
      "request": "launch",
      "module": "src.worker_service",
      "console": "integratedTerminal"
    }
  ]
}
```

### PyCharm Configuration

1. Run > Edit Configurations
2. Add Python configuration
3. Script path: `/path/to/src/api/main.py`
4. Parameters: `--reload`

### Logging

```python
import structlog

logger = structlog.get_logger()

# Debug logging
logger.debug("debug_message", extra_data="value")
logger.info("info_message", bucket="test")
logger.error("error_message", error=str(e))
```

---

## Database Management

### Migrations with Alembic

```bash
# Initialize alembic
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Add new column"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Direct Database Access

```bash
# PostgreSQL CLI
docker exec -it bucket-scanner-postgres psql -U scanner bucket_scanner

# Redis CLI
docker exec -it bucket-scanner-redis redis-cli
```

---

## Adding New Features

### New Cloud Provider

1. Create scanner class:

```python
# src/scanner/newprovider_scanner.py
from .base_scanner import BaseScanner, CloudProvider

class NewProviderScanner(BaseScanner):
    def __init__(self):
        super().__init__(CloudProvider.NEW_PROVIDER)
    
    async def check_bucket_exists(self, bucket_name: str) -> bool:
        # Implementation
        pass
```

2. Update orchestrator:

```python
# src/scanner/orchestrator.py
from .newprovider_scanner import NewProviderScanner

self.scanners[CloudProvider.NEW_PROVIDER] = NewProviderScanner()
```

3. Add tests:

```python
# tests/test_scanner/test_newprovider.py
@pytest.mark.asyncio
async def test_new_provider_scan():
    scanner = NewProviderScanner()
    result = await scanner.scan_bucket("test")
    assert result is not None
```

### New API Endpoint

1. Add route:

```python
# src/api/routes.py
@router.get("/custom-endpoint")
async def custom_endpoint():
    return {"message": "Custom response"}
```

2. Add tests:

```python
# tests/test_api/test_routes.py
def test_custom_endpoint():
    response = client.get("/api/v1/custom-endpoint")
    assert response.status_code == 200
```

---

## Performance Profiling

### Memory Profiling

```bash
pip install memory-profiler

# Profile function
from memory_profiler import profile

@profile
async def my_function():
    # Code to profile
    pass
```

### API Profiling

```bash
pip install py-spy

# Profile running process
py-spy record -o profile.svg --pid <pid>
```

---

## Common Tasks

### Reset Database

```bash
python -c "
from src.database import DatabaseRepository
import asyncio

async def reset():
    db = DatabaseRepository()
    await db.drop_db()
    await db.init_db()

asyncio.run(reset())
"
```

### Clear Redis Queue

```bash
docker exec bucket-scanner-redis redis-cli FLUSHALL
```

### Generate Test Data

```python
# scripts/generate_test_data.py
from src.database import DatabaseRepository
import asyncio

async def generate():
    db = DatabaseRepository()
    for i in range(100):
        await db.create_scan_result({
            'bucket_name': f'test-bucket-{i}',
            'provider': 'aws_s3',
            'exists': True,
            'is_accessible': i % 3 == 0,
            'access_level': 'public-read',
            'url': f'https://test-bucket-{i}.s3.amazonaws.com',
            'permissions': ['list'],
            'risk_level': 'medium',
            'risk_score': 50
        })

asyncio.run(generate())
```

---

## Troubleshooting

### Import Errors

```bash
# Ensure src is in PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Test connection
psql -h localhost -U scanner -d bucket_scanner
```

### Redis Connection Issues

```bash
# Test Redis
docker exec bucket-scanner-redis redis-cli ping
```

---

## Code Style Guide

### Python Conventions

- Follow PEP 8
- Use type hints
- Document with docstrings
- Max line length: 100

### Example:

```python
async def scan_bucket(
    self,
    bucket_name: str,
    provider: Optional[CloudProvider] = None
) -> List[BucketScanResult]:
    """Scan a bucket across providers.
    
    Args:
        bucket_name: Name of the bucket
        provider: Specific provider or None for all
        
    Returns:
        List of scan results
        
    Raises:
        ValueError: If bucket_name is invalid
    """
    if not bucket_name:
        raise ValueError("bucket_name cannot be empty")
    
    # Implementation
    pass
```

---

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)
- [Boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [Redis Documentation](https://redis.io/documentation)
- [Docker Documentation](https://docs.docker.com/)
