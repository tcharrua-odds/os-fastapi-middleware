import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from os_fastapi_middleware import (
    AdminIPBypassMiddleware,
    APIKeyMiddleware,
    RateLimitMiddleware,
    InMemoryAPIKeyProvider,
    InMemoryRateLimitProvider,
    AdminIPBypassDependency,
    APIKeyDependency,
    InMemoryIPWhitelistProvider,
)

ADMIN_IP = "203.0.113.10"
NON_ADMIN_IP = "198.51.100.23"


def build_middleware_app():
    app = FastAPI()

    api_key_provider = InMemoryAPIKeyProvider({"acct": "valid-key"})
    rate_limit_provider = InMemoryRateLimitProvider()

    app.add_middleware(APIKeyMiddleware, provider=api_key_provider, header_name="X-API-Key")
    app.add_middleware(RateLimitMiddleware, provider=rate_limit_provider, requests_per_window=2, window_seconds=60)
    app.add_middleware(AdminIPBypassMiddleware, admin_ips=[ADMIN_IP], trust_proxy_headers=True)

    @app.get("/")
    async def root():
        return {"ok": True}

    return app


def build_dependency_app():
    app = FastAPI()

    api_key_provider = InMemoryAPIKeyProvider({"acct": "valid-key"})

    admin_dep = AdminIPBypassDependency(admin_ips=[ADMIN_IP], auto_error=False)
    api_key_dep = APIKeyDependency(api_key_provider, header_name="X-API-Key", auto_error=True)

    @app.get("/")
    async def root(_admin: bool = Depends(admin_dep), _api: str = Depends(api_key_dep)):
        return {"ok": True}

    return app


def test_admin_state_not_persisted_across_requests_middleware():
    app = build_middleware_app()
    client = TestClient(app)

    # First request as admin should pass without API key
    assert client.get("/", headers={"X-Real-IP": ADMIN_IP}).status_code == 200

    # Next request from non-admin without API key should NOT inherit admin and should be 401
    r = client.get("/", headers={"X-Real-IP": NON_ADMIN_IP})
    assert r.status_code == 401


def test_admin_state_not_persisted_across_requests_dependency():
    app = build_dependency_app()
    client = TestClient(app)

    # First request as admin should pass without API key
    assert client.get("/", headers={"X-Real-IP": ADMIN_IP}).status_code == 200

    # Next request from non-admin without API key should be 401
    r = client.get("/", headers={"X-Real-IP": NON_ADMIN_IP})
    assert r.status_code == 401
