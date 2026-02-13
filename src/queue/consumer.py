"""Queue consumer for processing scan tasks."""
import redis.asyncio as redis
import json
import asyncio
from typing import Optional, Callable
from src.config import settings
from src.scanner.orchestrator import ScanOrchestrator
from src.scanner.base_scanner import CloudProvider
import structlog

logger = structlog.get_logger()


class QueueConsumer:
    """Redis-based queue consumer for processing scan tasks."""
    
    def __init__(self, orchestrator: Optional[ScanOrchestrator] = None):
        """Initialize queue consumer.
        
        Args:
            orchestrator: Scan orchestrator instance
        """
        self.redis_client: Optional[redis.Redis] = None
        self.queue_name = "scan_queue"
        self.orchestrator = orchestrator or ScanOrchestrator()
        self.running = False
    
    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis_client = await redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("queue_consumer_connected", url=settings.redis_url)
        except Exception as e:
            logger.error("queue_consumer_connection_failed", error=str(e))
            raise
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("queue_consumer_disconnected")
    
    async def consume_task(self, timeout: int = 5) -> Optional[dict]:
        """Consume a single task from the queue.
        
        Args:
            timeout: Timeout in seconds for blocking pop
            
        Returns:
            Task dictionary or None if queue is empty
        """
        if not self.redis_client:
            await self.connect()
        
        try:
            # BRPOP: blocking right pop (FIFO for our queue)
            result = await self.redis_client.brpop(self.queue_name, timeout=timeout)
            
            if result:
                _, task_json = result
                task = json.loads(task_json)
                logger.debug("task_consumed", bucket=task.get('bucket_name'))
                return task
            
            return None
            
        except Exception as e:
            logger.error("task_consume_failed", error=str(e))
            return None
    
    async def process_task(self, task: dict, result_callback: Optional[Callable] = None):
        """Process a scan task.
        
        Args:
            task: Task dictionary
            result_callback: Optional callback for handling results
        """
        bucket_name = task.get('bucket_name')
        provider_str = task.get('provider')
        
        logger.info("processing_task", bucket=bucket_name, provider=provider_str)
        
        try:
            # Convert provider string to enum if specified
            provider = None
            if provider_str:
                provider = CloudProvider(provider_str)
            
            # Perform scan
            results = await self.orchestrator.scan_bucket(bucket_name, provider)
            
            # Handle results
            if result_callback:
                for result in results:
                    await result_callback(result)
            
            logger.info(
                "task_processed",
                bucket=bucket_name,
                results_count=len(results)
            )
            
        except Exception as e:
            logger.error(
                "task_processing_failed",
                bucket=bucket_name,
                error=str(e)
            )
    
    async def start(self, result_callback: Optional[Callable] = None, max_concurrent: int = 10):
        """Start consuming tasks continuously.
        
        Args:
            result_callback: Callback for handling scan results
            max_concurrent: Maximum concurrent task processing
        """
        self.running = True
        logger.info("queue_consumer_started", max_concurrent=max_concurrent)
        
        await self.connect()
        
        # Semaphore to limit concurrent processing
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_semaphore(task):
            async with semaphore:
                await self.process_task(task, result_callback)
        
        while self.running:
            try:
                task = await self.consume_task()
                
                if task:
                    # Process task asynchronously without waiting
                    asyncio.create_task(process_with_semaphore(task))
                else:
                    # No task available, brief sleep
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error("consumer_loop_error", error=str(e))
                await asyncio.sleep(5)  # Back off on error
    
    async def stop(self):
        """Stop consuming tasks."""
        self.running = False
        await self.disconnect()
        logger.info("queue_consumer_stopped")
