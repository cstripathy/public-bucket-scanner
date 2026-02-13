"""IP rotation and proxy management."""
import random
from typing import List, Optional
import httpx
import structlog

logger = structlog.get_logger()


class IPRotator:
    """Manages IP rotation through proxy pools."""
    
    def __init__(self, proxy_list: List[str] = None, rotation_strategy: str = "round_robin"):
        """Initialize IP rotator.
        
        Args:
            proxy_list: List of proxy URLs (e.g., ['socks5://host:port', 'http://host:port'])
            rotation_strategy: Strategy for proxy selection ('round_robin', 'random', 'failover')
        """
        self.proxy_list = proxy_list or []
        self.rotation_strategy = rotation_strategy
        self.current_index = 0
        self.failed_proxies = set()
        logger.info(
            "ip_rotator_initialized",
            proxies=len(self.proxy_list),
            strategy=rotation_strategy
        )
    
    def get_next_proxy(self) -> Optional[str]:
        """Get next proxy based on rotation strategy.
        
        Returns:
            Proxy URL or None if no proxies available
        """
        if not self.proxy_list:
            return None
        
        available_proxies = [
            p for p in self.proxy_list if p not in self.failed_proxies
        ]
        
        if not available_proxies:
            # Reset failed proxies if all have failed
            logger.warning("all_proxies_failed_resetting")
            self.failed_proxies.clear()
            available_proxies = self.proxy_list.copy()
        
        if self.rotation_strategy == "round_robin":
            proxy = available_proxies[self.current_index % len(available_proxies)]
            self.current_index += 1
            return proxy
        
        elif self.rotation_strategy == "random":
            return random.choice(available_proxies)
        
        elif self.rotation_strategy == "failover":
            # Always use first available proxy
            return available_proxies[0]
        
        return None
    
    def mark_proxy_failed(self, proxy: str):
        """Mark a proxy as failed.
        
        Args:
            proxy: Proxy URL that failed
        """
        self.failed_proxies.add(proxy)
        logger.warning("proxy_marked_failed", proxy=proxy)
    
    def mark_proxy_success(self, proxy: str):
        """Mark a proxy as successful (remove from failed list).
        
        Args:
            proxy: Proxy URL that succeeded
        """
        if proxy in self.failed_proxies:
            self.failed_proxies.remove(proxy)
            logger.info("proxy_restored", proxy=proxy)
    
    async def test_proxy(self, proxy: str, test_url: str = "https://api.ipify.org") -> bool:
        """Test if a proxy is working.
        
        Args:
            proxy: Proxy URL to test
            test_url: URL to test against
            
        Returns:
            True if proxy is working
        """
        try:
            async with httpx.AsyncClient(proxies={"all://": proxy}, timeout=10.0) as client:
                response = await client.get(test_url)
                success = response.status_code == 200
                
                if success:
                    logger.info("proxy_test_success", proxy=proxy, ip=response.text.strip())
                else:
                    logger.warning("proxy_test_failed", proxy=proxy, status=response.status_code)
                
                return success
                
        except Exception as e:
            logger.error("proxy_test_error", proxy=proxy, error=str(e))
            return False
    
    async def test_all_proxies(self) -> List[str]:
        """Test all proxies and return working ones.
        
        Returns:
            List of working proxy URLs
        """
        working = []
        
        for proxy in self.proxy_list:
            if await self.test_proxy(proxy):
                working.append(proxy)
        
        logger.info("proxy_test_complete", total=len(self.proxy_list), working=len(working))
        return working
    
    def get_proxy_config(self) -> Optional[dict]:
        """Get httpx-compatible proxy configuration.
        
        Returns:
            Dictionary with proxy configuration or None
        """
        proxy = self.get_next_proxy()
        if proxy:
            return {"all://": proxy}
        return None


class DirectIPRotator:
    """Rotates between multiple network interfaces (for systems with multiple IPs)."""
    
    def __init__(self, interface_ips: List[str] = None):
        """Initialize direct IP rotator.
        
        Args:
            interface_ips: List of local IP addresses to rotate through
        """
        self.interface_ips = interface_ips or []
        self.current_index = 0
        logger.info("direct_ip_rotator_initialized", ips=len(self.interface_ips))
    
    def get_next_ip(self) -> Optional[str]:
        """Get next IP address.
        
        Returns:
            IP address or None
        """
        if not self.interface_ips:
            return None
        
        ip = self.interface_ips[self.current_index % len(self.interface_ips)]
        self.current_index += 1
        return ip
    
    def get_transport_config(self) -> Optional[dict]:
        """Get transport configuration for binding to specific IP.
        
        Returns:
            Transport configuration dict or None
        """
        ip = self.get_next_ip()
        if ip:
            return {"local_addr": (ip, 0)}
        return None
