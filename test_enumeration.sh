#!/bin/bash
# Test bucket name enumeration functionality

set -e

API_URL="http://localhost:8000/api/v1"
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Bucket Name Enumeration Demo${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Test 1: List available wordlists
echo -e "${YELLOW}[TEST 1] List Available Wordlists${NC}"
curl -s $API_URL/enumerate/wordlists | python3 -m json.tool
echo -e "${GREEN}✓ Wordlists retrieved${NC}\n"

# Test 2: Enumerate for a company (pattern-based)
echo -e "${YELLOW}[TEST 2] Enumerate - Pattern-Based Generation${NC}"
echo "Generating bucket names for: Acme Corp"
curl -s -X POST $API_URL/enumerate \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Acme Corp",
    "providers": ["aws_s3", "gcp_gcs"],
    "max_names": 50,
    "use_wordlist": false,
    "auto_scan": false
  }' | python3 -m json.tool | head -80
echo -e "${GREEN}✓ Pattern-based enumeration completed${NC}\n"

# Test 3: Enumerate with wordlist
echo -e "${YELLOW}[TEST 3] Enumerate - Wordlist-Based Generation${NC}"
echo "Using common.txt wordlist"
curl -s -X POST $API_URL/enumerate \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "TechStartup",
    "providers": ["aws_s3"],
    "max_names": 30,
    "use_wordlist": true,
    "wordlist_names": ["common"],
    "auto_scan": false
  }' | python3 -m json.tool | head -80
echo -e "${GREEN}✓ Wordlist-based enumeration completed${NC}\n"

# Test 4: Common patterns
echo -e "${YELLOW}[TEST 4] Generate Common Public Bucket Patterns${NC}"
curl -s -X POST "$API_URL/enumerate/common-patterns?auto_scan=false" \
  -H "Content-Type: application/json" | python3 -m json.tool | head -50
echo -e "${GREEN}✓ Common patterns generated${NC}\n"

# Test 5: Enumerate and auto-queue for scanning
echo -e "${YELLOW}[TEST 5] Enumerate + Auto-Queue for Scanning${NC}"
echo "Generating names for MyCorp and queuing for scanning..."
response=$(curl -s -X POST $API_URL/enumerate \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "MyCorp",
    "providers": ["aws_s3"],
    "max_names": 20,
    "use_wordlist": false,
    "auto_scan": true
  }')
echo "$response" | python3 -m json.tool
echo -e "${GREEN}✓ Names generated and queued${NC}\n"

# Check queue size
echo -e "${YELLOW}[TEST 6] Check Queue Size After Enumeration${NC}"
curl -s $API_URL/queue/size | python3 -m json.tool
echo -e "${GREEN}✓ Queue size retrieved${NC}\n"

# Show statistics
echo -e "${YELLOW}[TEST 7] Current Statistics${NC}"
curl -s $API_URL/statistics | python3 -m json.tool
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Enumeration Demo Complete${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}✅ Enumeration Features:${NC}"
echo "  ✓ Pattern-based generation (company-backup, etc.)"
echo "  ✓ Wordlist-based combinations"
echo "  ✓ Common public bucket patterns"
echo "  ✓ Auto-queue for scanning"
echo "  ✓ Multi-provider support"
echo ""
echo -e "${YELLOW}📝 Key Endpoints:${NC}"
echo "  POST /api/v1/enumerate - Generate bucket names"
echo "  GET  /api/v1/enumerate/wordlists - List wordlists"
echo "  POST /api/v1/enumerate/common-patterns - Common patterns"
echo ""
echo -e "${YELLOW}💡 Example Usage:${NC}"
echo '  curl -X POST http://localhost:8000/api/v1/enumerate \'
echo '    -H "Content-Type: application/json" \'
echo '    -d '"'"'{"company_name": "YourCompany", "auto_scan": true}'"'"
