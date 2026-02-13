"""Base scanner interface for all cloud storage providers."""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import structlog

logger = structlog.get_logger()


class BucketAccessLevel(Enum):
    """Bucket access level enumeration."""
    PRIVATE = "private"
    PUBLIC_READ = "public-read"
    PUBLIC_WRITE = "public-write"
    PUBLIC_READ_WRITE = "public-read-write"
    AUTHENTICATED_READ = "authenticated-read"
    UNKNOWN = "unknown"


class CloudProvider(Enum):
    """Supported cloud providers."""
    AWS_S3 = "aws_s3"
    GCP_GCS = "gcp_gcs"
    AZURE_BLOB = "azure_blob"


@dataclass
class BucketScanResult:
    """Result from scanning a bucket."""
    provider: CloudProvider
    bucket_name: str
    exists: bool
    is_accessible: bool
    access_level: BucketAccessLevel
    permissions: List[str]
    url: str
    files_found: Optional[List[str]] = None
    sensitive_files: Optional[List[str]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseScanner(ABC):
    """Base class for cloud storage scanners."""
    
    def __init__(self, provider: CloudProvider):
        """Initialize the scanner.
        
        Args:
            provider: The cloud provider type
        """
        self.provider = provider
        self.logger = logger.bind(provider=provider.value)
    
    @abstractmethod
    async def check_bucket_exists(self, bucket_name: str) -> bool:
        """Check if a bucket exists.
        
        Args:
            bucket_name: Name of the bucket to check
            
        Returns:
            True if bucket exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def check_public_access(self, bucket_name: str) -> BucketAccessLevel:
        """Check if bucket has public access.
        
        Args:
            bucket_name: Name of the bucket to check
            
        Returns:
            Access level of the bucket
        """
        pass
    
    @abstractmethod
    async def list_files(self, bucket_name: str, max_files: int = 100) -> List[str]:
        """List files in a bucket if accessible.
        
        Args:
            bucket_name: Name of the bucket
            max_files: Maximum number of files to list
            
        Returns:
            List of file paths
        """
        pass
    
    @abstractmethod
    async def get_bucket_permissions(self, bucket_name: str) -> List[str]:
        """Get detailed permissions for a bucket.
        
        Args:
            bucket_name: Name of the bucket
            
        Returns:
            List of permissions
        """
        pass
    
    async def scan_bucket(self, bucket_name: str) -> BucketScanResult:
        """Perform a complete scan of a bucket.
        
        Args:
            bucket_name: Name of the bucket to scan
            
        Returns:
            Complete scan results
        """
        self.logger.info("scanning_bucket", bucket=bucket_name)
        
        try:
            # Check existence
            exists = await self.check_bucket_exists(bucket_name)
            if not exists:
                return BucketScanResult(
                    provider=self.provider,
                    bucket_name=bucket_name,
                    exists=False,
                    is_accessible=False,
                    access_level=BucketAccessLevel.UNKNOWN,
                    permissions=[],
                    url=self._get_bucket_url(bucket_name),
                    error="Bucket does not exist"
                )
            
            # Check access level
            access_level = await self.check_public_access(bucket_name)
            is_accessible = access_level not in [BucketAccessLevel.PRIVATE, BucketAccessLevel.UNKNOWN]
            
            # Get permissions
            permissions = await self.get_bucket_permissions(bucket_name)
            
            # List files if accessible
            files_found = None
            sensitive_files = None
            if is_accessible:
                files_found = await self.list_files(bucket_name)
                sensitive_files = self._detect_sensitive_files(files_found)
            
            result = BucketScanResult(
                provider=self.provider,
                bucket_name=bucket_name,
                exists=True,
                is_accessible=is_accessible,
                access_level=access_level,
                permissions=permissions,
                url=self._get_bucket_url(bucket_name),
                files_found=files_found,
                sensitive_files=sensitive_files
            )
            
            self.logger.info(
                "scan_complete",
                bucket=bucket_name,
                accessible=is_accessible,
                access_level=access_level.value
            )
            
            return result
            
        except Exception as e:
            self.logger.error("scan_error", bucket=bucket_name, error=str(e))
            return BucketScanResult(
                provider=self.provider,
                bucket_name=bucket_name,
                exists=False,
                is_accessible=False,
                access_level=BucketAccessLevel.UNKNOWN,
                permissions=[],
                url=self._get_bucket_url(bucket_name),
                error=str(e)
            )
    
    @abstractmethod
    def _get_bucket_url(self, bucket_name: str) -> str:
        """Get the URL for accessing a bucket.
        
        Args:
            bucket_name: Name of the bucket
            
        Returns:
            Full URL to the bucket
        """
        pass
    
    def _detect_sensitive_files(self, files: List[str]) -> List[str]:
        """Detect potentially sensitive files.
        
        Args:
            files: List of file paths
            
        Returns:
            List of sensitive file paths
        """
        sensitive_patterns = [
            '.env', 'config', 'secret', 'password', 'credential',
            'token', 'key', 'private', '.pem', '.key', '.ppk',
            'backup', '.sql', '.db', 'database', 'admin',
            'wp-config', '.git', '.aws', 'id_rsa'
        ]
        
        sensitive = []
        for file in files:
            file_lower = file.lower()
            if any(pattern in file_lower for pattern in sensitive_patterns):
                sensitive.append(file)
        
        return sensitive
