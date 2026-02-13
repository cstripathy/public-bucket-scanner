"""AWS S3 bucket scanner implementation."""
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import List
import httpx
from .base_scanner import BaseScanner, CloudProvider, BucketAccessLevel
import structlog

logger = structlog.get_logger()


class AWSS3Scanner(BaseScanner):
    """Scanner for AWS S3 buckets."""
    
    def __init__(self, access_key: str = "", secret_key: str = "", region: str = "us-east-1"):
        """Initialize AWS S3 scanner.
        
        Args:
            access_key: AWS access key (optional for anonymous access)
            secret_key: AWS secret key (optional for anonymous access)
            region: AWS region
        """
        super().__init__(CloudProvider.AWS_S3)
        self.region = region
        self.access_key = access_key
        self.secret_key = secret_key
        
        # Create S3 client (can be anonymous)
        if access_key and secret_key:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region
            )
        else:
            # Anonymous client for public bucket detection
            from botocore import UNSIGNED
            from botocore.config import Config
            self.s3_client = boto3.client('s3', config=Config(signature_version=UNSIGNED))
    
    async def check_bucket_exists(self, bucket_name: str) -> bool:
        """Check if S3 bucket exists using HEAD request.
        
        Args:
            bucket_name: Name of the S3 bucket
            
        Returns:
            True if bucket exists
        """
        try:
            # Try HTTP HEAD request first (faster)
            url = f"https://{bucket_name}.s3.amazonaws.com"
            async with httpx.AsyncClient() as client:
                response = await client.head(url, timeout=5.0)
                # 200, 403, or 301 means bucket exists
                return response.status_code in [200, 403, 301]
        except Exception:
            # Fallback to boto3
            try:
                self.s3_client.head_bucket(Bucket=bucket_name)
                return True
            except ClientError as e:
                error_code = e.response['Error']['Code']
                # 403 means bucket exists but we don't have access
                # 404 means bucket doesn't exist
                return error_code == '403'
            except Exception:
                return False
    
    async def check_public_access(self, bucket_name: str) -> BucketAccessLevel:
        """Check S3 bucket public access configuration.
        
        Uses multiple methods:
        1. Try anonymous LIST operation (strongest indicator)
        2. Check bucket ACL
        3. Check bucket policy
        4. Check public access block settings
        
        Args:
            bucket_name: Name of the S3 bucket
            
        Returns:
            Access level of the bucket
        """
        try:
            # Method 1: Try anonymous LIST (most reliable)
            url = f"https://{bucket_name}.s3.amazonaws.com"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                
                if response.status_code == 200:
                    # Can list bucket anonymously = public read
                    return BucketAccessLevel.PUBLIC_READ
                elif response.status_code == 403:
                    # Bucket exists but list denied, check other methods
                    pass
            
            # Method 2: Check bucket ACL
            try:
                acl = self.s3_client.get_bucket_acl(Bucket=bucket_name)
                for grant in acl.get('Grants', []):
                    grantee = grant.get('Grantee', {})
                    uri = grantee.get('URI', '')
                    permission = grant.get('Permission', '')
                    
                    # Check for AllUsers or AuthenticatedUsers group
                    if 'AllUsers' in uri:
                        if permission == 'FULL_CONTROL':
                            return BucketAccessLevel.PUBLIC_READ_WRITE
                        elif permission in ['READ', 'READ_ACP']:
                            return BucketAccessLevel.PUBLIC_READ
                        elif permission in ['WRITE', 'WRITE_ACP']:
                            return BucketAccessLevel.PUBLIC_WRITE
                    elif 'AuthenticatedUsers' in uri:
                        return BucketAccessLevel.AUTHENTICATED_READ
            except ClientError:
                pass
            
            # Method 3: Check bucket policy for public statements
            try:
                policy_response = self.s3_client.get_bucket_policy(Bucket=bucket_name)
                policy_str = policy_response.get('Policy', '')
                if '"Principal":"*"' in policy_str or '"Principal":{"AWS":"*"}' in policy_str:
                    if '"Action":"s3:GetObject"' in policy_str:
                        return BucketAccessLevel.PUBLIC_READ
            except ClientError:
                pass
            
            # Method 4: Check public access block
            try:
                public_block = self.s3_client.get_public_access_block(Bucket=bucket_name)
                config = public_block.get('PublicAccessBlockConfiguration', {})
                
                # If all blocks are False, bucket CAN be public (but might not be)
                if not any(config.values()):
                    return BucketAccessLevel.UNKNOWN
            except ClientError:
                # No public access block means it could be public
                pass
            
            return BucketAccessLevel.PRIVATE
            
        except Exception as e:
            self.logger.error("public_access_check_failed", bucket=bucket_name, error=str(e))
            return BucketAccessLevel.UNKNOWN
    
    async def list_files(self, bucket_name: str, max_files: int = 100) -> List[str]:
        """List files in S3 bucket.
        
        Args:
            bucket_name: Name of the bucket
            max_files: Maximum number of files to list
            
        Returns:
            List of file keys
        """
        files = []
        try:
            # Try anonymous access first
            response = self.s3_client.list_objects_v2(
                Bucket=bucket_name,
                MaxKeys=max_files
            )
            
            for obj in response.get('Contents', []):
                files.append(obj['Key'])
                if len(files) >= max_files:
                    break
                    
        except Exception as e:
            self.logger.error("list_files_failed", bucket=bucket_name, error=str(e))
        
        return files
    
    async def get_bucket_permissions(self, bucket_name: str) -> List[str]:
        """Get detailed permissions for S3 bucket.
        
        Args:
            bucket_name: Name of the bucket
            
        Returns:
            List of permission strings
        """
        permissions = []
        
        # Try various S3 operations to determine permissions
        tests = [
            ('list', lambda: self.s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)),
            ('get_acl', lambda: self.s3_client.get_bucket_acl(Bucket=bucket_name)),
            ('get_policy', lambda: self.s3_client.get_bucket_policy(Bucket=bucket_name)),
            ('get_location', lambda: self.s3_client.get_bucket_location(Bucket=bucket_name)),
        ]
        
        for perm_name, test_func in tests:
            try:
                test_func()
                permissions.append(perm_name)
            except ClientError:
                pass
            except Exception:
                pass
        
        return permissions
    
    def _get_bucket_url(self, bucket_name: str) -> str:
        """Get S3 bucket URL.
        
        Args:
            bucket_name: Name of the bucket
            
        Returns:
            Full URL to the bucket
        """
        return f"https://{bucket_name}.s3.amazonaws.com"
