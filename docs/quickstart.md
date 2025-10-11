# Quickstart

This guide shows how to get the middlewares running quickly in a FastAPI app.

## 1) Create the app and configure providers

```python
from fastapi import FastAPI, Request
from os_fastapi_middleware.middleware import (
    APIKeyMiddleware,
    RateLimitMiddleware,
    IPWhitelistMiddleware,
)
from os_fastapi_middleware.providers import (
    InMemoryAPIKeyProvider,
    InMemoryRateLimitProvider,
    InMemoryIPWhitelistProvider,
)

app = FastAPI(title="My Secure API")

api_key_provider = InMemoryAPIKeyProvider(valid_keys={
    "secret-key-123": {"user": "john", "tier": "premium"},
    "secret-key-456": {"user": "jane", "tier": "basic"},
})

rate_limit_provider = InMemoryRateLimitProvider()

ip_whitelist_provider = InMemoryIPWhitelistProvider(allowed_ips=[
    "127.0.0.1",
    "192.168.1.0/24",
])

# Order matters: last added = first executed
app.add_middleware(
    RateLimitMiddleware,
    provider=rate_limit_provider,
    requests_per_window=100,
    window_seconds=60,
)

app.add_middleware(
    APIKeyMiddleware,
    provider=api_key_provider,
    include_metadata=True,  # injects metadata into request.state.api_key_metadata
)

app.add_middleware(
    IPWhitelistMiddleware,
    provider=ip_whitelist_provider,
)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/secure")
async def secure_endpoint(request: Request):
    metadata = request.state.api_key_metadata  # provided by APIKeyMiddleware
    return {"message": f"Hello {metadata['user']}"}
```

Run with Uvicorn:

```bash
uvicorn main:app --reload
```

## 2) Making requests

- API Key: send header `X-API-Key: secret-key-123` (or another you configured)
- IP Whitelist: allow IPs or networks (CIDR) in the provider
- Rate Limit: observe response headers:
  - `X-RateLimit-Limit`: window limit
  - `X-RateLimit-Remaining`: remaining in current window
  - `X-RateLimit-Reset`: seconds until reset

Example with curl:

```bash
curl -H "X-API-Key: secret-key-123" http://127.0.0.1:8000/secure
```

## 3) Quick tests with httpx

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_secure(client_app):
    from main import app  # your app
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/secure", headers={"X-API-Key": "secret-key-123"})
        assert r.status_code == 200
        assert "Hello" in r.json()["message"]
```

## Next steps

- Read docs/advanced.md for advanced configurations (proxies, Redis, custom providers, selective routes)