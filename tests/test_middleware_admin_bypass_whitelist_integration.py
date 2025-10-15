import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from os_fastapi_middleware import (
    AdminIPBypassMiddleware,
    IPWhitelistMiddleware,
    APIKeyMiddleware,
    InMemoryIPWhitelistProvider,
    InMemoryAPIKeyProvider,
)

ADMIN_IP = "127.0.0.1"
NON_ADMIN_IP = "198.51.100.23"
WHITELISTED_IP = "203.0.113.10"


@pytest.fixture()
def make_app():
    def _factory():
        app = FastAPI()

        # Providers: whitelist does NOT include NON_ADMIN_IP nor ADMIN_IP
        whitelist_provider = InMemoryIPWhitelistProvider([WHITELISTED_IP])
        api_key_provider = InMemoryAPIKeyProvider({"acct": "valid-key"})

        # Add middlewares so that Admin runs first, then whitelist, then API key
        # (Starlette executes in reverse order of addition)
        app.add_middleware(
            APIKeyMiddleware,
            provider=api_key_provider,
            header_name="X-API-Key",
            exempt_paths=["/health"],
        )
        app.add_middleware(
            IPWhitelistMiddleware,
            provider=whitelist_provider,
            exempt_paths=["/health"],
            trust_proxy_headers=True,
        )
        app.add_middleware(
            AdminIPBypassMiddleware,
            admin_ips=[ADMIN_IP],
            trust_proxy_headers=True,
        )

        @app.get("/")
        async def root():
            return {"ok": True}

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        return app

    return _factory


def test_admin_ip_bypasses_whitelist_and_api_key_middlewares(make_app):
    app = make_app()
    client = TestClient(app)

    # From ADMIN_IP, without API key and not in whitelist: should still pass
    r = client.get("/", headers={"X-Real-IP": ADMIN_IP})
    assert r.status_code == 200


def test_non_admin_not_whitelisted_blocked_even_with_api_key(make_app):
    app = make_app()
    client = TestClient(app)

    # From NON_ADMIN_IP, not whitelisted, even with a valid API key should be blocked by whitelist
    r = client.get("/", headers={"X-Real-IP": NON_ADMIN_IP, "X-API-Key": "valid-key"})
    assert r.status_code == 403
    assert "IP" in r.json()["detail"]


def test_non_admin_not_whitelisted_blocked_without_api_key(make_app):
    app = make_app()
    client = TestClient(app)

    # From NON_ADMIN_IP, not whitelisted, without API key should be blocked by whitelist (403),
    # not by API key (401), proving whitelist runs and enforces before API key.
    r = client.get("/", headers={"X-Real-IP": NON_ADMIN_IP})
    assert r.status_code == 403
