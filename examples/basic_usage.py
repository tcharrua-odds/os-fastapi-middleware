from os_fastapi_middleware import InMemoryAPIKeyProvider, InMemoryRateLimitProvider, InMemoryIPWhitelistProvider, \
    RateLimitMiddleware, APIKeyMiddleware, IPWhitelistMiddleware

from fastapi import FastAPI, Request

# Create FastAPI app
app = FastAPI(title="My Secure API")

# Configure providers
api_key_provider = InMemoryAPIKeyProvider(
    valid_keys={
        "account_123": "secret-key-123",
        "account_456": "secret-key-456",
    }
)

rate_limit_provider = InMemoryRateLimitProvider()

ip_whitelist_provider = InMemoryIPWhitelistProvider(
    allowed_ips=["127.0.0.1", "192.168.1.0/24"]
)

# Add middlewares (order matters: last added = first executed)
app.add_middleware(
    RateLimitMiddleware,
    provider=rate_limit_provider,
    requests_per_window=100,
    window_seconds=60
)

app.add_middleware(
    APIKeyMiddleware,
    provider=api_key_provider,
    include_metadata=True
)

app.add_middleware(
    IPWhitelistMiddleware,
    provider=ip_whitelist_provider
)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/secure")
async def secure_endpoint(request: Request):
    # Access metadata from middleware
    metadata = request.state.api_key_metadata
    return {"message": f"Hello, account: {metadata['account_id']}"}
