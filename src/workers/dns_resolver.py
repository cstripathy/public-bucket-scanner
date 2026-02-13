"""DNS resolver worker for resolving bucket DNS entries."""
import dns.resolver
import dns.exception
from typing import Optional, List
import asyncio
import structlog

logger = structlog.get_logger()


class DNSResolver:
    """DNS resolver for checking bucket domain resolution."""
    
    def __init__(self, timeout: int = 5, nameservers: Optional[List[str]] = None):
        """Initialize DNS resolver.
        
        Args:
            timeout: DNS query timeout in seconds
            nameservers: List of DNS servers to use (defaults to system DNS)
        """
        self.timeout = timeout
        self.resolver = dns.resolver.Resolver()
        
        if nameservers:
            self.resolver.nameservers = nameservers
        
        self.resolver.lifetime = timeout
        logger.info("dns_resolver_initialized", nameservers=self.resolver.nameservers)
    
    async def resolve(self, hostname: str) -> Optional[List[str]]:
        """Resolve hostname to IP addresses.
        
        Args:
            hostname: Hostname to resolve
            
        Returns:
            List of IP addresses or None if resolution fails
        """
        try:
            # Run DNS resolution in thread pool (dnspython is not async)
            loop = asyncio.get_event_loop()
            answers = await loop.run_in_executor(
                None,
                lambda: self.resolver.resolve(hostname, 'A')
            )
            
            ips = [str(rdata) for rdata in answers]
            logger.debug("dns_resolved", hostname=hostname, ips=ips)
            return ips
            
        except dns.resolver.NXDOMAIN:
            logger.debug("dns_nxdomain", hostname=hostname)
            return None
        except dns.resolver.Timeout:
            logger.warning("dns_timeout", hostname=hostname)
            return None
        except dns.exception.DNSException as e:
            logger.error("dns_error", hostname=hostname, error=str(e))
            return None
        except Exception as e:
            logger.error("dns_unexpected_error", hostname=hostname, error=str(e))
            return None
    
    async def resolve_bucket_domains(self, bucket_name: str) -> dict:
        """Resolve bucket domains for all cloud providers.
        
        Args:
            bucket_name: Bucket name to check
            
        Returns:
            Dictionary with resolution results for each provider
        """
        domains = {
            'aws_s3': f"{bucket_name}.s3.amazonaws.com",
            'gcp_gcs': f"storage.googleapis.com",  # GCS uses storage.googleapis.com/<bucket>
            'azure_blob': None  # Azure requires account name
        }
        
        results = {}
        tasks = []
        
        for provider, domain in domains.items():
            if domain:
                tasks.append((provider, self.resolve(domain)))
        
        # Resolve all domains concurrently
        for provider, task in tasks:
            results[provider] = await task
        
        return results
    
    async def check_dns_exists(self, hostname: str) -> bool:
        """Check if DNS entry exists for hostname.
        
        Args:
            hostname: Hostname to check
            
        Returns:
            True if DNS entry exists
        """
        ips = await self.resolve(hostname)
        return ips is not None and len(ips) > 0
