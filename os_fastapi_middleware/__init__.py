"""FastAPI Security Middleware - Biblioteca de segurança adaptável."""
from os_fastapi_middleware.providers.base import (
    BaseAPIKeyProvider,
    BaseRateLimitProvider,
    BaseIPWhitelistProvider,
    BaseRequestLogProvider,
)
from os_fastapi_middleware.providers.memory import (
    InMemoryAPIKeyProvider,
    InMemoryRateLimitProvider,
    InMemoryIPWhitelistProvider
)
from .config import (
    SecurityConfig,
    APIKeyConfig,
    RateLimitConfig,
    IPWhitelistConfig
)
from .dependencies.api_key import APIKeyDependency
from .dependencies.ip_whitelist import IPWhitelistDependency
from .dependencies.rate_limit import RateLimitDependency
from .exceptions import (
    SecurityException,
    UnauthorizedException,
    ForbiddenException,
    RateLimitExceededException,
    IPNotAllowedException
)
from .middleware.api_key import APIKeyMiddleware
from .middleware.ip_whitelist import IPWhitelistMiddleware
from .middleware.rate_limit import RateLimitMiddleware
from .middleware.request_logger import RequestLoggingMiddleware

__version__ = "1.1.1"

__all__ = [
    # Middlewares
    "APIKeyMiddleware",
    "RateLimitMiddleware",
    "IPWhitelistMiddleware",
    "RequestLoggingMiddleware",

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
