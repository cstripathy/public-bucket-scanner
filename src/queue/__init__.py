"""Queue module for task distribution."""
from .producer import QueueProducer
from .consumer import QueueConsumer

__all__ = ["QueueProducer", "QueueConsumer"]
