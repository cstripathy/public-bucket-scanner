"""Orchestrator for coordinating scans across multiple cloud providers."""
from typing import List, Dict, Optional
import asyncio
from .base_scanner import BaseScanner, BucketScanResult, CloudProvider
from .aws_scanner import AWSS3Scanner
from .gcp_scanner import GCPStorageScanner
from .azure_scanner import AzureBlobScanner
from src.config import settings
import structlog

logger = structlog.get_logger()


class ScanOrchestrator:
    """Orchestrates scanning across multiple cloud providers."""
    
    def __init__(self):
        """Initialize the scan orchestrator with all scanners."""
        self.scanners: Dict[CloudProvider, BaseScanner] = {}
        
        # Initialize AWS scanner
        self.scanners[CloudProvider.AWS_S3] = AWSS3Scanner(
            access_key=settings.aws_access_key_id,
            secret_key=settings.aws_secret_access_key,
            region=settings.aws_region
        )
        
        # Initialize GCP scanner
        self.scanners[CloudProvider.GCP_GCS] = GCPStorageScanner(
            project_id=settings.gcp_project_id,
            credentials_path=settings.gcp_credentials_path
        )
        
        # Initialize Azure scanner
        self.scanners[CloudProvider.AZURE_BLOB] = AzureBlobScanner(
            account_name=settings.azure_account_name,
            account_key=settings.azure_account_key,
            connection_string=settings.azure_connection_string
        )
        
        logger.info("scan_orchestrator_initialized", providers=len(self.scanners))
    
    async def scan_bucket(
        self,
        bucket_name: str,
        provider: Optional[CloudProvider] = None
    ) -> List[BucketScanResult]:
        """Scan a bucket across specified or all providers.
        
        Args:
            bucket_name: Name of the bucket to scan
            provider: Specific provider to scan, or None for all providers
            
        Returns:
            List of scan results for each provider
        """
        results = []
        
        if provider:
            # Scan specific provider
            scanner = self.scanners.get(provider)
            if scanner:
                result = await scanner.scan_bucket(bucket_name)
                results.append(result)
        else:
            # Scan all providers
            tasks = [
                scanner.scan_bucket(bucket_name)
                for scanner in self.scanners.values()
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions
            results = [r for r in results if isinstance(r, BucketScanResult)]
        
        logger.info(
            "scan_orchestration_complete",
            bucket=bucket_name,
            results=len(results)
        )
        
        return results
    
    async def scan_multiple_buckets(
        self,
        bucket_names: List[str],
        provider: Optional[CloudProvider] = None
    ) -> Dict[str, List[BucketScanResult]]:
        """Scan multiple buckets across providers.
        
        Args:
            bucket_names: List of bucket names to scan
            provider: Specific provider to scan, or None for all providers
            
        Returns:
            Dictionary mapping bucket names to their scan results
        """
        tasks = {
            bucket_name: self.scan_bucket(bucket_name, provider)
            for bucket_name in bucket_names
        }
        
        # Execute all scans concurrently
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        # Map results back to bucket names
        scan_results = {}
        for bucket_name, result in zip(tasks.keys(), results):
            if isinstance(result, list):
                scan_results[bucket_name] = result
            else:
                # Handle exceptions
                logger.error("scan_failed", bucket=bucket_name, error=str(result))
                scan_results[bucket_name] = []
        
        return scan_results
    
    def get_scanner(self, provider: CloudProvider) -> Optional[BaseScanner]:
        """Get scanner for a specific provider.
        
        Args:
            provider: Cloud provider
            
        Returns:
            Scanner instance or None
        """
        return self.scanners.get(provider)
