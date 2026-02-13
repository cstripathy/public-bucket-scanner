"""Content analyzer worker for analyzing bucket contents."""
from typing import List, Dict, Any
from dataclasses import dataclass
import re
import structlog

logger = structlog.get_logger()


@dataclass
class ContentAnalysisResult:
    """Result from content analysis."""
    bucket_name: str
    total_files: int
    sensitive_files: List[str]
    file_types: Dict[str, int]
    risk_score: int  # 0-100
    findings: List[Dict[str, Any]]


class ContentAnalyzer:
    """Analyzes bucket contents for sensitive data and security issues."""
    
    # Patterns for sensitive file detection
    SENSITIVE_PATTERNS = {
        'credentials': [
            r'\.env$', r'\.env\.',
            r'secret', r'password', r'passwd',
            r'credential', r'creds',
            r'auth', r'token', r'api[-_]?key',
        ],
        'private_keys': [
            r'\.pem$', r'\.key$', r'\.ppk$',
            r'private[-_]?key', r'id_rsa', r'id_dsa',
            r'\.p12$', r'\.pfx$',
        ],
        'config_files': [
            r'config\.(json|xml|yml|yaml|ini|conf)$',
            r'wp-config\.php$',
            r'settings\.(py|json|xml)$',
            r'\.htaccess$', r'\.htpasswd$',
        ],
        'database': [
            r'\.sql$', r'\.db$', r'\.sqlite',
            r'database', r'backup\.', r'dump\.',
            r'\.mdb$', r'\.accdb$',
        ],
        'source_code': [
            r'\.git/', r'\.svn/', r'\.hg/',
            r'\.env\.local', r'\.env\.production',
        ],
        'cloud_config': [
            r'\.aws/', r'\.azure/', r'\.gcp/',
            r'credentials\.json', r'service[-_]?account',
        ],
        'logs': [
            r'\.log$', r'access_log', r'error_log',
            r'debug\.', r'trace\.',
        ],
    }
    
    def __init__(self):
        """Initialize content analyzer."""
        logger.info("content_analyzer_initialized")
    
    def analyze(
        self,
        bucket_name: str,
        files: List[str]
    ) -> ContentAnalysisResult:
        """Analyze bucket contents for sensitive data.
        
        Args:
            bucket_name: Name of the bucket
            files: List of file paths
            
        Returns:
            Content analysis result
        """
        if not files:
            return ContentAnalysisResult(
                bucket_name=bucket_name,
                total_files=0,
                sensitive_files=[],
                file_types={},
                risk_score=0,
                findings=[]
            )
        
        # Detect sensitive files
        sensitive_files = self._detect_sensitive_files(files)
        
        # Analyze file types
        file_types = self._analyze_file_types(files)
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(files, sensitive_files)
        
        # Generate findings
        findings = self._generate_findings(files, sensitive_files)
        
        result = ContentAnalysisResult(
            bucket_name=bucket_name,
            total_files=len(files),
            sensitive_files=sensitive_files,
            file_types=file_types,
            risk_score=risk_score,
            findings=findings
        )
        
        logger.info(
            "content_analysis_complete",
            bucket=bucket_name,
            total_files=len(files),
            sensitive_count=len(sensitive_files),
            risk_score=risk_score
        )
        
        return result
    
    def _detect_sensitive_files(self, files: List[str]) -> List[str]:
        """Detect potentially sensitive files.
        
        Args:
            files: List of file paths
            
        Returns:
            List of sensitive file paths
        """
        sensitive = []
        
        for file in files:
            file_lower = file.lower()
            
            # Check against all patterns
            for category, patterns in self.SENSITIVE_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, file_lower):
                        sensitive.append(file)
                        break
                if file in sensitive:
                    break
        
        return sensitive
    
    def _analyze_file_types(self, files: List[str]) -> Dict[str, int]:
        """Analyze file types distribution.
        
        Args:
            files: List of file paths
            
        Returns:
            Dictionary mapping file extensions to counts
        """
        file_types = {}
        
        for file in files:
            # Get extension
            if '.' in file:
                ext = file.rsplit('.', 1)[-1].lower()
            else:
                ext = 'no_extension'
            
            file_types[ext] = file_types.get(ext, 0) + 1
        
        return file_types
    
    def _calculate_risk_score(
        self,
        files: List[str],
        sensitive_files: List[str]
    ) -> int:
        """Calculate overall risk score (0-100).
        
        Args:
            files: All files
            sensitive_files: Sensitive files detected
            
        Returns:
            Risk score from 0 to 100
        """
        if not files:
            return 0
        
        score = 0
        
        # Base score for having any public files
        score += 10
        
        # Score based on number of files
        if len(files) > 1000:
            score += 20
        elif len(files) > 100:
            score += 15
        elif len(files) > 10:
            score += 10
        else:
            score += 5
        
        # Score based on sensitive files ratio
        if sensitive_files:
            ratio = len(sensitive_files) / len(files)
            score += int(ratio * 50)
        
        # Bonus for specific high-risk patterns
        high_risk_patterns = [
            'password', 'secret', '.env', 'credential',
            'private', '.key', '.pem', 'id_rsa'
        ]
        
        for file in sensitive_files:
            file_lower = file.lower()
            if any(pattern in file_lower for pattern in high_risk_patterns):
                score += 5  # Add points per high-risk file
        
        # Cap at 100
        return min(score, 100)
    
    def _generate_findings(
        self,
        files: List[str],
        sensitive_files: List[str]
    ) -> List[Dict[str, Any]]:
        """Generate detailed findings.
        
        Args:
            files: All files
            sensitive_files: Sensitive files
            
        Returns:
            List of finding dictionaries
        """
        findings = []
        
        # Group sensitive files by category
        categorized = {}
        for file in sensitive_files:
            file_lower = file.lower()
            for category, patterns in self.SENSITIVE_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, file_lower):
                        if category not in categorized:
                            categorized[category] = []
                        categorized[category].append(file)
                        break
        
        # Create findings for each category
        for category, files_list in categorized.items():
            severity = self._get_category_severity(category)
            
            findings.append({
                'category': category,
                'severity': severity,
                'count': len(files_list),
                'files': files_list[:10],  # Limit to first 10
                'description': self._get_category_description(category)
            })
        
        return findings
    
    def _get_category_severity(self, category: str) -> str:
        """Get severity level for a category.
        
        Args:
            category: Category name
            
        Returns:
            Severity: critical, high, medium, or low
        """
        critical = ['credentials', 'private_keys', 'cloud_config']
        high = ['database', 'config_files']
        medium = ['source_code', 'logs']
        
        if category in critical:
            return 'critical'
        elif category in high:
            return 'high'
        elif category in medium:
            return 'medium'
        else:
            return 'low'
    
    def _get_category_description(self, category: str) -> str:
        """Get description for a category.
        
        Args:
            category: Category name
            
        Returns:
            Description string
        """
        descriptions = {
            'credentials': 'Environment files, secrets, passwords, or API keys detected',
            'private_keys': 'Private cryptographic keys or certificates found',
            'config_files': 'Configuration files that may contain sensitive settings',
            'database': 'Database files, backups, or SQL dumps discovered',
            'source_code': 'Source code repository files or version control data',
            'cloud_config': 'Cloud provider configuration or service account files',
            'logs': 'Log files that may contain sensitive information',
        }
        
        return descriptions.get(category, 'Potentially sensitive files detected')
