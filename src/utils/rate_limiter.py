"""Rate limiter for controlling request rates."""
import asyncio
import time
from collections import deque
from typing import Optional
import structlog

logger = structlog.get_logger()


class RateLimiter:
    """Token bucket rate limiter for async operations."""
    
    def __init__(self, max_requests: int = 10, time_window: float = 1.0):
        """Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = asyncio.Lock()
        logger.info(
            "rate_limiter_initialized",
            max_requests=max_requests,
            window=time_window
        )
    
    async def acquire(self, timeout: Optional[float] = None) -> bool:
        """Acquire permission to make a request.
        
        Args:
            timeout: Maximum time to wait for permission (None = wait forever)
            
        Returns:
            True if permission acquired, False if timeout
        """
        start_time = time.time()
        
        while True:
            async with self.lock:
                now = time.time()
                
                # Remove old requests outside the time window
                while self.requests and self.requests[0] < now - self.time_window:
                    self.requests.popleft()
                
                # Check if we can make a request
                if len(self.requests) < self.max_requests:
                    self.requests.append(now)
                    return True
                
                # Check timeout
                if timeout is not None and (time.time() - start_time) >= timeout:
                    return False
            
            # Wait a bit before retrying
            wait_time = self.time_window / self.max_requests
            await asyncio.sleep(wait_time)
    
    async def __aenter__(self):
        """Context manager entry."""
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass
    
    def get_current_rate(self) -> float:
        """Get current request rate.
        
        Returns:
            Requests per second
        """
        now = time.time()
        # Count requests in the last second
        recent = sum(1 for req_time in self.requests if req_time > now - 1.0)
        return recent


class AdaptiveRateLimiter(RateLimiter):
    """Rate limiter that adapts based on success/failure rates."""
    
    def __init__(self, initial_rate: int = 10, min_rate: int = 1, max_rate: int = 100):
        """Initialize adaptive rate limiter.
        
        Args:
            initial_rate: Initial request rate
            min_rate: Minimum request rate
            max_rate: Maximum request rate
        """
        super().__init__(max_requests=initial_rate, time_window=1.0)
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.success_count = 0
        self.failure_count = 0
        logger.info(
            "adaptive_rate_limiter_initialized",
            initial=initial_rate,
            min=min_rate,
            max=max_rate
        )
    
    async def report_success(self):
        """Report a successful request."""
        self.success_count += 1
        
        # Gradually increase rate on sustained success
        if self.success_count > 10 and self.failure_count == 0:
            new_rate = min(self.max_requests + 1, self.max_rate)
            if new_rate != self.max_requests:
                self.max_requests = new_rate
                logger.info("rate_increased", new_rate=new_rate)
            self.success_count = 0
    
    async def report_failure(self):
        """Report a failed request (e.g., rate limited by target)."""
        self.failure_count += 1
        self.success_count = 0
        
        # Quickly decrease rate on failure
        if self.failure_count >= 3:
            new_rate = max(self.max_requests // 2, self.min_rate)
            if new_rate != self.max_requests:
                self.max_requests = new_rate
                logger.warning("rate_decreased", new_rate=new_rate)
            self.failure_count = 0
