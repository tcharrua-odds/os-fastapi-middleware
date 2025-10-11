"""FastAPI Security Middleware - Biblioteca de segurança adaptável."""

from .middleware.api_key import APIKeyMiddleware
from .middleware.rate_limit import RateLimitMiddleware
from .middleware.ip_whitelist import IPWhitelistMiddleware

from .dependencies.api_key import APIKeyDependency
from .dependencies.rate_limit import RateLimitDependency
from .dependencies.ip_whitelist import IPWhitelistDependency

from .providers.base import (
    BaseAPIKeyProvider,
    BaseRateLimitProvider,
    BaseIPWhitelistProvider
)

from .providers.memory import (
    InMemoryAPIKeyProvider,
    InMemoryRateLimitProvider,
    InMemoryIPWhitelistProvider
)

from .exceptions import (
    SecurityException,
    UnauthorizedException,
    ForbiddenException,
    RateLimitExceededException,
    IPNotAllowedException
)

from .config import (
    SecurityConfig,
    APIKeyConfig,
    RateLimitConfig,
    IPWhitelistConfig
)

__version__ = "1.0.0"

__all__ = [
    # Middlewares
    "APIKeyMiddleware",
    "RateLimitMiddleware",
    "IPWhitelistMiddleware",
    
    # Dependencies
    "APIKeyDependency",
    "RateLimitDependency",
    "IPWhitelistDependency",
    
    # Providers Base
    "BaseAPIKeyProvider",
    "BaseRateLimitProvider",
    "BaseIPWhitelistProvider",
    
    # Providers In-Memory
    "InMemoryAPIKeyProvider",
    "InMemoryRateLimitProvider",
    "InMemoryIPWhitelistProvider",
    
    # Exceptions
    "SecurityException",
    "UnauthorizedException",
    "ForbiddenException",
    "RateLimitExceededException",
    "IPNotAllowedException",
    
    # Config
    "SecurityConfig",
    "APIKeyConfig",
    "RateLimitConfig",
    "IPWhitelistConfig",
]