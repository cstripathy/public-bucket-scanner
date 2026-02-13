"""Database repository for CRUD operations."""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy import desc, func
from .models import Base, ScanResult, ScanTask, Finding
from src.config import settings
import structlog

logger = structlog.get_logger()


class DatabaseRepository:
    """Repository for database operations."""
    
    def __init__(self):
        """Initialize database repository."""
        # Convert postgresql:// to postgresql+asyncpg://
        db_url = settings.database_url.replace('postgresql://', 'postgresql+asyncpg://')
        
        self.engine = create_async_engine(
            db_url,
            echo=settings.debug,
            future=True
        )
        
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        logger.info("database_repository_initialized")
    
    async def init_db(self):
        """Initialize database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("database_tables_created")
    
    async def drop_db(self):
        """Drop all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("database_tables_dropped")
    
    # ============= Scan Result Operations =============
    
    async def create_scan_result(self, result_data: Dict[str, Any]) -> ScanResult:
        """Create a new scan result.
        
        Args:
            result_data: Dictionary with scan result data
            
        Returns:
            Created ScanResult instance
        """
        async with self.async_session() as session:
            result = ScanResult(**result_data)
            session.add(result)
            await session.commit()
            await session.refresh(result)
            logger.info("scan_result_created", id=result.id, bucket=result.bucket_name)
            return result
    
    async def get_scan_result(self, result_id: int) -> Optional[ScanResult]:
        """Get scan result by ID."""
        async with self.async_session() as session:
            stmt = select(ScanResult).where(ScanResult.id == result_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    async def get_scan_results_by_bucket(
        self,
        bucket_name: str,
        limit: int = 10
    ) -> List[ScanResult]:
        """Get recent scan results for a bucket."""
        async with self.async_session() as session:
            stmt = (
                select(ScanResult)
                .where(ScanResult.bucket_name == bucket_name)
                .order_by(desc(ScanResult.created_at))
                .limit(limit)
            )
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def get_recent_scan_results(self, limit: int = 50) -> List[ScanResult]:
        """Get recent scan results."""
        async with self.async_session() as session:
            stmt = (
                select(ScanResult)
                .order_by(desc(ScanResult.created_at))
                .limit(limit)
            )
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def get_public_buckets(self, limit: int = 100) -> List[ScanResult]:
        """Get all publicly accessible buckets."""
        async with self.async_session() as session:
            stmt = (
                select(ScanResult)
                .where(ScanResult.is_accessible == True)
                .order_by(desc(ScanResult.risk_score))
                .limit(limit)
            )
            result = await session.execute(stmt)
            return result.scalars().all()
    
    # ============= Scan Task Operations =============
    
    async def create_scan_task(self, task_data: Dict[str, Any]) -> ScanTask:
        """Create a new scan task."""
        async with self.async_session() as session:
            task = ScanTask(**task_data)
            session.add(task)
            await session.commit()
            await session.refresh(task)
            logger.info("scan_task_created", id=task.id, bucket=task.bucket_name)
            return task
    
    async def get_scan_task(self, task_id: int) -> Optional[ScanTask]:
        """Get scan task by ID."""
        async with self.async_session() as session:
            stmt = select(ScanTask).where(ScanTask.id == task_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    async def update_scan_task_status(
        self,
        task_id: int,
        status: str,
        **kwargs
    ) -> Optional[ScanTask]:
        """Update scan task status and related fields."""
        async with self.async_session() as session:
            stmt = select(ScanTask).where(ScanTask.id == task_id)
            result = await session.execute(stmt)
            task = result.scalar_one_or_none()
            
            if task:
                task.status = status
                for key, value in kwargs.items():
                    setattr(task, key, value)
                await session.commit()
                await session.refresh(task)
            
            return task
    
    # ============= Finding Operations =============
    
    async def create_finding(self, finding_data: Dict[str, Any]) -> Finding:
        """Create a new security finding."""
        async with self.async_session() as session:
            finding = Finding(**finding_data)
            session.add(finding)
            await session.commit()
            await session.refresh(finding)
            logger.info("finding_created", id=finding.id, severity=finding.severity)
            return finding
    
    async def get_findings(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> List[Finding]:
        """Get findings with optional filters."""
        async with self.async_session() as session:
            stmt = select(Finding).order_by(desc(Finding.created_at))
            
            if status:
                stmt = stmt.where(Finding.status == status)
            if severity:
                stmt = stmt.where(Finding.severity == severity)
            
            stmt = stmt.limit(limit)
            
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def get_findings_by_bucket(self, bucket_name: str) -> List[Finding]:
        """Get all findings for a specific bucket."""
        async with self.async_session() as session:
            stmt = (
                select(Finding)
                .where(Finding.bucket_name == bucket_name)
                .order_by(desc(Finding.created_at))
            )
            result = await session.execute(stmt)
            return result.scalars().all()
    
    # ============= Statistics =============
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics."""
        async with self.async_session() as session:
            # Total scans
            total_scans = await session.execute(select(func.count(ScanResult.id)))
            total_count = total_scans.scalar()
            
            # Public buckets
            public_count = await session.execute(
                select(func.count(ScanResult.id))
                .where(ScanResult.is_accessible == True)
            )
            public = public_count.scalar()
            
            # Findings by severity
            critical = await session.execute(
                select(func.count(Finding.id))
                .where(Finding.severity == 'critical')
                .where(Finding.status == 'open')
            )
            high = await session.execute(
                select(func.count(Finding.id))
                .where(Finding.severity == 'high')
                .where(Finding.status == 'open')
            )
            medium = await session.execute(
                select(func.count(Finding.id))
                .where(Finding.severity == 'medium')
                .where(Finding.status == 'open')
            )
            
            return {
                'total_scans': total_count,
                'public_buckets': public,
                'open_findings': {
                    'critical': critical.scalar(),
                    'high': high.scalar(),
                    'medium': medium.scalar()
                }
            }
