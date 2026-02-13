"""Permission checker worker for analyzing bucket permissions."""
from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import structlog

logger = structlog.get_logger()


class PermissionType(Enum):
    """Types of permissions to check."""
    READ = "read"
    WRITE = "write"
    LIST = "list"
    DELETE = "delete"
    READ_ACL = "read_acl"
    WRITE_ACL = "write_acl"


@dataclass
class PermissionCheckResult:
    """Result from permission check."""
    bucket_name: str
    provider: str
    permissions: List[PermissionType]
    is_public: bool
    is_writable: bool
    risk_level: str  # low, medium, high, critical
    recommendations: List[str]


class PermissionChecker:
    """Analyzes and checks bucket permissions."""
    
    def __init__(self):
        """Initialize permission checker."""
        logger.info("permission_checker_initialized")
    
    def analyze_permissions(
        self,
        bucket_name: str,
        provider: str,
        permissions: List[str],
        is_public: bool,
        files_found: List[str] = None
    ) -> PermissionCheckResult:
        """Analyze bucket permissions and determine risk level.
        
        Args:
            bucket_name: Name of the bucket
            provider: Cloud provider
            permissions: List of detected permissions
            is_public: Whether bucket is publicly accessible
            files_found: List of files found in bucket
            
        Returns:
            Permission check result with risk assessment
        """
        perm_types = []
        
        # Map permission strings to types
        if 'list' in permissions:
            perm_types.append(PermissionType.LIST)
        if 'read' in permissions or 'get' in permissions:
            perm_types.append(PermissionType.READ)
        if 'write' in permissions or 'put' in permissions:
            perm_types.append(PermissionType.WRITE)
        if 'delete' in permissions:
            perm_types.append(PermissionType.DELETE)
        
        # Determine if writable
        is_writable = any(p in perm_types for p in [
            PermissionType.WRITE,
            PermissionType.DELETE,
            PermissionType.WRITE_ACL
        ])
        
        # Calculate risk level
        risk_level = self._calculate_risk_level(
            is_public=is_public,
            is_writable=is_writable,
            permissions=perm_types,
            files_found=files_found
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            is_public=is_public,
            is_writable=is_writable,
            provider=provider,
            files_found=files_found
        )
        
        result = PermissionCheckResult(
            bucket_name=bucket_name,
            provider=provider,
            permissions=perm_types,
            is_public=is_public,
            is_writable=is_writable,
            risk_level=risk_level,
            recommendations=recommendations
        )
        
        logger.info(
            "permission_analysis_complete",
            bucket=bucket_name,
            risk=risk_level,
            public=is_public,
            writable=is_writable
        )
        
        return result
    
    def _calculate_risk_level(
        self,
        is_public: bool,
        is_writable: bool,
        permissions: List[PermissionType],
        files_found: List[str] = None
    ) -> str:
        """Calculate risk level based on permissions and exposure.
        
        Args:
            is_public: Whether bucket is public
            is_writable: Whether bucket is writable
            permissions: List of permission types
            files_found: List of files found
            
        Returns:
            Risk level: low, medium, high, or critical
        """
        if not is_public:
            return "low"
        
        # Public + writable = critical
        if is_writable:
            return "critical"
        
        # Public with sensitive files = high
        if files_found:
            sensitive_patterns = ['.env', 'secret', 'password', 'credential', 'key', '.pem']
            has_sensitive = any(
                any(pattern in f.lower() for pattern in sensitive_patterns)
                for f in files_found
            )
            if has_sensitive:
                return "high"
        
        # Public read-only with files = medium
        if files_found and len(files_found) > 0:
            return "medium"
        
        # Public but empty or list-only = low-medium
        return "medium"
    
    def _generate_recommendations(
        self,
        is_public: bool,
        is_writable: bool,
        provider: str,
        files_found: List[str] = None
    ) -> List[str]:
        """Generate security recommendations.
        
        Args:
            is_public: Whether bucket is public
            is_writable: Whether bucket is writable
            provider: Cloud provider
            files_found: List of files
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        if is_public:
            recommendations.append(
                f"Bucket is publicly accessible. Review if this is intentional."
            )
            
            if provider == "aws_s3":
                recommendations.append(
                    "Consider enabling AWS S3 Block Public Access settings."
                )
                recommendations.append(
                    "Review bucket ACL and bucket policies for AllUsers grants."
                )
            elif provider == "gcp_gcs":
                recommendations.append(
                    "Check IAM policy for 'allUsers' or 'allAuthenticatedUsers' members."
                )
                recommendations.append(
                    "Consider using signed URLs for temporary access instead."
                )
            elif provider == "azure_blob":
                recommendations.append(
                    "Change container public access level to 'Private'."
                )
                recommendations.append(
                    "Use Shared Access Signatures (SAS) for controlled access."
                )
        
        if is_writable:
            recommendations.append(
                "⚠️ CRITICAL: Bucket has public write access! This allows anyone to upload/modify files."
            )
            recommendations.append(
                "Immediately remove public write permissions."
            )
        
        if files_found and len(files_found) > 0:
            recommendations.append(
                f"Found {len(files_found)} accessible files. Review for sensitive data."
            )
        
        if not recommendations:
            recommendations.append("Bucket appears to be properly secured.")
        
        return recommendations
