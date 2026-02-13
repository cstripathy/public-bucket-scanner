#!/bin/bash
# Final Verification Script for Interview Submission
# Comprehensive check of all project components

# Note: Not using 'set -e' as we handle errors explicitly

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     BUCKET SCANNER - INTERVIEW SUBMISSION CHECK        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}\n"

ERRORS=0
WARNINGS=0

# Check 1: Project Files
echo -e "${YELLOW}[1/10] Checking Project Files...${NC}"
required_files=(
    "README.md"
    "LICENSE"
    "CONTRIBUTING.md"
    "INTERVIEW.md"
    "QUICKSTART.md"
    "docker-compose.yml"
    "Dockerfile"
    "requirements.txt"
    ".env.example"
    ".gitignore"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ${GREEN}✓${NC} $file"
    else
        echo -e "  ${RED}✗${NC} $file (MISSING)"
        ((ERRORS++))
    fi
done

# Check 2: Documentation
echo -e "\n${YELLOW}[2/10] Checking Documentation...${NC}"
docs=(
    "docs/API.md"
    "docs/DEPLOYMENT.md"
    "docs/DEVELOPMENT.md"
    "docs/ENUMERATION.md"
)

for doc in "${docs[@]}"; do
    if [ -f "$doc" ]; then
        lines=$(wc -l < "$doc")
        echo -e "  ${GREEN}✓${NC} $doc ($lines lines)"
    else
        echo -e "  ${RED}✗${NC} $doc (MISSING)"
        ((WARNINGS++))
    fi
done

# Check 3: Source Code
echo -e "\n${YELLOW}[3/10] Checking Source Code Structure...${NC}"
src_dirs=(
    "src/scanner"
    "src/workers"
    "src/enumeration"
    "src/queue"
    "src/api"
    "src/database"
    "src/utils"
    "src/config"
)

for dir in "${src_dirs[@]}"; do
    if [ -d "$dir" ]; then
        count=$(find "$dir" -name "*.py" | wc -l)
        echo -e "  ${GREEN}✓${NC} $dir ($count Python files)"
    else
        echo -e "  ${RED}✗${NC} $dir (MISSING)"
        ((ERRORS++))
    fi
done

# Check 4: Wordlists
echo -e "\n${YELLOW}[4/10] Checking Wordlists...${NC}"
if [ -d "wordlists" ]; then
    wordlist_count=$(find wordlists -name "*.txt" | wc -l)
    echo -e "  ${GREEN}✓${NC} wordlists/ directory ($wordlist_count wordlists)"
    for wordlist in wordlists/*.txt; do
        if [ -f "$wordlist" ]; then
            lines=$(wc -l < "$wordlist" 2>/dev/null || echo "0")
            echo -e "    • $(basename $wordlist): $lines patterns"
        fi
    done
else
    echo -e "  ${RED}✗${NC} wordlists/ directory (MISSING)"
    ((ERRORS++))
fi

# Check 5: Test Scripts
echo -e "\n${YELLOW}[5/10] Checking Test Scripts...${NC}"
test_scripts=(
    "test_poc.py"
    "test_workflow.sh"
    "test_enumeration.sh"
)

for script in "${test_scripts[@]}"; do
    if [ -f "$script" ]; then
        if [ -x "$script" ] || [[ "$script" == *.py ]]; then
            echo -e "  ${GREEN}✓${NC} $script (executable)"
        else
            echo -e "  ${YELLOW}⚠${NC} $script (not executable)"
            ((WARNINGS++))
        fi
    else
        echo -e "  ${RED}✗${NC} $script (MISSING)"
        ((ERRORS++))
    fi
done

# Check 6: Docker Configuration
echo -e "\n${YELLOW}[6/10] Checking Docker Configuration...${NC}"
if docker compose config > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} docker-compose.yml is valid"
    services=$(docker compose config --services | wc -l)
    echo -e "  ${GREEN}✓${NC} Configured services: $services"
else
    echo -e "  ${RED}✗${NC} docker-compose.yml has errors"
    ((ERRORS++))
fi

# Check 7: Running Services
echo -e "\n${YELLOW}[7/10] Checking Running Services...${NC}"
if docker compose ps | grep -q "Up"; then
    running=$(docker compose ps --filter "status=running" | grep -c "Up" || echo "0")
    echo -e "  ${GREEN}✓${NC} Services running: $running"
    
    # Check health
    if curl -s http://localhost:8000/health | grep -q "healthy"; then
        echo -e "  ${GREEN}✓${NC} API health check: PASS"
    else
        echo -e "  ${YELLOW}⚠${NC} API health check: Services might be starting"
        ((WARNINGS++))
    fi
else
    echo -e "  ${YELLOW}⚠${NC} No services running (expected if not started)"
    echo -e "    Run: docker compose up -d --build"
fi

# Check 8: Database Schema
echo -e "\n${YELLOW}[8/10] Checking Database Schema...${NC}"
if [ -f "init-db.sql" ]; then
    tables=$(grep -c "CREATE TABLE" init-db.sql || echo "0")
    indexes=$(grep -c "CREATE INDEX" init-db.sql || echo "0")
    echo -e "  ${GREEN}✓${NC} init-db.sql exists"
    echo -e "    • Tables: $tables"
    echo -e "    • Indexes: $indexes"
else
    echo -e "  ${RED}✗${NC} init-db.sql (MISSING)"
    ((ERRORS++))
fi

# Check 9: No Sensitive Data
echo -e "\n${YELLOW}[9/10] Checking for Sensitive Data...${NC}"
# Look for hardcoded credentials (actual values, not variable assignments)
found_sensitive=0

# Check for potential hardcoded passwords (not empty strings or placeholders)
if grep -rI "password[[:space:]]*=[[:space:]]*['\"].*[^'\"[:space:]]" --include="*.py" src/ 2>/dev/null | grep -v "change_me" | grep -v '""' | grep -v "Set via" | grep -q .; then
    echo -e "  ${RED}✗${NC} Found potential hardcoded passwords"
    ((ERRORS++))
    found_sensitive=1
fi

# Check for AWS keys
if grep -rI "AKIA[0-9A-Z]{16}" --include="*.py" --include="*.yml" src/ 2>/dev/null | grep -q .; then
    echo -e "  ${RED}✗${NC} Found potential AWS access keys"
    ((ERRORS++))
    found_sensitive=1
fi

if [ $found_sensitive -eq 0 ]; then
    echo -e "  ${GREEN}✓${NC} No hardcoded credentials found"
fi

# Check 10: Git Repository
echo -e "\n${YELLOW}[10/10] Checking Git Configuration...${NC}"
if [ -d ".git" ]; then
    echo -e "  ${GREEN}✓${NC} Git repository initialized"
    
    # Check for untracked important files
    if git status --short 2>/dev/null | grep -q "??"; then
        echo -e "  ${YELLOW}⚠${NC} Untracked files exist (may want to commit)"
        ((WARNINGS++))
    else
        echo -e "  ${GREEN}✓${NC} All important files tracked"
    fi
else
    echo -e "  ${YELLOW}⚠${NC} Not a git repository"
    echo -e "    Recommendation: git init && git add .  && git commit -m 'Initial commit'"
    ((WARNINGS++))
fi

# Summary
echo -e "\n${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    SUMMARY                              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}\n"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ ALL CHECKS PASSED!${NC}"
    echo -e "${GREEN}✓ Project is ready for interview submission${NC}\n"
    exit_code=0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ ${WARNINGS} WARNING(S) - Project is mostly ready${NC}\n"
    exit_code=0
else
    echo -e "${RED}✗ ${ERRORS} ERROR(S) and ${WARNINGS} WARNING(S)${NC}"
    echo -e "${RED}✗ Please fix errors before submission${NC}\n"
    exit_code=1
fi

# Additional Information
echo -e "${BLUE}Additional Information:${NC}"
echo -e "  • Total Python files: $(find src -name '*.py' | wc -l)"
echo -e "  • Total lines of code: $(find src -name '*.py' -exec wc -l {} + 2>/dev/null | tail -1 | awk '{print $1}')"
echo -e "  • Documentation files: $(find docs -name '*.md' | wc -l)"
echo -e "  • Test scripts: $(ls test_*.{py,sh} 2>/dev/null | wc -l)"
echo -e "  • Wordlists: $(find wordlists -name '*.txt' 2>/dev/null | wc -l)"

echo -e "\n${BLUE}Quick Start Commands:${NC}"
echo -e "  ${GREEN}•${NC} Start system:    ${YELLOW}docker compose up -d --build${NC}"
echo -e "  ${GREEN}•${NC} Run tests:       ${YELLOW}./test_workflow.sh${NC}"
echo -e "  ${GREEN}•${NC} Check health:    ${YELLOW}curl http://localhost:8000/health${NC}"
echo -e "  ${GREEN}•${NC} View API docs:   ${YELLOW}open http://localhost:8000/docs${NC}"
echo -e "  ${GREEN}•${NC} Stop system:     ${YELLOW}docker compose down${NC}"

echo -e "\n${BLUE}Interview Documents:${NC}"
echo -e "  ${GREEN}•${NC} Main README:     ${YELLOW}README.md${NC}"
echo -e "  ${GREEN}•${NC} Interview Guide: ${YELLOW}INTERVIEW.md${NC}"
echo -e "  ${GREEN}•${NC} Quick Start:     ${YELLOW}QUICKSTART.md${NC}"
echo -e "  ${GREEN}•${NC} API Docs:        ${YELLOW}docs/API.md${NC}"

echo ""
exit $exit_code
