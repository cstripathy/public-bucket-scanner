"""Application configuration settings."""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Application
    app_name: str = "Bucket Scanner"
    debug: bool = False
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    
    # Database
    postgres_user: str = "scanner"
    postgres_password: str = ""  # Set via environment variable
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "bucket_scanner"
    
    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    
    @property
    def redis_url(self) -> str:
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    # Kafka (for future enhancement)
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_topic: str = "bucket-scan-tasks"
    
    # Rate Limiting
    max_requests_per_second: int = 10
    max_concurrent_workers: int = 50
    request_timeout: int = 10
    
    # Scanner Configuration
    dns_timeout: int = 5
    http_timeout: int = 10
    max_retries: int = 3
    
    # Proxy Configuration (optional)
    use_proxy: bool = False
    proxy_list: List[str] = []
    rotate_proxy: bool = False
    
    # Notification Configuration
    enable_notifications: bool = False
    webhook_url: str = ""
    slack_webhook: str = ""
    
    # AWS Configuration
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    
    # GCP Configuration
    gcp_project_id: str = ""
    gcp_credentials_path: str = ""
    
    # Azure Configuration
    azure_connection_string: str = ""
    azure_account_name: str = ""
    azure_account_key: str = ""


# Global settings instance
settings = Settings()
