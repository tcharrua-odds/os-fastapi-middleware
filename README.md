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
    "secret-key-123": {"user": "john", "tier": "premium"}
})
rate_limit_provider = InMemoryRateLimitProvider()
ip_whitelist_provider = InMemoryIPWhitelistProvider(allowed_ips=["127.0.0.1"]) 

app.add_middleware(RateLimitMiddleware, provider=rate_limit_provider, requests_per_window=100, window_seconds=60)
app.add_middleware(APIKeyMiddleware, provider=api_key_provider, include_metadata=True)
app.add_middleware(IPWhitelistMiddleware, provider=ip_whitelist_provider)

@app.get("/secure")
async def secure(request: Request):
    return {"hello": request.state.api_key_metadata["user"]}
```

More examples in examples/.

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
