# 🔍 Bucket Name Enumeration Module

## Overview

The enumeration module completes the **Bucket Scanner Architecture** by providing intelligent bucket name discovery capabilities. Instead of requiring manual input, the system can now automatically generate and test thousands of potential bucket names across AWS S3, GCP Cloud Storage, and Azure Blob Storage.

---

## 🎯 How It Works

### **1. Pattern-Based Generation**
Generates bucket names using common organizational patterns:

```
company-[purpose]
company-[env]-[purpose]
[purpose]-company
company-[year]
company-backup-[year][month]
```

**Examples for "Acme Corp":**
- `acme-corp-backup`
- `acme-corp-prod-data`
- `acme-corp-dev-uploads`
- `backup-acme-corp`
- `acme-corp-2025`

### **2. Wordlist-Based Generation**
Combines company name with curated wordlists:

**Included Wordlists:**
- **`common.txt`** - 100+ common bucket patterns
- **`aws-specific.txt`** - AWS service-specific patterns

**Example Combinations:**
```
acme + backup    = acme-backup, backup-acme
acme + logs      = acme-logs, logs-acme
acme + static    = acme-static, static-acme
```

### **3. Common Public Patterns**
Tests frequently misconfigured bucket names:
- `backup`, `backups`, `data`
- `uploads`, `files`, `public`
- `static`, `assets`, `media`
- With variations: `backup-prod`, `data-dev`, etc.

---

## 📡 API Endpoints

### **1. Enumerate for Company**
```bash
POST /api/v1/enumerate
```

**Request**:
```json
{
  "company_name": "Acme Corp",
  "providers": ["aws_s3", "gcp_gcs", "azure_blob"],
  "use_wordlist": true,
  "wordlist_names": ["common", "aws-specific"],
  "max_names": 100,
  "auto_scan": true
}
```

**Response**:
```json
{
  "company_name": "Acme Corp",
  "names_generated": 300,
  "candidates": [
    {"bucket_name": "acme-corp-backup", "provider": "aws_s3"},
    {"bucket_name": "acme-corp-prod-data", "provider": "gcp_gcs"},
    ...
  ],
  "queued_for_scan": 300,
  "message": "Generated 300 potential bucket names, 300 queued for scanning"
}
```

### **2. List Wordlists**
```bash
GET /api/v1/enumerate/wordlists
```

**Response**:
```json
{
  "wordlists": ["common", "aws-specific"],
  "count": 2
}
```

### **3. Common Patterns**
```bash
POST /api/v1/enumerate/common-patterns?auto_scan=true
```

**Response**:
```json
{
  "patterns_generated": 252,
  "providers": ["aws_s3", "gcp_gcs", "azure_blob"],
  "queued_for_scan": 252,
  "candidates": [...]
}
```

---

## 🚀 Usage Examples

### **Example 1: Enumerate for a Company**
```bash
curl -X POST http://localhost:8000/api/v1/enumerate \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "MyCompany",
    "providers": ["aws_s3"],
    "use_wordlist": false,
    "max_names": 50,
    "auto_scan": false
  }'
```

### **Example 2: Enumerate with Wordlist + Auto-Scan**
```bash
curl -X POST http://localhost:8000/api/v1/enumerate \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "TechCorp",
    "use_wordlist": true,
    "wordlist_names": ["common"],
    "max_names": 100,
    "auto_scan": true
  }'
```

### **Example 3: Scan Common Public Patterns**
```bash
curl -X POST "http://localhost:8000/api/v1/enumerate/common-patterns?auto_scan=true" \
  -H "Content-Type: application/json"
```

---

## 📂 Wordlist Management

### **Location**
Wordlists are stored in: `wordlists/`

### **Format**
```text
# Comment lines start with #

backup
backups
data
storage
# ... more patterns
```

### **Available Wordlists**

#### **common.txt** (100+ entries)
General bucket patterns found across all cloud providers:
- Data storage: backup, data, files, documents
- Media: images, videos, uploads
- Web: static, public, cdn, website
- Environments: dev, prod, staging, test
- Departments: engineering, marketing, sales

#### **aws-specific.txt** (50+ entries)
AWS-specific patterns:
- Services: cloudtrail, lambda, elasticbeanstalk
- Regional: us-east-1, eu-west-1
- Integrations: athena, redshift, emr

### **Creating Custom Wordlists**

1. Create file: `wordlists/my-wordlist.txt`
2. Add patterns (one per line)
3. Rebuild container or copy to running container:
```bash
docker cp wordlists/my-wordlist.txt bucket-scanner-api:/app/wordlists/
```

---

## 🧠 Generation Strategies

### **Strategy 1: Common Prefixes**
```
backup, backups, data, files, uploads, downloads,
assets, static, media, images, documents
```

### **Strategy 2: Common Suffixes**
```
backup, backups, data, files, prod, production,
dev, development, staging, test, qa
```

### **Strategy 3: Environments**
```
prod, production, dev, development, staging,
test, qa, uat, demo, sandbox
```

### **Strategy 4: Separators**
```
- (hyphen)
_ (underscore)
(no separator)
```

### **Strategy 5: Date-Based**
```
company-2024
company-backup-2025
company-backup-202501
```

---

## 🔗 Integration with Architecture

### **Complete Workflow**

```
1. ENUMERATION (New!)
   ├─ Generate Names → Pattern-based / Wordlist
   ├─ Queue Tasks    → Redis queue
   └─ Priority       → Configurable

2. SCANNING
   ├─ Worker Pool    → Process queue
   ├─ DNS Resolution → Check existence
   ├─ HTTP Probes    → Verify access
   └─ Permission     → Anonymous checks

3. ANALYSIS
   ├─ Content        → List files
   ├─ Sensitive Data → Pattern matching
   └─ Risk Scoring   → Calculate severity

4. STORAGE
   ├─ PostgreSQL     → Scan results
   ├─ Findings       → Security issues
   └─ Statistics     → Aggregated data
```

### **Architecture Diagram Integration**

```
┌──────────────────┐
│   ENUMERATION    │  ← NEW MODULE
│  Name Generator  │
└────────┬─────────┘
         ↓
┌────────────────────┐
│  BUCKET DISCOVERY  │
│  DNS/HTTP Probes   │
└────────┬───────────┘
         ↓
┌────────────────────┐
│ PERMISSION CHECKS  │
│  Anonymous Access  │
└────────┬───────────┘
         ↓
┌────────────────────┐
│ CONTENT ANALYSIS   │
│  File Enumeration  │
└────────┬───────────┘
         ↓
┌────────────────────┐
│     STORAGE        │
│    PostgreSQL      │
└────────────────────┘
```

---

## 📊 Real-World Example

### **Scenario**: Security audit for "TechCorp"

```bash
# Step 1: Enumerate potential buckets
curl -X POST http://localhost:8000/api/v1/enumerate \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "TechCorp",
    "use_wordlist": true,
    "wordlist_names": ["common", "aws-specific"],
    "max_names": 200,
    "auto_scan": true
  }'
```

**Generated names** (200 total):
- techcorp-backup
- techcorp-prod-data
- techcorp-dev-uploads
- backup-techcorp
- ... (196 more)

**Auto-queued**: All 200 names

### **Step 2: Monitor Progress**
```bash
# Check queue
curl http://localhost:8000/api/v1/queue/size

# Check results
curl http://localhost:8000/api/v1/public-buckets

# View statistics
curl http://localhost:8000/api/v1/statistics
```

### **Results**:
- **Scanned**: 200 buckets
- **Found**: 12 buckets exist
- **Public**: 3 buckets publicly accessible
- **High Risk**: 1 bucket with sensitive files

---

## 🎯 Best Practices

### **1. Start with Pattern-Based**
```json
{
  "use_wordlist": false,
  "max_names": 50
}
```
Quick test of common patterns before full enumeration.

### **2. Use Wordlists for Thorough Scans**
```json
{
  "use_wordlist": true,
  "wordlist_names": ["common", "aws-specific"],
  "max_names": 200
}
```
Comprehensive coverage with curated lists.

### **3. Enable Auto-Scan for Large Operations**
```json
{
  "auto_scan": true
}
```
Automatically queue all generated names for worker processing.

### **4. Test Common Patterns First**
```bash
POST /enumerate/common-patterns?auto_scan=true
```
Quick wins - find commonly misconfigured buckets.

---

## 📈 Performance

- **Generation Speed**: ~10,000 names/second
- **Pattern Combinations**: Up to 500 per company
- **Wordlist Combinations**: Up to 1000+ combinations
- **Memory Efficient**: Streaming generation
- **Scalable**: Worker pool processes queue in parallel

---

## 🔐 Security Considerations

### **Rate Limiting**
- Enumeration generates names quickly
- Actual scanning respects rate limits
- Workers process queue with delays

### **Legal Compliance**
- Only scans buckets you have permission to test
- Follow responsible disclosure practices
- Document findings appropriately

### **Data Privacy**
- Enumeration generates names, doesn't access data
- Actual content analysis requires explicit scanning
- Respect data privacy regulations

---

## 🛠️ Development

### **Add Custom Patterns**

Edit `src/enumeration/name_generator.py`:
```python
COMMON_PREFIXES = [
    "backup", "data", "files",
    # Add your patterns here
    "custom-pattern-1",
    "custom-pattern-2"
]
```

### **Create Industry-Specific Wordlists**

Create `wordlists/healthcare.txt`:
```
patient-data
medical-records
hipaa-compliance
phi-backup
```

Use in enumeration:
```json
{
  "wordlist_names": ["common", "healthcare"]
}
```

---

## 📝 Summary

The **Enumeration Module** completes the bucket scanner architecture by providing:

✅ **Intelligent name generation** - Pattern-based + wordlist  
✅ **Multi-cloud support** - AWS, GCP, Azure  
✅ **Auto-queue integration** - Seamless workflow  
✅ **Customizable wordlists** - Industry-specific patterns  
✅ **API-driven** - Easy integration  
✅ **Scalable** - Worker pool processing  

**Now your POC can:**
1. ✅ **Enumerate** bucket names (Pattern + Wordlist)
2. ✅ **Discover** buckets (DNS + HTTP probes)
3. ✅ **Check** permissions (Anonymous access)
4. ✅ **Analyze** content (File enumeration)
5. ✅ **Store** results (PostgreSQL)
6. ✅ **Queue** tasks (Redis + Workers)
7. ✅ **Monitor** progress (Statistics + API)

**Your architecture is now complete!** 🎉
