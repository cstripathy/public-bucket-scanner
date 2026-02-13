"""Azure Blob Storage scanner implementation."""
from azure.storage.blob import BlobServiceClient, ContainerClient, PublicAccess
from azure.core.exceptions import ResourceNotFoundError, HttpResponseError
from typing import List
import httpx
from .base_scanner import BaseScanner, CloudProvider, BucketAccessLevel
import structlog

logger = structlog.get_logger()


class AzureBlobScanner(BaseScanner):
    """Scanner for Azure Blob Storage containers."""
    
    def __init__(self, account_name: str = "", account_key: str = "", connection_string: str = ""):
        """Initialize Azure Blob Storage scanner.
        
        Args:
            account_name: Azure storage account name
            account_key: Azure storage account key (optional for anonymous access)
            connection_string: Azure connection string (alternative to name/key)
        """
        super().__init__(CloudProvider.AZURE_BLOB)
        self.account_name = account_name
        
        # Create blob service client
        try:
            if connection_string:
                self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
                # Extract account name from connection string
                for part in connection_string.split(';'):
                    if 'AccountName=' in part:
                        self.account_name = part.split('=')[1]
            elif account_name and account_key:
                account_url = f"https://{account_name}.blob.core.windows.net"
                self.blob_service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=account_key
                )
            else:
                # Anonymous client (for public container detection)
                self.blob_service_client = None
        except Exception as e:
            logger.warning("azure_client_init_failed", error=str(e))
            self.blob_service_client = None
    
    async def check_bucket_exists(self, bucket_name: str) -> bool:
        """Check if Azure container exists.
        
        Note: In Azure, buckets are called 'containers'
        
        Args:
            bucket_name: Name of the container
            
        Returns:
            True if container exists
        """
        try:
            # Try HTTP HEAD request first
            url = f"https://{self.account_name}.blob.core.windows.net/{bucket_name}?restype=container"
            async with httpx.AsyncClient() as client:
                response = await client.head(url, timeout=5.0)
                # 200 = exists and accessible, 404 = doesn't exist
                return response.status_code in [200, 403, 409]
        except Exception:
            # Fallback to Azure client
            if self.blob_service_client:
                try:
                    container_client = self.blob_service_client.get_container_client(bucket_name)
                    container_client.get_container_properties()
                    return True
                except ResourceNotFoundError:
                    return False
                except HttpResponseError:
                    # Container exists but no access
                    return True
                except Exception:
                    return False
            return False
    
    async def check_public_access(self, bucket_name: str) -> BucketAccessLevel:
        """Check Azure container public access configuration.
        
        Azure public access levels:
        - Private: No public access
        - Blob: Public read access for blobs only
        - Container: Public read access for container and blobs
        
        Args:
            bucket_name: Name of the container
            
        Returns:
            Access level of the container
        """
        try:
            # Method 1: Try anonymous LIST operation
            url = f"https://{self.account_name}.blob.core.windows.net/{bucket_name}?restype=container&comp=list"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                
                if response.status_code == 200:
                    # Can list container anonymously = public read
                    return BucketAccessLevel.PUBLIC_READ
            
            # Method 2: Check container properties
            if self.blob_service_client:
                try:
                    container_client = self.blob_service_client.get_container_client(bucket_name)
                    properties = container_client.get_container_properties()
                    
                    public_access = properties.get('public_access')
                    
                    if public_access == PublicAccess.Container:
                        # Full public read access to container and blobs
                        return BucketAccessLevel.PUBLIC_READ
                    elif public_access == PublicAccess.Blob:
                        # Public read access to blobs only (not container listing)
                        return BucketAccessLevel.PUBLIC_READ
                    elif public_access is None or public_access == 'off':
                        return BucketAccessLevel.PRIVATE
                        
                except Exception as e:
                    self.logger.debug("properties_check_failed", container=bucket_name, error=str(e))
            
            # Method 3: Try anonymous blob listing using Azure SDK
            try:
                account_url = f"https://{self.account_name}.blob.core.windows.net"
                anonymous_client = BlobServiceClient(account_url=account_url)
                container_client = anonymous_client.get_container_client(bucket_name)
                
                # Try to list blobs
                blobs = list(container_client.list_blobs(max_results=1))
                if blobs:
                    return BucketAccessLevel.PUBLIC_READ
                    
            except Exception:
                pass
            
            return BucketAccessLevel.PRIVATE
            
        except Exception as e:
            self.logger.error("public_access_check_failed", container=bucket_name, error=str(e))
            return BucketAccessLevel.UNKNOWN
    
    async def list_files(self, bucket_name: str, max_files: int = 100) -> List[str]:
        """List files in Azure container.
        
        Args:
            bucket_name: Name of the container
            max_files: Maximum number of files to list
            
        Returns:
            List of blob names
        """
        files = []
        try:
            if self.blob_service_client:
                container_client = self.blob_service_client.get_container_client(bucket_name)
            else:
                # Try anonymous access
                account_url = f"https://{self.account_name}.blob.core.windows.net"
                anonymous_client = BlobServiceClient(account_url=account_url)
                container_client = anonymous_client.get_container_client(bucket_name)
            
            for blob in container_client.list_blobs():
                files.append(blob.name)
                if len(files) >= max_files:
                    break
                    
        except Exception as e:
            self.logger.error("list_files_failed", container=bucket_name, error=str(e))
        
        return files
    
    async def get_bucket_permissions(self, bucket_name: str) -> List[str]:
        """Get detailed permissions for Azure container.
        
        Args:
            bucket_name: Name of the container
            
        Returns:
            List of permission strings
        """
        permissions = []
        
        if not self.blob_service_client:
            return permissions
        
        # Try various Azure operations
        try:
            container_client = self.blob_service_client.get_container_client(bucket_name)
            
            # Test list
            try:
                list(container_client.list_blobs(max_results=1))
                permissions.append('list')
            except Exception:
                pass
            
            # Test get properties
            try:
                container_client.get_container_properties()
                permissions.append('get_properties')
            except Exception:
                pass
            
            # Test get ACL
            try:
                container_client.get_container_access_policy()
                permissions.append('get_acl')
            except Exception:
                pass
                
        except Exception as e:
            self.logger.error("permission_check_failed", container=bucket_name, error=str(e))
        
        return permissions
    
    def _get_bucket_url(self, bucket_name: str) -> str:
        """Get Azure container URL.
        
        Args:
            bucket_name: Name of the container
            
        Returns:
            Full URL to the container
        """
        return f"https://{self.account_name}.blob.core.windows.net/{bucket_name}"
