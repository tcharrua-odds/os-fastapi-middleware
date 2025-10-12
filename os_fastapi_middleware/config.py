from typing import List, Optional
from pydantic import BaseModel, Field


class APIKeyConfig(BaseModel):
    
    header_name: str = Field(default="X-API-Key", description="Nome do header da API key")
    exempt_paths: List[str] = Field(
        default=["/health", "/docs", "/redoc", "/openapi.json"],
        description="Paths that don't require an API key"
    )
    include_metadata: bool = Field(
        default=False,
        description="If true, include metadata in request state"
    )


class RateLimitConfig(BaseModel):
    
    requests_per_window: int = Field(
        default=100,
        description="Number of requests allowed per window"
    )
    window_seconds: int = Field(
        default=60,
        description="Window size in seconds"
    )
    exempt_paths: List[str] = Field(
        default=["/health", "/docs", "/redoc", "/openapi.json"],
        description="Paths without rate limit"
    )
    add_headers: bool = Field(
        default=True,
        description="If true add rate limit headers X-RateLimit-*"
    )
    key_prefix: str = Field(
        default="rate_limit",
        description="Prefix for rate limit keys"
    )


class IPWhitelistConfig(BaseModel):
    
    allowed_ips: List[str] = Field(
        default=[],
        description="Allowed IP addresses (supports CIDR)"
    )
    exempt_paths: List[str] = Field(
        default=["/health", "/docs", "/redoc", "/openapi.json"],
        description="Paths without IP whitelist"
    )
    trust_proxy_headers: bool = Field(
        default=True,
        description="If true trust X-Forwarded-For and X-Real-IP headers"
    )
    block_on_error: bool = Field(
        default=True,
        description="If true block IP on error"
    )


class SecurityConfig(BaseModel):
    
    api_key: Optional[APIKeyConfig] = None
    rate_limit: Optional[RateLimitConfig] = None
    ip_whitelist: Optional[IPWhitelistConfig] = None
    
    @classmethod
    def from_env(cls):
        import os
        
        config = cls()

        if os.getenv("SECURITY_API_KEY_ENABLED", "false").lower() == "true":
            config.api_key = APIKeyConfig(
                header_name=os.getenv("SECURITY_API_KEY_HEADER", "X-API-Key"),
                include_metadata=os.getenv("SECURITY_API_KEY_INCLUDE_METADATA", "false").lower() == "true"
            )

        if os.getenv("SECURITY_RATE_LIMIT_ENABLED", "false").lower() == "true":
            config.rate_limit = RateLimitConfig(
                requests_per_window=int(os.getenv("SECURITY_RATE_LIMIT_REQUESTS", "100")),
                window_seconds=int(os.getenv("SECURITY_RATE_LIMIT_WINDOW", "60"))
            )

        if os.getenv("SECURITY_IP_WHITELIST_ENABLED", "false").lower() == "true":
            allowed_ips = os.getenv("SECURITY_ALLOWED_IPS", "").split(",")
            config.ip_whitelist = IPWhitelistConfig(
                allowed_ips=[ip.strip() for ip in allowed_ips if ip.strip()]
            )
        
        return config