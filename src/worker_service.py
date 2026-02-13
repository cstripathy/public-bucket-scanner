"""Worker service for processing scan tasks from queue."""
import asyncio
from src.queue.consumer import QueueConsumer
from src.database import DatabaseRepository
from src.utils.notifier import Notifier
from src.config import settings
import structlog
import signal
import sys

logger = structlog.get_logger()

# Global flag for graceful shutdown
shutdown_flag = False


async def result_callback(scan_result):
    """Callback for handling scan results.
    
    Args:
        scan_result: BucketScanResult from scanner
    """
    try:
        db_repo = DatabaseRepository()
        notifier = Notifier()
        
        # Calculate risk
        risk_level = "low"
        risk_score = 0
        
        if scan_result.is_accessible:
            risk_score += 30
            risk_level = "medium"
            
            if scan_result.sensitive_files:
                risk_score += len(scan_result.sensitive_files) * 10
                risk_level = "high"
        
        # Save to database
        result_data = {
            'bucket_name': scan_result.bucket_name,
            'provider': scan_result.provider.value,
            'exists': scan_result.exists,
            'is_accessible': scan_result.is_accessible,
            'access_level': scan_result.access_level.value,
            'url': scan_result.url,
            'permissions': scan_result.permissions,
            'files_found': scan_result.files_found,
            'sensitive_files': scan_result.sensitive_files,
            'risk_level': risk_level,
            'risk_score': min(risk_score, 100),
            'error': scan_result.error,
            'metadata': scan_result.metadata
        }
        
        db_result = await db_repo.create_scan_result(result_data)
        
        # Send notification if enabled
        if scan_result.is_accessible:
            await notifier.send_finding(
                bucket_name=scan_result.bucket_name,
                provider=scan_result.provider.value,
                risk_level=risk_level,
                details={
                    'url': scan_result.url,
                    'is_accessible': scan_result.is_accessible,
                    'sensitive_files': scan_result.sensitive_files,
                    'recommendations': [
                        'Review bucket permissions',
                        'Remove public access if not required',
                        'Audit sensitive files'
                    ]
                }
            )
        
        logger.info(
            "scan_result_processed",
            bucket=scan_result.bucket_name,
            result_id=db_result.id,
            risk_level=risk_level
        )
        
    except Exception as e:
        logger.error("result_callback_error", error=str(e))


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global shutdown_flag
    logger.info("shutdown_signal_received", signal=signum)
    shutdown_flag = True


async def main():
    """Main worker function."""
    global shutdown_flag
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("worker_starting")
    
    # Initialize database
    db_repo = DatabaseRepository()
    await db_repo.init_db()
    
    # Initialize consumer
    consumer = QueueConsumer()
    
    try:
        # Start consuming tasks
        logger.info("worker_started", max_concurrent=settings.max_concurrent_workers)
        
        # Run consumer until shutdown signal
        consumer_task = asyncio.create_task(
            consumer.start(
                result_callback=result_callback,
                max_concurrent=settings.max_concurrent_workers
            )
        )
        
        # Wait for shutdown signal
        while not shutdown_flag:
            await asyncio.sleep(1)
        
        # Graceful shutdown
        logger.info("worker_stopping")
        await consumer.stop()
        
        # Wait for consumer task to complete
        try:
            await asyncio.wait_for(consumer_task, timeout=30.0)
        except asyncio.TimeoutError:
            logger.warning("consumer_shutdown_timeout")
            consumer_task.cancel()
        
    except Exception as e:
        logger.error("worker_error", error=str(e))
        raise
    finally:
        logger.info("worker_stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("worker_interrupted")
        sys.exit(0)
    except Exception as e:
        logger.error("worker_fatal_error", error=str(e))
        sys.exit(1)
