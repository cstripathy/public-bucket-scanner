# API Documentation

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
Currently, the API does not require authentication. In production, implement OAuth2/JWT tokens.

---

## Endpoints

### Scan Operations

#### POST /scan/immediate
Perform an immediate (synchronous) bucket scan.

**Request Body:**
```json
{
  "bucket_name": "example-bucket",
  "provider": "aws_s3",
  "priority": 0
}
```

**Parameters:**
- `bucket_name` (required): Name of the bucket to scan
- `provider` (optional): Cloud provider (`aws_s3`, `gcp_gcs`, `azure_blob`). Omit to scan all providers.
- `priority` (optional): Priority level (default: 0)

**Response:**
```json
[
  {
    "id": 1,
    "bucket_name": "example-bucket",
    "provider": "aws_s3",
    "exists": true,
    "is_accessible": true,
    "access_level": "public-read",
    "url": "https://example-bucket.s3.amazonaws.com",
    "permissions": ["list", "get_acl"],
    "files_found": ["file1.txt", "file2.jpg"],
    "sensitive_files": [".env"],
    "risk_level": "high",
    "risk_score": 75,
    "created_at": "2026-02-11T10:30:00Z"
  }
]
```

**Status Codes:**
- `200`: Success
- `400`: Invalid request
- `500`: Server error

---

#### POST /scan/queue
Queue a bucket scan for asynchronous processing.

**Request Body:**
```json
{
  "bucket_name": "example-bucket",
  "provider": "aws_s3",
  "priority": 10
}
```

**Response:**
```json
{
  "task_id": 123,
  "bucket_name": "example-bucket",
  "status": "queued",
  "message": "Scan queued successfully. Task ID: 123"
}
```

---

### Results

#### GET /results
Get recent scan results.

**Query Parameters:**
- `limit` (optional): Maximum results to return (default: 50, max: 500)

**Response:**
```json
[
  {
    "id": 1,
    "bucket_name": "example-bucket",
    "provider": "aws_s3",
    "exists": true,
    "is_accessible": true,
    "access_level": "public-read",
    "url": "https://example-bucket.s3.amazonaws.com",
    "risk_level": "high",
    "risk_score": 75,
    "created_at": "2026-02-11T10:30:00Z"
  }
]
```

---

#### GET /results/{bucket_name}
Get scan results for a specific bucket.

**Path Parameters:**
- `bucket_name`: Name of the bucket

**Query Parameters:**
- `limit` (optional): Maximum results (default: 10)

**Response:** Same as `/results`

---

#### GET /public-buckets
Get all publicly accessible buckets found.

**Query Parameters:**
- `limit` (optional): Maximum results (default: 100)

**Response:** Same as `/results`, filtered for accessible buckets

---

### Findings

#### GET /findings
Get security findings with optional filters.

**Query Parameters:**
- `status` (optional): Filter by status (`open`, `acknowledged`, `resolved`, `false_positive`)
- `severity` (optional): Filter by severity (`low`, `medium`, `high`, `critical`)
- `limit` (optional): Maximum results (default: 100)

**Response:**
```json
[
  {
    "id": 1,
    "scan_result_id": 123,
    "bucket_name": "example-bucket",
    "provider": "aws_s3",
    "finding_type": "public_bucket",
    "severity": "high",
    "title": "Publicly accessible bucket with sensitive files",
    "description": "Bucket allows public read access and contains credential files",
    "file_path": ".env",
    "url": "https://example-bucket.s3.amazonaws.com/.env",
    "recommendations": [
      "Remove public access",
      "Rotate exposed credentials",
      "Enable access logging"
    ],
    "status": "open",
    "created_at": "2026-02-11T10:30:00Z"
  }
]
```

---

#### GET /findings/{bucket_name}
Get all findings for a specific bucket.

**Path Parameters:**
- `bucket_name`: Name of the bucket

**Response:** Same as `/findings`

---

### Tasks

#### GET /task/{task_id}
Get status of a queued scan task.

**Path Parameters:**
- `task_id`: ID of the task

**Response:**
```json
{
  "id": 123,
  "bucket_name": "example-bucket",
  "provider": "aws_s3",
  "status": "completed",
  "priority": 10,
  "result_count": 3,
  "error": null,
  "created_at": "2026-02-11T10:00:00Z",
  "started_at": "2026-02-11T10:05:00Z",
  "completed_at": "2026-02-11T10:10:00Z"
}
```

**Task Statuses:**
- `pending`: Waiting in queue
- `processing`: Currently being processed
- `completed`: Successfully completed
- `failed`: Processing failed

---

### Queue

#### GET /queue/size
Get current queue size.

**Response:**
```json
{
  "queue_size": 42
}
```

---

### Statistics

#### GET /statistics
Get overall scanning statistics.

**Response:**
```json
{
  "total_scans": 1234,
  "public_buckets": 156,
  "open_findings": {
    "critical": 5,
    "high": 23,
    "medium": 87
  }
}
```

---

## Response Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request - Invalid parameters |
| 404 | Not Found |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

---

## Rate Limiting

The API implements rate limiting to prevent abuse:
- Default: 10 requests per second per IP
- Configurable via `MAX_REQUESTS_PER_SECOND` environment variable

Rate limit headers:
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1613045678
```

---

## Examples

### Python
```python
import requests

# Immediate scan
response = requests.post(
    "http://localhost:8000/api/v1/scan/immediate",
    json={"bucket_name": "example-bucket"}
)
results = response.json()

# Get public buckets
response = requests.get("http://localhost:8000/api/v1/public-buckets")
buckets = response.json()
```

### cURL
```bash
# Scan bucket
curl -X POST http://localhost:8000/api/v1/scan/immediate \
  -H "Content-Type: application/json" \
  -d '{"bucket_name": "example-bucket"}'

# Get statistics  
curl http://localhost:8000/api/v1/statistics
```

### JavaScript/Node.js
```javascript
const axios = require('axios');

async function scanBucket(bucketName) {
  const response = await axios.post(
    'http://localhost:8000/api/v1/scan/immediate',
    { bucket_name: bucketName }
  );
  return response.data;
}

scanBucket('example-bucket').then(console.log);
```

---

## Interactive Documentation

FastAPI provides automatic interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These interfaces allow you to:
- Browse all endpoints
- Test requests directly
- View request/response schemas
- Download OpenAPI specification
