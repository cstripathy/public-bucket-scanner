"""Bucket name generation and enumeration strategies."""
import itertools
from typing import List, Set, Optional
import structlog

logger = structlog.get_logger()


class BucketNameGenerator:
    """Generate potential bucket names using various strategies."""
    
    # Common bucket name patterns
    COMMON_PREFIXES = [
        "backup", "backups", "data", "files", "uploads", "downloads",
        "assets", "static", "media", "images", "documents", "docs",
        "storage", "archive", "logs", "reports", "exports", "dumps"
    ]
    
    COMMON_SUFFIXES = [
        "backup", "backups", "data", "files", "prod", "production",
        "dev", "development", "staging", "test", "qa", "uat",
        "public", "private", "internal", "external", "temp", "tmp"
    ]
    
    ENVIRONMENTS = [
        "prod", "production", "dev", "development", "staging",
        "test", "qa", "uat", "demo", "sandbox", "preprod"
    ]
    
    SEPARATORS = ["-", "_", ""]
    
    def __init__(self):
        """Initialize name generator."""
        self.generated_names: Set[str] = set()
        
    def generate_for_company(
        self,
        company_name: str,
        providers: Optional[List[str]] = None,
        max_names: int = 100
    ) -> List[dict]:
        """Generate bucket names for a company.
        
        Args:
            company_name: Company/organization name
            providers: List of cloud providers to generate for
            max_names: Maximum number of names to generate per provider
            
        Returns:
            List of dicts with bucket_name and provider
        """
        if providers is None:
            providers = ["aws_s3", "gcp_gcs", "azure_blob"]
            
        company_clean = self._clean_name(company_name)
        candidates = []
        
        # Strategy 1: Common patterns
        candidates.extend(self._pattern_based(company_clean))
        
        # Strategy 2: Environment-based
        candidates.extend(self._environment_based(company_clean))
        
        # Strategy 3: Purpose-based
        candidates.extend(self._purpose_based(company_clean))
        
        # Strategy 4: Date-based
        candidates.extend(self._date_based(company_clean))
        
        # Remove duplicates and limit
        unique_candidates = list(set(candidates))[:max_names]
        
        # Generate for each provider
        results = []
        for provider in providers:
            for name in unique_candidates:
                results.append({
                    "bucket_name": name,
                    "provider": provider
                })
                
        logger.info(
            "bucket_names_generated",
            company=company_name,
            count=len(results),
            providers=providers
        )
        
        return results
    
    def generate_from_wordlist(
        self,
        company_name: str,
        wordlist: List[str],
        providers: Optional[List[str]] = None,
        max_combinations: int = 200
    ) -> List[dict]:
        """Generate names combining company name with wordlist.
        
        Args:
            company_name: Company/organization name
            wordlist: List of words to combine
            providers: Cloud providers
            max_combinations: Max combinations to generate
            
        Returns:
            List of bucket name candidates
        """
        if providers is None:
            providers = ["aws_s3", "gcp_gcs", "azure_blob"]
            
        company_clean = self._clean_name(company_name)
        candidates = []
        
        # Combine company name with each word
        for word in wordlist[:max_combinations]:
            for sep in self.SEPARATORS[:2]:  # Only - and _
                candidates.append(f"{company_clean}{sep}{word}")
                candidates.append(f"{word}{sep}{company_clean}")
                
        # Limit to max
        unique_candidates = list(set(candidates))[:max_combinations]
        
        results = []
        for provider in providers:
            for name in unique_candidates:
                results.append({
                    "bucket_name": name,
                    "provider": provider
                })
                
        return results
    
    def generate_permutations(
        self,
        base_name: str,
        include_years: bool = True,
        include_environments: bool = True
    ) -> List[str]:
        """Generate permutations of a base name.
        
        Args:
            base_name: Base bucket name
            include_years: Include year suffixes
            include_environments: Include environment names
            
        Returns:
            List of name permutations
        """
        base_clean = self._clean_name(base_name)
        candidates = [base_clean]
        
        # Add environment variations
        if include_environments:
            for env in self.ENVIRONMENTS:
                for sep in ["-", "_", ""]:
                    candidates.append(f"{base_clean}{sep}{env}")
                    candidates.append(f"{env}{sep}{base_clean}")
        
        # Add year variations
        if include_years:
            years = ["2024", "2025", "2026", "2023"]
            for year in years:
                for sep in ["-", "_", ""]:
                    candidates.append(f"{base_clean}{sep}{year}")
                    
        return list(set(candidates))
    
    def _pattern_based(self, company: str) -> List[str]:
        """Generate names using common patterns."""
        names = []
        
        # company-prefix/prefix-company
        for prefix in self.COMMON_PREFIXES[:10]:
            for sep in self.SEPARATORS[:2]:
                names.append(f"{company}{sep}{prefix}")
                names.append(f"{prefix}{sep}{company}")
        
        # company-suffix/suffix-company
        for suffix in self.COMMON_SUFFIXES[:10]:
            for sep in self.SEPARATORS[:2]:
                names.append(f"{company}{sep}{suffix}")
                
        return names
    
    def _environment_based(self, company: str) -> List[str]:
        """Generate environment-specific names."""
        names = []
        
        for env in self.ENVIRONMENTS:
            for sep in ["-", "_"]:
                # company-env
                names.append(f"{company}{sep}{env}")
                # company-env-data
                names.append(f"{company}{sep}{env}{sep}data")
                # company-env-backup
                names.append(f"{company}{sep}{env}{sep}backup")
                
        return names
    
    def _purpose_based(self, company: str) -> List[str]:
        """Generate purpose-specific names."""
        purposes = [
            "data", "backup", "uploads", "files", "logs",
            "assets", "media", "static", "public", "private"
        ]
        
        names = []
        for purpose in purposes:
            for sep in ["-", "_"]:
                names.append(f"{company}{sep}{purpose}")
                
                # With environment
                for env in ["prod", "dev", "staging"]:
                    names.append(f"{company}{sep}{env}{sep}{purpose}")
                    names.append(f"{company}{sep}{purpose}{sep}{env}")
                    
        return names
    
    def _date_based(self, company: str) -> List[str]:
        """Generate date-based bucket names."""
        names = []
        years = ["2024", "2025", "2026"]
        months = ["01", "06", "12"]
        
        for year in years:
            for sep in ["-", "_"]:
                # company-year
                names.append(f"{company}{sep}{year}")
                # company-backup-year
                names.append(f"{company}{sep}backup{sep}{year}")
                
                # Monthly backups
                for month in months:
                    names.append(f"{company}{sep}backup{sep}{year}{month}")
                    
        return names
    
    def _clean_name(self, name: str) -> str:
        """Clean and normalize company/bucket name.
        
        Args:
            name: Raw name
            
        Returns:
            Cleaned name (lowercase, alphanumeric + hyphens)
        """
        # Convert to lowercase
        clean = name.lower()
        
        # Replace spaces and special chars with hyphens
        clean = clean.replace(" ", "-")
        clean = clean.replace("_", "-")
        clean = "".join(c for c in clean if c.isalnum() or c == "-")
        
        # Remove multiple consecutive hyphens
        while "--" in clean:
            clean = clean.replace("--", "-")
            
        # Remove leading/trailing hyphens
        clean = clean.strip("-")
        
        return clean
    
    def generate_common_public_buckets(self) -> List[dict]:
        """Generate commonly found public bucket names.
        
        Returns:
            List of common public bucket patterns
        """
        common_patterns = [
            "backup", "backups", "data", "public", "files",
            "uploads", "downloads", "static", "assets", "media",
            "website", "web", "www", "site", "images", "img",
            "documents", "docs", "archive", "temp", "tmp"
        ]
        
        results = []
        providers = ["aws_s3", "gcp_gcs", "azure_blob"]
        
        for pattern in common_patterns:
            for provider in providers:
                results.append({
                    "bucket_name": pattern,
                    "provider": provider
                })
                
                # Add with common suffixes
                for suffix in ["prod", "dev", "public"]:
                    results.append({
                        "bucket_name": f"{pattern}-{suffix}",
                        "provider": provider
                    })
                    
        return results
