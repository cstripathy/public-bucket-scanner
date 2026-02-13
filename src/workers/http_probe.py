"""HTTP probe worker for sending HTTP requests to buckets."""
import httpx
from typing import Optional, Dict, Any
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()


@dataclass
class ProbeResult:
    """Result from HTTP probe."""
    url: str
    status_code: Optional[int]
    success: bool
    headers: Optional[Dict[str, str]]
    content_length: Optional[int]
    error: Optional[str]
    response_time: float


class HTTPProbe:
    """HTTP probe for testing bucket accessibility."""
    
    def __init__(self, timeout: int = 10, max_retries: int = 3, follow_redirects: bool = True):
        """Initialize HTTP probe.
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            follow_redirects: Whether to follow HTTP redirects
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.follow_redirects = follow_redirects
        logger.info("http_probe_initialized", timeout=timeout, max_retries=max_retries)
    
    async def probe(self, url: str, method: str = "GET") -> ProbeResult:
        """Probe a URL with HTTP request.
        
        Args:
            url: URL to probe
            method: HTTP method (GET, HEAD, etc.)
            
        Returns:
            Probe result with status and metadata
        """
        import time
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=self.follow_redirects
            ) as client:
                
                if method.upper() == "HEAD":
                    response = await client.head(url)
                else:
                    response = await client.get(url)
                
                response_time = time.time() - start_time
                
                result = ProbeResult(
                    url=url,
                    status_code=response.status_code,
                    success=response.status_code < 400,
                    headers=dict(response.headers),
                    content_length=len(response.content) if method == "GET" else None,
                    error=None,
                    response_time=response_time
                )
                
                logger.debug(
                    "probe_success",
                    url=url,
                    status=response.status_code,
                    time=response_time
                )
                
                return result
                
        except httpx.TimeoutException:
            response_time = time.time() - start_time
            logger.warning("probe_timeout", url=url)
            return ProbeResult(
                url=url,
                status_code=None,
                success=False,
                headers=None,
                content_length=None,
                error="Timeout",
                response_time=response_time
            )
        except httpx.RequestError as e:
            response_time = time.time() - start_time
            logger.error("probe_error", url=url, error=str(e))
            return ProbeResult(
                url=url,
                status_code=None,
                success=False,
                headers=None,
                content_length=None,
                error=str(e),
                response_time=response_time
            )
        except Exception as e:
            response_time = time.time() - start_time
            logger.error("probe_unexpected_error", url=url, error=str(e))
            return ProbeResult(
                url=url,
                status_code=None,
                success=False,
                headers=None,
                content_length=None,
                error=str(e),
                response_time=response_time
            )
    
    async def probe_with_retry(self, url: str, method: str = "GET") -> ProbeResult:
        """Probe URL with automatic retry on failure.
        
        Args:
            url: URL to probe
            method: HTTP method
            
        Returns:
            Probe result
        """
        last_result = None
        
        for attempt in range(self.max_retries):
            result = await self.probe(url, method)
            
            if result.success:
                return result
            
            last_result = result
            
            if attempt < self.max_retries - 1:
                logger.debug("probe_retry", url=url, attempt=attempt + 1)
                await asyncio.sleep(1)  # Brief delay between retries
        
        return last_result
    
    async def probe_bucket_urls(self, bucket_name: str, account_name: str = "") -> Dict[str, ProbeResult]:
        """Probe bucket URLs for all cloud providers.
        
        Args:
            bucket_name: Bucket name
            account_name: Account name (for Azure)
            
        Returns:
            Dictionary of probe results by provider
        """
        import asyncio
        
        urls = {
            'aws_s3': f"https://{bucket_name}.s3.amazonaws.com",
            'gcp_gcs': f"https://storage.googleapis.com/{bucket_name}",
        }
        
        if account_name:
            urls['azure_blob'] = f"https://{account_name}.blob.core.windows.net/{bucket_name}"
        
        # Probe all URLs concurrently
        tasks = {
            provider: self.probe(url, method="HEAD")
            for provider, url in urls.items()
        }
        
        results = {}
        for provider, task in tasks.items():
            results[provider] = await task
        
        return results
