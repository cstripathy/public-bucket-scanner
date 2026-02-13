"""FastAPI application main file."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog
from src.config import settings
from src.database import DatabaseRepository
from src.queue import QueueProducer
from . import routes

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()

# Global instances
db_repo: DatabaseRepository = None
queue_producer: QueueProducer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI app."""
    global db_repo, queue_producer
    
    # Startup
    logger.info("application_starting")
    
    # Initialize database
    db_repo = DatabaseRepository()
    await db_repo.init_db()
    app.state.db = db_repo
    
    # Initialize queue producer
    queue_producer = QueueProducer()
    await queue_producer.connect()
    app.state.queue = queue_producer
    
    logger.info("application_started")
    
    yield
    
    # Shutdown
    logger.info("application_shutting_down")
    
    if queue_producer:
        await queue_producer.disconnect()
    
    logger.info("application_stopped")


# Create FastAPI app
app = FastAPI(
    title="Bucket Scanner API",
    description="Cloud storage bucket security scanner",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
