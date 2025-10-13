# OS FastAPI Middlewares

Simple and adaptable: production-ready security middlewares for FastAPI, including API Key, Rate Limit, and IP Whitelist. Plug in in-memory or Redis providers, or implement your own.

- API Key: validates a key from the request, optionally injects metadata into request.state
- Rate Limit: enforces requests per time window and adds X-RateLimit-* headers
- IP Whitelist: allows only approved IPs or networks (supports CIDR)

Docs: see docs/installation.md, docs/quickstart.md, and docs/advanced.md.

## Installation

- Basic: `pip install os-fastapi-middleware`
- With Redis (optional): `pip install os-fastapi-middleware[redis]`

Requirements: Python >= 3.8, FastAPI >= 0.100, Starlette >= 0.27.

## Quick example

```python
from fastapi import FastAPI, Request
from os_fastapi_middleware.middleware import APIKeyMiddleware, RateLimitMiddleware, IPWhitelistMiddleware
from os_fastapi_middleware.providers import (
    InMemoryAPIKeyProvider,
    InMemoryRateLimitProvider,
    InMemoryIPWhitelistProvider,
)

app = FastAPI()

api_key_provider = InMemoryAPIKeyProvider(valid_keys={
    "account_123": "secret-key-123"
})
rate_limit_provider = InMemoryRateLimitProvider()
ip_whitelist_provider = InMemoryIPWhitelistProvider(allowed_ips=["127.0.0.1"]) 

app.add_middleware(RateLimitMiddleware, provider=rate_limit_provider, requests_per_window=100, window_seconds=60)
app.add_middleware(APIKeyMiddleware, provider=api_key_provider, include_metadata=True)
app.add_middleware(IPWhitelistMiddleware, provider=ip_whitelist_provider)

@app.get("/secure")
async def secure(request: Request):
    return {"hello": request.state.api_key_metadata["account_id"]}
```

More examples in examples/.

## Per-route or route group usage

You can also apply validations selectively to specific routes or route groups using dependencies:

```python
from fastapi import FastAPI, Depends, Request
from os_fastapi_middleware.dependencies import APIKeyDependency, RateLimitDependency, IPWhitelistDependency
from os_fastapi_middleware.providers import (
    InMemoryAPIKeyProvider,
    InMemoryRateLimitProvider,
    InMemoryIPWhitelistProvider,
)

app = FastAPI()

# Configure providers
api_key_provider = InMemoryAPIKeyProvider(valid_keys={"account_123": "secret-key-123"})
rate_limit_provider = InMemoryRateLimitProvider()
ip_whitelist_provider = InMemoryIPWhitelistProvider(allowed_ips=["127.0.0.1"])

# Create dependency instances
api_key_dep = APIKeyDependency(provider=api_key_provider)
rate_limit_dep = RateLimitDependency(provider=rate_limit_provider, requests_per_window=10, window_seconds=60)
ip_whitelist_dep = IPWhitelistDependency(provider=ip_whitelist_provider)

# Public route - no validation
@app.get("/public")
async def public():
    return {"message": "This is public"}

# Protected route - API key only
@app.get("/protected", dependencies=[Depends(api_key_dep)])
async def protected():
    return {"message": "API key validated"}

# Strict route - multiple validations
@app.get("/admin", dependencies=[Depends(ip_whitelist_dep), Depends(api_key_dep), Depends(rate_limit_dep)])
async def admin():
    return {"message": "Admin area with all protections"}

# Route group with shared dependencies
from fastapi import APIRouter
api_router = APIRouter(prefix="/api", dependencies=[Depends(api_key_dep)])

@api_router.get("/data")
async def get_data():
    return {"data": "protected by API key"}

@api_router.get("/stats")
async def get_stats():
    return {"stats": "also protected by API key"}

app.include_router(api_router)
```

See examples/selective_routes.py for more details.

## Key features

- Pluggable providers: in-memory, Redis, and base classes to customize
- Clear configuration: sensible, named parameters
- Rate limit headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
- Works behind proxies (X-Forwarded-For) when enabled

## Tests

Install dev dependencies and run:

```bash
pip install -e .[dev]
pytest -q
```

## License

MIT. See LICENSE if available.
