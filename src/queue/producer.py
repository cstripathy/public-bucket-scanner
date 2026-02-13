"""Queue producer for publishing scan tasks."""
import redis.asyncio as redis
import json
from typing import Optional, Dict, Any
from src.config import settings
import structlog

logger = structlog.get_logger()


class QueueProducer:
    """Redis-based queue producer for scan tasks."""
    
    def __init__(self):
        """Initialize queue producer."""
        self.redis_client: Optional[redis.Redis] = None
        self.queue_name = "scan_queue"
    
    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis_client = await redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("queue_producer_connected", url=settings.redis_url)
        except Exception as e:
            logger.error("queue_producer_connection_failed", error=str(e))
            raise
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("queue_producer_disconnected")
    
    async def publish_scan_task(
        self,
        bucket_name: str,
        provider: Optional[str] = None,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Publish a scan task to the queue.
        
        Args:
            bucket_name: Name of bucket to scan
            provider: Specific provider or None for all
            priority: Task priority (higher = more urgent)
            metadata: Additional task metadata
            
        Returns:
            True if task was published successfully
        """
        if not self.redis_client:
            await self.connect()
        
        task = {
            'bucket_name': bucket_name,
            'provider': provider,
            'priority': priority,
            'metadata': metadata or {}
        }
        
        try:
            # Add to Redis list (LPUSH for priority queue behavior)
            task_json = json.dumps(task)
            await self.redis_client.lpush(self.queue_name, task_json)
            
            logger.info(
                "task_published",
                bucket=bucket_name,
                provider=provider,
                priority=priority
            )
            return True
            
        except Exception as e:
            logger.error("task_publish_failed", bucket=bucket_name, error=str(e))
            return False
    
    async def get_queue_size(self) -> int:
        """Get current queue size.
        
        Returns:
            Number of pending tasks
        """
        if not self.redis_client:
            await self.connect()
        
        try:
            size = await self.redis_client.llen(self.queue_name)
            return size
        except Exception as e:
            logger.error("get_queue_size_failed", error=str(e))
            return 0
