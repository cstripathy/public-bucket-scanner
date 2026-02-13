"""GCP Cloud Storage scanner implementation."""
from google.cloud import storage
from google.cloud.exceptions import NotFound, Forbidden
from typing import List
import httpx
from .base_scanner import BaseScanner, CloudProvider, BucketAccessLevel
import structlog

logger = structlog.get_logger()


class GCPStorageScanner(BaseScanner):
    """Scanner for GCP Cloud Storage buckets."""
    
    def __init__(self, project_id: str = "", credentials_path: str = ""):
        """Initialize GCP Cloud Storage scanner.
        
        Args:
            project_id: GCP project ID (optional for anonymous access)
            credentials_path: Path to service account credentials (optional)
        """
        super().__init__(CloudProvider.GCP_GCS)
        self.project_id = project_id
        
        # Create storage client
        try:
            if credentials_path:
                self.storage_client = storage.Client.from_service_account_json(
                    credentials_path,
                    project=project_id
                )
            else:
                # Anonymous client for public bucket detection
                self.storage_client = storage.Client.create_anonymous_client()
        except Exception as e:
            logger.warning("gcp_client_init_failed", error=str(e))
            self.storage_client = storage.Client.create_anonymous_client()
    
    async def check_bucket_exists(self, bucket_name: str) -> bool:
        """Check if GCS bucket exists.
        
        Args:
            bucket_name: Name of the GCS bucket
            
        Returns:
            True if bucket exists
        """
        try:
            # Try HTTP HEAD request first
            url = f"https://storage.googleapis.com/{bucket_name}"
            async with httpx.AsyncClient() as client:
                response = await client.head(url, timeout=5.0)
                # 200, 403, or 404 in certain conditions
                return response.status_code in [200, 403]
        except Exception:
            # Fallback to GCS client
            try:
                bucket = self.storage_client.bucket(bucket_name)
                bucket.reload()
                return True
            except NotFound:
                return False
            except Forbidden:
                # Bucket exists but no access
                return True
            except Exception:
                return False
    
    async def check_public_access(self, bucket_name: str) -> BucketAccessLevel:
        """Check GCS bucket public access configuration.
        
        GCS public access patterns:
        1. Try anonymous GET/LIST operations
        2. Check IAM policy for allUsers or allAuthenticatedUsers
        3. Check bucket-level permissions
        
        Args:
            bucket_name: Name of the GCS bucket
            
        Returns:
            Access level of the bucket
        """
        try:
            # Method 1: Try anonymous LIST operation
            url = f"https://storage.googleapis.com/{bucket_name}"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                
                if response.status_code == 200:
                    # Can list bucket anonymously = public read
                    return BucketAccessLevel.PUBLIC_READ
            
            # Method 2: Check IAM policy
            try:
                bucket = self.storage_client.bucket(bucket_name)
                policy = bucket.get_iam_policy()
                
                for binding in policy.bindings:
                    members = binding.get('members', [])
                    role = binding.get('role', '')
                    
                    # Check for allUsers (public) or allAuthenticatedUsers
                    if 'allUsers' in members:
                        if 'storage.objects.list' in role or 'roles/storage.objectViewer' in role:
                            return BucketAccessLevel.PUBLIC_READ
                        elif 'storage.objects.create' in role or 'roles/storage.objectCreator' in role:
                            return BucketAccessLevel.PUBLIC_WRITE
                        elif 'roles/storage.admin' in role:
                            return BucketAccessLevel.PUBLIC_READ_WRITE
                    elif 'allAuthenticatedUsers' in members:
                        return BucketAccessLevel.AUTHENTICATED_READ
            except Exception as e:
                self.logger.debug("iam_policy_check_failed", bucket=bucket_name, error=str(e))
            
            # Method 3: Try to get a sample object with anonymous access
            try:
                bucket = self.storage_client.bucket(bucket_name)
                blobs = list(bucket.list_blobs(max_results=1))
                if blobs:
                    # If we can list, it's at least public read
                    return BucketAccessLevel.PUBLIC_READ
            except Exception:
                pass
            
            return BucketAccessLevel.PRIVATE
            
        except Exception as e:
            self.logger.error("public_access_check_failed", bucket=bucket_name, error=str(e))
            return BucketAccessLevel.UNKNOWN
    
    async def list_files(self, bucket_name: str, max_files: int = 100) -> List[str]:
        """List files in GCS bucket.
        
        Args:
            bucket_name: Name of the bucket
            max_files: Maximum number of files to list
            
        Returns:
            List of file names
        """
        files = []
        try:
            bucket = self.storage_client.bucket(bucket_name)
            blobs = bucket.list_blobs(max_results=max_files)
            
            for blob in blobs:
                files.append(blob.name)
                if len(files) >= max_files:
                    break
                    
        except Exception as e:
            self.logger.error("list_files_failed", bucket=bucket_name, error=str(e))
        
        return files
    
    async def get_bucket_permissions(self, bucket_name: str) -> List[str]:
        """Get detailed permissions for GCS bucket.
        
        Args:
            bucket_name: Name of the bucket
            
        Returns:
            List of permission strings
        """
        permissions = []
        
        # Try various GCS operations
        try:
            bucket = self.storage_client.bucket(bucket_name)
            
            # Test list
            try:
                list(bucket.list_blobs(max_results=1))
                permissions.append('list')
            except Exception:
                pass
            
            # Test get IAM policy
            try:
                bucket.get_iam_policy()
                permissions.append('get_iam_policy')
            except Exception:
                pass
            
            # Test get metadata
            try:
                bucket.reload()
                permissions.append('get_metadata')
            except Exception:
                pass
                
        except Exception as e:
            self.logger.error("permission_check_failed", bucket=bucket_name, error=str(e))
        
        return permissions
    
    def _get_bucket_url(self, bucket_name: str) -> str:
        """Get GCS bucket URL.
        
        Args:
            bucket_name: Name of the bucket
            
        Returns:
            Full URL to the bucket
        """
        return f"https://storage.googleapis.com/{bucket_name}"
