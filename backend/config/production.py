"""Production configuration for FinTradeAgent backend."""

import os
from typing import List, Optional
from pydantic import BaseSettings, validator
from functools import lru_cache


class ProductionSettings(BaseSettings):
    """Production-specific settings with security hardening."""
    
    # Application Configuration
    app_name: str = "FinTradeAgent API"
    app_version: str = "1.0.0"
    app_env: str = "production"
    debug: bool = False
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    reload: bool = False
    
    # Database Configuration
    database_url: str
    database_pool_min_size: int = 10
    database_pool_max_size: int = 20
    database_pool_timeout: int = 30
    database_ssl_mode: str = "require"
    
    # Redis Configuration
    redis_url: str = "redis://redis:6379/0"
    redis_pool_min_size: int = 5
    redis_pool_max_size: int = 10
    
    # Security Configuration
    secret_key: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60
    allowed_hosts: List[str] = ["api.fintradeagent.com", "fintradeagent.com"]
    cors_origins: List[str] = [
        "https://fintradeagent.com",
        "https://www.fintradeagent.com"
    ]
    
    # SSL/TLS Configuration
    ssl_redirect: bool = True
    secure_ssl_redirect: bool = True
    secure_proxy_ssl_header: str = "HTTP_X_FORWARDED_PROTO,https"
    secure_hsts_seconds: int = 31536000
    secure_hsts_include_subdomains: bool = True
    secure_hsts_preload: bool = True
    
    # Rate Limiting Configuration
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_period: int = 60
    rate_limit_storage: str = "redis://redis:6379/1"
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: str = "/var/log/fintradeagent/app.log"
    log_max_size: str = "100MB"
    log_backup_count: int = 5
    sentry_dsn: Optional[str] = None
    
    # Performance Configuration
    cache_ttl: int = 3600
    cache_enabled: bool = True
    gzip_enabled: bool = True
    gzip_minimum_size: int = 1000
    compression_level: int = 6
    
    # External API Configuration
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    alpha_vantage_api_key: Optional[str] = None
    yahoo_finance_enabled: bool = True
    
    # Monitoring Configuration
    health_check_enabled: bool = True
    metrics_enabled: bool = True
    performance_monitoring: bool = True
    async_worker_pool_size: int = 20
    
    # WebSocket Configuration
    websocket_heartbeat_interval: int = 30
    websocket_timeout: int = 300
    websocket_max_connections: int = 1000
    
    # Background Tasks
    celery_broker_url: str = "redis://redis:6379/2"
    celery_result_backend: str = "redis://redis:6379/3"
    celery_worker_processes: int = 2
    
    # File Storage Configuration
    storage_path: str = "/var/lib/fintradeagent"
    static_files_path: str = "/var/www/fintradeagent/static"
    max_upload_size: int = 10485760  # 10MB
    
    # Backup Configuration
    backup_enabled: bool = True
    backup_schedule: str = "0 2 * * *"  # Daily at 2 AM
    backup_retention_days: int = 30
    
    @validator('cors_origins', pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    @validator('allowed_hosts', pre=True)
    def parse_allowed_hosts(cls, v):
        """Parse allowed hosts from comma-separated string."""
        if isinstance(v, str):
            return [host.strip() for host in v.split(',')]
        return v
    
    @validator('secret_key', 'jwt_secret_key')
    def validate_secrets(cls, v):
        """Ensure secrets are provided and have minimum length."""
        if not v or len(v) < 32:
            raise ValueError("Secret keys must be at least 32 characters long")
        return v
    
    @property
    def database_config(self) -> dict:
        """Database connection configuration."""
        return {
            "url": self.database_url,
            "min_size": self.database_pool_min_size,
            "max_size": self.database_pool_max_size,
            "timeout": self.database_pool_timeout,
            "ssl": self.database_ssl_mode,
        }
    
    @property
    def redis_config(self) -> dict:
        """Redis connection configuration."""
        return {
            "url": self.redis_url,
            "min_size": self.redis_pool_min_size,
            "max_size": self.redis_pool_max_size,
        }
    
    @property
    def security_headers(self) -> dict:
        """Security headers for production."""
        return {
            "Strict-Transport-Security": f"max-age={self.secure_hsts_seconds}; "
                                       f"includeSubDomains{'; preload' if self.secure_hsts_preload else ''}",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' wss: https:;"
            )
        }
    
    class Config:
        env_file = ".env.production"
        case_sensitive = False


@lru_cache()
def get_production_settings() -> ProductionSettings:
    """Get cached production settings."""
    return ProductionSettings()


# Export settings instance
production_settings = get_production_settings()