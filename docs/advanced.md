# Advanced

This guide covers more elaborate scenarios: selective routes, custom providers, proxy support, Redis for distributed rate limiting, and useful tips.

## Selective routes (apply rules per endpoint)

Besides global middlewares, you can enforce checks per route using dependencies. The library exposes similar helpers in `os_fastapi_middleware.dependencies`.

Simple example of API Key check per route:

```python
from fastapi import FastAPI, Depends, Header, HTTPException, status
from os_fastapi_middleware.providers import InMemoryAPIKeyProvider

app = FastAPI()
api_key_provider = InMemoryAPIKeyProvider(valid_keys={"account_u": "k"})

async def require_api_key(x_api_key: str = Header(None)):
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")
    is_valid = await api_key_provider.validate_key(x_api_key)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    meta = await api_key_provider.get_key_metadata(x_api_key)
    return meta

@app.get("/only-this-route")
async def only_this_route(meta = Depends(require_api_key)):
    return {"ok": True, "account_id": meta.get("account_id")}
```

See also examples/selective_routes.py for a more complete approach.

## Custom providers

Implement your data sources by inheriting the base classes in `os_fastapi_middleware.providers`.

### API Key Provider

```python
from os_fastapi_middleware.providers import BaseAPIKeyProvider

class MyAPIKeyProvider(BaseAPIKeyProvider):
    async def validate_key(self, key: str) -> bool:
        # Validate if key exists
        if key == "prod-key":
            return True
        return False
    
    async def get_key_metadata(self, key: str) -> dict:
        # Return account_id for the key
        if key == "prod-key":
            return {"account_id": "account_alice"}
        return None
```

### IP Whitelist Provider

```python
from os_fastapi_middleware.providers import BaseIPWhitelistProvider

class MyIPWhitelistProvider(BaseIPWhitelistProvider):
    async def is_allowed(self, ip: str) -> bool:
        # Support IP or CIDR: 10.0.0.0/8, 192.168.1.0/24 etc.
        # Put your logic here (DB, cache, etc.)
        return ip.startswith("10.")
```

### Rate Limit Provider

```python
from os_fastapi_middleware.providers import BaseRateLimitProvider

class MyRateLimitProvider(BaseRateLimitProvider):
    async def check_rate_limit(self, *, key: str, limit: int, window_seconds: int) -> bool:
        # Return True if within limit; False if exceeded
        return True
```

Then pass your implementations when adding the middlewares:

```python
app.add_middleware(APIKeyMiddleware, provider=MyAPIKeyProvider())
app.add_middleware(IPWhitelistMiddleware, provider=MyIPWhitelistProvider())
app.add_middleware(RateLimitMiddleware, provider=MyRateLimitProvider(), requests_per_window=100, window_seconds=60)
```

## Working behind proxies (X-Forwarded-For)

`IPWhitelistMiddleware` can read proxy headers if you trust them. Enable via `trust_proxy_headers=True` (default True). If disabled, the middleware uses `request.client.host` and normalizes non-IP values to `127.0.0.1` in test environments.

```python
app.add_middleware(
    IPWhitelistMiddleware,
    provider=ip_whitelist_provider,
    trust_proxy_headers=True,  # trust proxy headers
)
```

Ensure your proxy (Nginx, Traefik, etc.) is configured to send `X-Forwarded-For` correctly.

## Redis for distributed Rate Limit

For multi-instance environments, use the Redis provider.

Install the extra:

```bash
pip install os-fastapi-middleware[redis]
```

Usage:

```python
from os_fastapi_middleware.providers import RedisRateLimitProvider

rate_limit_provider = RedisRateLimitProvider(redis_url="redis://localhost:6379/0")

app.add_middleware(
    RateLimitMiddleware,
    provider=rate_limit_provider,
    requests_per_window=100,
    window_seconds=60,
)
```

Initialize and close in the app lifecycle:

```python
@app.on_event("startup")
async def on_startup():
    await rate_limit_provider.init()

@app.on_event("shutdown")
async def on_shutdown():
    await rate_limit_provider.close()
```

## Rate Limit headers

`RateLimitMiddleware` adds the following headers to the response:
- `X-RateLimit-Limit`: total allowed per window
- `X-RateLimit-Remaining`: remaining in the current window
- `X-RateLimit-Reset`: seconds until reset

When the limit is exceeded, response is 429 Too Many Requests with a descriptive JSON body.

## Whitelist via CIDR

`InMemoryIPWhitelistProvider` and custom providers may accept CIDR networks, e.g.: `"10.0.0.0/8"`, `"192.168.1.0/24"`. Mix with individual IPs as needed.

```python
ip_whitelist_provider = InMemoryIPWhitelistProvider(
    allowed_ips=["127.0.0.1", "10.0.0.0/8", "192.168.1.0/24"]
)
```

## Production tips

- Log invalid API key attempts and IP blocks
- Use HTTPS and rotate your keys regularly
- For Redis, configure timeouts and authentication
- Ensure only trusted proxies can set `X-Forwarded-For`
