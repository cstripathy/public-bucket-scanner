"""API routes for bucket scanner."""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from src.scanner.orchestrator import ScanOrchestrator
from src.scanner.base_scanner import CloudProvider
from src.database import DatabaseRepository
from src.queue import QueueProducer
from src.workers import ContentAnalyzer, PermissionChecker
from src.enumeration import BucketNameGenerator, WordlistManager
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["scanner"])

# Request/Response models
class ScanRequest(BaseModel):
    """Request model for bucket scan."""
    bucket_name: str = Field(..., description="Name of the bucket to scan")
    provider: Optional[str] = Field(None, description="Cloud provider (aws_s3, gcp_gcs, azure_blob)")
    priority: int = Field(0, description="Scan priority (higher = more urgent)")
    

class ScanResponse(BaseModel):
    """Response model for scan result."""
    id: int
    bucket_name: str
    provider: str
    exists: bool
    is_accessible: bool
    access_level: str
    url: str
    risk_level: Optional[str] = None
    risk_score: int
    created_at: str


class TaskResponse(BaseModel):
    """Response model for scan task."""
    task_id: int
    bucket_name: str
    status: str
    message: str


class StatisticsResponse(BaseModel):
    """Response model for statistics."""
    total_scans: int
    public_buckets: int
    open_findings: Dict[str, int]


# Dependency to get database
def get_db(request: Request):
    return request.app.state.db


# Dependency to get queue
def get_queue(request: Request):
    return request.app.state.queue


@router.post("/scan/immediate", response_model=List[Dict[str, Any]])
async def scan_bucket_immediate(
    request: ScanRequest,
    db: DatabaseRepository = Depends(get_db)
):
    """Perform an immediate bucket scan (synchronous).
    
    This will scan the bucket right away and return results.
    Use for quick checks. For large-scale scanning, use /scan/queue endpoint.
    """
    logger.info("immediate_scan_requested", bucket=request.bucket_name)
    
    try:
        # Initialize orchestrator
        orchestrator = ScanOrchestrator()
        
        # Parse provider if specified
        provider = None
        if request.provider:
            try:
                provider = CloudProvider(request.provider)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid provider: {request.provider}"
                )
        
        # Perform scan
        results = await orchestrator.scan_bucket(request.bucket_name, provider)
        
        # Save results to database
        saved_results = []
        for result in results:
            # Calculate risk
            risk_level = "low"
            risk_score = 0
            
            if result.is_accessible:
                risk_score += 30
                risk_level = "medium"
                
                if result.sensitive_files:
                    risk_score += len(result.sensitive_files) * 10
                    risk_level = "high"
            
            result_data = {
                'bucket_name': result.bucket_name,
                'provider': result.provider.value,
                'exists': result.exists,
                'is_accessible': result.is_accessible,
                'access_level': result.access_level.value,
                'url': result.url,
                'permissions': result.permissions,
                'files_found': result.files_found,
                'sensitive_files': result.sensitive_files,
                'risk_level': risk_level,
                'risk_score': min(risk_score, 100),
                'error': result.error,
                'metadata': result.metadata
            }
            
            db_result = await db.create_scan_result(result_data)
            saved_results.append(db_result.to_dict())
        
        return saved_results
        
    except Exception as e:
        logger.error("immediate_scan_failed", bucket=request.bucket_name, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan/queue", response_model=TaskResponse)
async def scan_bucket_queued(
    request: ScanRequest,
    db: DatabaseRepository = Depends(get_db),
    queue: QueueProducer = Depends(get_queue)
):
    """Queue a bucket scan for asynchronous processing.
    
    This adds the scan to a queue for processing by workers.
    Use for large-scale scanning operations.
    """
    logger.info("queued_scan_requested", bucket=request.bucket_name)
    
    try:
        # Create task in database
        task_data = {
            'bucket_name': request.bucket_name,
            'provider': request.provider,
            'status': 'pending',
            'priority': request.priority
        }
        
        task = await db.create_scan_task(task_data)
        
        # Publish to queue
        success = await queue.publish_scan_task(
            bucket_name=request.bucket_name,
            provider=request.provider,
            priority=request.priority,
            metadata={'task_id': task.id}
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to queue task")
        
        return TaskResponse(
            task_id=task.id,
            bucket_name=request.bucket_name,
            status="queued",
            message=f"Scan queued successfully. Task ID: {task.id}"
        )
        
    except Exception as e:
        logger.error("queue_scan_failed", bucket=request.bucket_name, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/{bucket_name}", response_model=List[Dict[str, Any]])
async def get_bucket_results(
    bucket_name: str,
    limit: int = 10,
    db: DatabaseRepository = Depends(get_db)
):
    """Get scan results for a specific bucket."""
    try:
        results = await db.get_scan_results_by_bucket(bucket_name, limit)
        return [r.to_dict() for r in results]
    except Exception as e:
        logger.error("get_results_failed", bucket=bucket_name, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results", response_model=List[Dict[str, Any]])
async def get_recent_results(
    limit: int = 50,
    db: DatabaseRepository = Depends(get_db)
):
    """Get recent scan results."""
    try:
        results = await db.get_recent_scan_results(limit)
        return [r.to_dict() for r in results]
    except Exception as e:
        logger.error("get_recent_results_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/public-buckets", response_model=List[Dict[str, Any]])
async def get_public_buckets(
    limit: int = 100,
    db: DatabaseRepository = Depends(get_db)
):
    """Get all publicly accessible buckets found."""
    try:
        results = await db.get_public_buckets(limit)
        return [r.to_dict() for r in results]
    except Exception as e:
        logger.error("get_public_buckets_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/findings", response_model=List[Dict[str, Any]])
async def get_findings(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
    db: DatabaseRepository = Depends(get_db)
):
    """Get security findings with optional filters."""
    try:
        findings = await db.get_findings(status, severity, limit)
        return [f.to_dict() for f in findings]
    except Exception as e:
        logger.error("get_findings_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/findings/{bucket_name}", response_model=List[Dict[str, Any]])
async def get_bucket_findings(
    bucket_name: str,
    db: DatabaseRepository = Depends(get_db)
):
    """Get all findings for a specific bucket."""
    try:
        findings = await db.get_findings_by_bucket(bucket_name)
        return [f.to_dict() for f in findings]
    except Exception as e:
        logger.error("get_bucket_findings_failed", bucket=bucket_name, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(db: DatabaseRepository = Depends(get_db)):
    """Get overall scanning statistics."""
    try:
        stats = await db.get_statistics()
        return StatisticsResponse(**stats)
    except Exception as e:
        logger.error("get_statistics_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}", response_model=Dict[str, Any])
async def get_task_status(
    task_id: int,
    db: DatabaseRepository = Depends(get_db)
):
    """Get status of a queued scan task."""
    try:
        task = await db.get_scan_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_task_failed", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue/size")
async def get_queue_size(queue: QueueProducer = Depends(get_queue)):
    """Get current queue size."""
    try:
        size = await queue.get_queue_size()
        return {"queue_size": size}
    except Exception as e:
        logger.error("get_queue_size_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENUMERATION ENDPOINTS
# ============================================================================

class EnumerationRequest(BaseModel):
    """Request model for bucket enumeration."""
    company_name: str = Field(..., description="Company/organization name")
    providers: Optional[List[str]] = Field(
        default=["aws_s3", "gcp_gcs", "azure_blob"],
        description="Cloud providers to enumerate"
    )
    use_wordlist: Optional[bool] = Field(
        default=False,
        description="Use wordlist for generation"
    )
    wordlist_names: Optional[List[str]] = Field(
        default=["common"],
        description="Wordlist names to use"
    )
    max_names: Optional[int] = Field(
        default=100,
        description="Maximum bucket names to generate"
    )
    auto_scan: Optional[bool] = Field(
        default=False,
        description="Automatically queue generated names for scanning"
    )


class EnumerationResponse(BaseModel):
    """Response model for enumeration."""
    company_name: str
    names_generated: int
    candidates: List[Dict[str, str]]
    queued_for_scan: Optional[int] = 0
    message: str


@router.post("/enumerate", response_model=EnumerationResponse)
async def enumerate_bucket_names(
    request: EnumerationRequest,
    queue: QueueProducer = Depends(get_queue)
):
    """Generate potential bucket names for a company.
    
    This endpoint generates bucket name candidates using various strategies:
    - Pattern-based generation (company-backup, backup-company, etc.)
    - Environment-based (company-prod-data, company-dev-uploads)
    - Wordlist combinations (if enabled)
    - Common public bucket patterns
    
    Can automatically queue generated names for scanning.
    """
    try:
        generator = BucketNameGenerator()
        
        # Generate names
        if request.use_wordlist:
            wordlist_mgr = WordlistManager()
            words = wordlist_mgr.load_multiple(request.wordlist_names)
            candidates = generator.generate_from_wordlist(
                request.company_name,
                words,
                request.providers,
                request.max_names
            )
        else:
            candidates = generator.generate_for_company(
                request.company_name,
                request.providers,
                request.max_names
            )
        
        queued_count = 0
        
        # Auto-queue for scanning if requested
        if request.auto_scan:
            for candidate in candidates:
                try:
                    await queue.enqueue_scan(
                        bucket_name=candidate["bucket_name"],
                        provider=candidate["provider"],
                        priority=5
                    )
                    queued_count += 1
                except Exception as e:
                    logger.warning(
                        "failed_to_queue_candidate",
                        bucket=candidate["bucket_name"],
                        error=str(e)
                    )
        
        logger.info(
            "enumeration_completed",
            company=request.company_name,
            generated=len(candidates),
            queued=queued_count
        )
        
        return EnumerationResponse(
            company_name=request.company_name,
            names_generated=len(candidates),
            candidates=candidates[:50],  # Return first 50 for display
            queued_for_scan=queued_count if request.auto_scan else None,
            message=f"Generated {len(candidates)} potential bucket names" +
                   (f", {queued_count} queued for scanning" if request.auto_scan else "")
        )
        
    except Exception as e:
        logger.error("enumeration_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/enumerate/wordlists")
async def list_wordlists():
    """List available wordlists."""
    try:
        wordlist_mgr = WordlistManager()
        wordlists = wordlist_mgr.get_available_wordlists()
        
        return {
            "wordlists": wordlists,
            "count": len(wordlists)
        }
    except Exception as e:
        logger.error("list_wordlists_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enumerate/common-patterns")
async def enumerate_common_patterns(
    providers: Optional[List[str]] = None,
    auto_scan: bool = False,
    queue: QueueProducer = Depends(get_queue)
):
    """Generate and optionally scan common public bucket patterns.
    
    This generates commonly found bucket names like:
    - backup, backups, data, uploads, etc.
    - With variations: backup-prod, data-dev, etc.
    
    Useful for discovering commonly misconfigured public buckets.
    """
    try:
        generator = BucketNameGenerator()
        candidates = generator.generate_common_public_buckets()
        
        # Filter by providers if specified
        if providers:
            candidates = [
                c for c in candidates
                if c["provider"] in providers
            ]
        
        queued_count = 0
        
        # Auto-queue if requested
        if auto_scan:
            for candidate in candidates:
                try:
                    await queue.enqueue_scan(
                        bucket_name=candidate["bucket_name"],
                        provider=candidate["provider"],
                        priority=3  # Lower priority for common scans
                    )
                    queued_count += 1
                except Exception:
                    pass
        
        return {
            "patterns_generated": len(candidates),
            "providers": providers or ["aws_s3", "gcp_gcs", "azure_blob"],
            "queued_for_scan": queued_count if auto_scan else 0,
            "candidates": candidates[:30]  # Show first 30
        }
        
    except Exception as e:
        logger.error("common_patterns_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

