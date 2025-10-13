import os
import sys
from typing import Optional, Callable

from os_fastapi_middleware import InMemoryAPIKeyProvider, InMemoryRateLimitProvider, InMemoryIPWhitelistProvider

# Allow running the example from the repo without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

app = FastAPI(title="Selective Routes Example")

api_key_provider = InMemoryAPIKeyProvider(
    valid_keys={
        "account_alice": "route-key-123",
        "account_bob": "route-key-456",
    }
)
rate_limit_provider = InMemoryRateLimitProvider()
ip_whitelist_provider = InMemoryIPWhitelistProvider(allowed_ips=["127.0.0.1"])  # Simples


# 1) Dependency: exige API key somente onde aplicada
async def require_api_key(
        request: Request,
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required")

    is_valid = await api_key_provider.validate_key(x_api_key)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")

    # Opcional: anexa metadados ao request.state
    request.state.api_key = x_api_key
    request.state.api_key_metadata = await api_key_provider.get_key_metadata(x_api_key)


# 2) Dependency: rate limit seletivo
async def selective_rate_limit(
        request: Request,
        requests_per_window: int = 5,
        window_seconds: int = 60,
        key_func: Optional[Callable[[Request], str]] = None,
):
    key_func = key_func or (lambda req: f"rl:api_key:{getattr(req.state, 'api_key', 'anon')}" if hasattr(req.state,
                                                                                                         'api_key') else f"rl:ip:{req.client.host if req.client else 'unknown'}")
    key = key_func(request)

    allowed = await rate_limit_provider.check_rate_limit(key, requests_per_window, window_seconds)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Max {requests_per_window}/{window_seconds}s",
        )


# 3) Dependency: IP whitelist seletivo
async def require_whitelisted_ip(request: Request):
    # Confia em X-Forwarded-For se presente; senão usa o client.host
    fwd = request.headers.get("X-Forwarded-For")
    if fwd:
        client_ip = fwd.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else ""

    if not client_ip:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Could not determine client IP")

    allowed = await ip_whitelist_provider.is_ip_allowed(client_ip)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"IP {client_ip} is not whitelisted")


@app.get("/public")
async def public():
    return {"area": "public"}


@app.get("/ip-only", dependencies=[Depends(require_whitelisted_ip)])
async def ip_only():
    return {"ok": True, "policy": "ip-whitelist"}


@app.get("/api-key-only", dependencies=[Depends(require_api_key)])
async def api_key_only(request: Request):
    return {"account_id": request.state.api_key_metadata.get("account_id")}


@app.get(
    "/strict",
    dependencies=[Depends(require_whitelisted_ip), Depends(require_api_key), Depends(selective_rate_limit)],
)
async def strict_endpoint():
    return {"policy": "ip + api-key + rate-limit"}


# Tratador global opcional para HTTPException
@app.exception_handler(HTTPException)
async def http_exc_handler(request: Request, exc: HTTPException):
    # Personalize o payload se quiser
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
