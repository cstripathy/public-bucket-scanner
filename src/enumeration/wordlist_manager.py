"""Wordlist management for bucket name enumeration."""
from pathlib import Path
from typing import List, Optional
import structlog

logger = structlog.get_logger()


class WordlistManager:
    """Manage and load wordlists for bucket enumeration."""
    
    def __init__(self, wordlist_dir: Optional[str] = None):
        """Initialize wordlist manager.
        
        Args:
            wordlist_dir: Directory containing wordlist files
        """
        if wordlist_dir is None:
            # Default to wordlists/ in project root
            wordlist_dir = Path(__file__).parent.parent.parent / "wordlists"
        
        self.wordlist_dir = Path(wordlist_dir)
        self.wordlist_dir.mkdir(exist_ok=True)
        
    def load_wordlist(self, name: str) -> List[str]:
        """Load a wordlist by name.
        
        Args:
            name: Wordlist name (without .txt extension)
            
        Returns:
            List of words from wordlist
        """
        wordlist_path = self.wordlist_dir / f"{name}.txt"
        
        if not wordlist_path.exists():
            logger.warning("wordlist_not_found", path=str(wordlist_path))
            return []
            
        try:
            with open(wordlist_path, 'r') as f:
                words = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.startswith('#')
                ]
                
            logger.info(
                "wordlist_loaded",
                name=name,
                count=len(words)
            )
            return words
            
        except Exception as e:
            logger.error(
                "wordlist_load_failed",
                name=name,
                error=str(e)
            )
            return []
    
    def load_multiple(self, names: List[str]) -> List[str]:
        """Load and combine multiple wordlists.
        
        Args:
            names: List of wordlist names
            
        Returns:
            Combined and deduplicated list of words
        """
        all_words = []
        
        for name in names:
            words = self.load_wordlist(name)
            all_words.extend(words)
            
        # Remove duplicates while preserving order
        seen = set()
        unique_words = []
        for word in all_words:
            if word not in seen:
                seen.add(word)
                unique_words.append(word)
                
        return unique_words
    
    def get_available_wordlists(self) -> List[str]:
        """Get list of available wordlist names.
        
        Returns:
            List of wordlist names (without .txt)
        """
        try:
            wordlists = [
                f.stem
                for f in self.wordlist_dir.glob("*.txt")
            ]
            return sorted(wordlists)
        except Exception as e:
            logger.error("failed_to_list_wordlists", error=str(e))
            return []
    
    def create_wordlist(self, name: str, words: List[str]) -> bool:
        """Create a new wordlist file.
        
        Args:
            name: Wordlist name
            words: List of words to write
            
        Returns:
            True if successful
        """
        try:
            wordlist_path = self.wordlist_dir / f"{name}.txt"
            
            with open(wordlist_path, 'w') as f:
                f.write("# Bucket name wordlist\n")
                f.write(f"# Generated wordlist: {name}\n\n")
                for word in words:
                    f.write(f"{word}\n")
                    
            logger.info(
                "wordlist_created",
                name=name,
                count=len(words)
            )
            return True
            
        except Exception as e:
            logger.error(
                "wordlist_creation_failed",
                name=name,
                error=str(e)
            )
            return False
    
    def get_common_patterns(self) -> List[str]:
        """Get built-in common bucket name patterns.
        
        Returns:
            List of common patterns
        """
        return [
            # Data storage
            "backup", "backups", "data", "storage", "archive",
            "files", "documents", "docs", "assets", "resources",
            
            # Media
            "images", "img", "photos", "media", "videos",
            "uploads", "downloads", "attachments",
            
            # Web
            "static", "public", "cdn", "website", "web", "www",
            
            # Application
            "app", "application", "api", "service", "code",
            
            # Logs and reports
            "logs", "logging", "reports", "analytics", "metrics",
            
            # Database
            "db", "database", "dumps", "exports", "snapshots",
            
            # Temporary
            "temp", "tmp", "cache", "staging",
            
            # Security
            "private", "internal", "confidential", "secure",
            
            # Development
            "dev", "development", "test", "testing", "qa",
            "prod", "production", "live",
            
            # Customer data
            "customer", "customers", "user", "users", "client", "clients"
        ]
