"""Tests for scanner module."""
import pytest
from src.scanner import AWSS3Scanner, GCPStorageScanner, AzureBlobScanner
from src.scanner.base_scanner import BucketAccessLevel


@pytest.mark.asyncio
async def test_aws_scanner_init():
    """Test AWS scanner initialization."""
    scanner = AWSS3Scanner()
    assert scanner is not None
    assert scanner.s3_client is not None


@pytest.mark.asyncio
async def test_gcp_scanner_init():
    """Test GCP scanner initialization."""
    scanner = GCPStorageScanner()
    assert scanner is not None


@pytest.mark.asyncio
async def test_azure_scanner_init():
    """Test Azure scanner initialization."""
    scanner = AzureBlobScanner(account_name="testaccount")
    assert scanner is not None
    assert scanner.account_name == "testaccount"


@pytest.mark.asyncio
async def test_bucket_url_generation():
    """Test bucket URL generation."""
    aws_scanner = AWSS3Scanner()
    gcp_scanner = GCPStorageScanner()
    azure_scanner = AzureBlobScanner(account_name="testaccount")
    
    assert aws_scanner._get_bucket_url("test") == "https://test.s3.amazonaws.com"
    assert gcp_scanner._get_bucket_url("test") == "https://storage.googleapis.com/test"
    assert azure_scanner._get_bucket_url("test") == "https://testaccount.blob.core.windows.net/test"
