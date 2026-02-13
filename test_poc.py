#!/usr/bin/env python3
"""
Standalone test script to validate bucket scanner components.
Tests core functionality without requiring Docker or cloud credentials.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_scanner_imports():
    """Test that all scanner modules can be imported."""
    print("🧪 Testing scanner imports...")
    try:
        from src.scanner import (
            BaseScanner, 
            AWSS3Scanner, 
            GCPStorageScanner, 
            AzureBlobScanner,
            ScanOrchestrator,
            BucketAccessLevel,
            CloudProvider
        )
        print("  ✅ Scanner imports successful")
        return True
    except Exception as e:
        print(f"  ❌ Scanner import failed: {e}")
        return False


async def test_worker_imports():
    """Test that all worker modules can be imported."""
    print("🧪 Testing worker imports...")
    try:
        from src.workers import (
            DNSResolver,
            HTTPProbe,
            PermissionChecker,
            ContentAnalyzer
        )
        print("  ✅ Worker imports successful")
        return True
    except Exception as e:
        print(f"  ❌ Worker import failed: {e}")
        return False


async def test_queue_imports():
    """Test queue system imports."""
    print("🧪 Testing queue imports...")
    try:
        from src.queue import QueueProducer, QueueConsumer
        print("  ✅ Queue imports successful")
        return True
    except Exception as e:
        print(f"  ❌ Queue import failed: {e}")
        return False


async def test_database_imports():
    """Test database imports."""
    print("🧪 Testing database imports...")
    try:
        from src.database import (
            Base,
            ScanResult,
            ScanTask,
            Finding,
            DatabaseRepository
        )
        print("  ✅ Database imports successful")
        return True
    except Exception as e:
        print(f"  ❌ Database import failed: {e}")
        return False


async def test_utils_imports():
    """Test utility imports."""
    print("🧪 Testing utils imports...")
    try:
        from src.utils import (
            RateLimiter,
            AdaptiveRateLimiter,
            IPRotator,
            Notifier
        )
        print("  ✅ Utils imports successful")
        return True
    except Exception as e:
        print(f"  ❌ Utils import failed: {e}")
        return False


async def test_api_imports():
    """Test API imports."""
    print("🧪 Testing API imports...")
    try:
        from src.api import app
        print("  ✅ API imports successful")
        return True
    except Exception as e:
        print(f"  ❌ API import failed: {e}")
        return False


async def test_enumeration_imports():
    """Test enumeration module imports."""
    print("🧪 Testing enumeration imports...")
    try:
        from src.enumeration import (
            BucketNameGenerator,
            WordlistManager
        )
        print("  ✅ Enumeration imports successful")
        return True
    except Exception as e:
        print(f"  ❌ Enumeration import failed: {e}")
        return False


async def test_name_generator():
    """Test bucket name generator functionality."""
    print("🧪 Testing bucket name generator...")
    try:
        from src.enumeration import BucketNameGenerator
        
        generator = BucketNameGenerator()
        
        # Test pattern-based generation
        pattern_names = generator.generate_for_company("TestCorp", max_names=10)
        assert len(pattern_names) >= 5, "Should generate at least 5 pattern-based names"
        
        # Test common patterns
        common_names = generator.generate_common_public_buckets(limit=10)
        assert len(common_names) >= 10, "Should generate at least 10 common patterns"
        
        print(f"  ✅ Name generator working (pattern: {len(pattern_names)}, common: {len(common_names)})")
        return True
    except Exception as e:
        print(f"  ❌ Name generator test failed: {e}")
        return False


async def test_wordlist_manager():
    """Test wordlist manager functionality."""
    print("🧪 Testing wordlist manager...")
    try:
        from src.enumeration import WordlistManager
        
        manager = WordlistManager()
        
        # Test wordlist loading
        available = manager.get_available_wordlists()
        
        # Test common patterns (should always be available)
        common_patterns = manager.get_common_patterns()
        assert len(common_patterns) > 0, "Should have common patterns available"
        
        print(f"  ✅ Wordlist manager working (wordlists: {len(available)}, patterns: {len(common_patterns)})")
        return True
    except Exception as e:
        print(f"  ❌ Wordlist manager test failed: {e}")
        return False


async def test_scanner_initialization():
    """Test scanner initialization without credentials."""
    print("🧪 Testing scanner initialization...")
    try:
        from src.scanner import AWSS3Scanner, GCPStorageScanner, AzureBlobScanner
        
        # Test AWS scanner (anonymous mode)
        aws_scanner = AWSS3Scanner()
        assert aws_scanner is not None
        assert aws_scanner._get_bucket_url("test") == "https://test.s3.amazonaws.com"
        
        # Test GCP scanner
        gcp_scanner = GCPStorageScanner()
        assert gcp_scanner is not None
        assert gcp_scanner._get_bucket_url("test") == "https://storage.googleapis.com/test"
        
        # Test Azure scanner
        azure_scanner = AzureBlobScanner(account_name="testaccount")
        assert azure_scanner is not None
        assert azure_scanner._get_bucket_url("test") == "https://testaccount.blob.core.windows.net/test"
        
        print("  ✅ Scanner initialization successful")
        return True
    except Exception as e:
        print(f"  ❌ Scanner initialization failed: {e}")
        return False


async def test_rate_limiter():
    """Test rate limiter functionality."""
    print("🧪 Testing rate limiter...")
    try:
        from src.utils import RateLimiter
        
        limiter = RateLimiter(max_requests=5, time_window=1.0)
        
        # Test acquire
        result = await limiter.acquire(timeout=1.0)
        assert result == True
        
        print("  ✅ Rate limiter working")
        return True
    except Exception as e:
        print(f"  ❌ Rate limiter test failed: {e}")
        return False


async def test_content_analyzer():
    """Test content analyzer functionality."""
    print("🧪 Testing content analyzer...")
    try:
        from src.workers import ContentAnalyzer
        
        analyzer = ContentAnalyzer()
        
        # Test with sample files
        test_files = [
            "config.json",
            ".env",
            "passwords.txt",
            "id_rsa",
            "normal_file.txt",
            "backup.sql"
        ]
        
        result = analyzer.analyze("test-bucket", test_files)
        
        assert result.total_files == 6
        assert len(result.sensitive_files) > 0
        assert result.risk_score > 0
        
        print(f"  ✅ Content analyzer working (found {len(result.sensitive_files)} sensitive files)")
        return True
    except Exception as e:
        print(f"  ❌ Content analyzer test failed: {e}")
        return False


async def test_permission_checker():
    """Test permission checker functionality."""
    print("🧪 Testing permission checker...")
    try:
        from src.workers import PermissionChecker
        
        checker = PermissionChecker()
        
        # Test permission analysis
        result = checker.analyze_permissions(
            bucket_name="test-bucket",
            provider="aws_s3",
            permissions=["list", "read"],
            is_public=True,
            files_found=[".env", "config.json"]
        )
        
        assert result.is_public == True
        assert result.risk_level in ["low", "medium", "high", "critical"]
        assert len(result.recommendations) > 0
        
        print(f"  ✅ Permission checker working (risk: {result.risk_level})")
        return True
    except Exception as e:
        print(f"  ❌ Permission checker test failed: {e}")
        return False


async def test_orchestrator():
    """Test scan orchestrator initialization."""
    print("🧪 Testing scan orchestrator...")
    try:
        from src.scanner import ScanOrchestrator
        
        orchestrator = ScanOrchestrator()
        assert len(orchestrator.scanners) == 3  # AWS, GCP, Azure
        
        print(f"  ✅ Orchestrator initialized with {len(orchestrator.scanners)} providers")
        return True
    except Exception as e:
        print(f"  ❌ Orchestrator test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("🚀 Bucket Scanner POC - Component Tests")
    print("=" * 60)
    print()
    
    results = []
    
    # Run all tests
    results.append(await test_scanner_imports())
    results.append(await test_worker_imports())
    results.append(await test_queue_imports())
    results.append(await test_database_imports())
    results.append(await test_utils_imports())
    results.append(await test_api_imports())
    results.append(await test_enumeration_imports())
    results.append(await test_scanner_initialization())
    results.append(await test_rate_limiter())
    results.append(await test_content_analyzer())
    results.append(await test_permission_checker())
    results.append(await test_orchestrator())
    results.append(await test_name_generator())
    results.append(await test_wordlist_manager())
    
    print()
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ All {total} tests PASSED!")
        print("=" * 60)
        return 0
    else:
        failed = total - passed
        print(f"❌ {failed}/{total} tests FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
