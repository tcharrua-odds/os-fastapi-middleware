import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from os_fastapi_middleware import (
    APIKeyMiddleware,
    RateLimitMiddleware,
    AdminIPBypassMiddleware,
    InMemoryAPIKeyProvider,
    InMemoryRateLimitProvider,
)


ADMIN_IP = "203.0.113.10"
NON_ADMIN_IP = "198.51.100.23"


@pytest.fixture()
def make_app():
    def _factory():
        app = FastAPI()

        # Providers
        api_key_provider = InMemoryAPIKeyProvider({
            "acct": "valid-key",
        })
        rate_limit_provider = InMemoryRateLimitProvider()

        # Middlewares: add security first, then AdminIPBypass last so it runs first
        app.add_middleware(
            APIKeyMiddleware,
            provider=api_key_provider,
            header_name="X-API-Key",
            exempt_paths=["/health"],
        )
        app.add_middleware(
            RateLimitMiddleware,
            provider=rate_limit_provider,
            requests_per_window=2,
            window_seconds=60,
            add_headers=False,
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


def test_admin_ip_bypasses_all(make_app):
    app = make_app()
    client = TestClient(app)

    headers = {"X-Real-IP": ADMIN_IP}

    # No API key, should still be allowed
    r1 = client.get("/", headers=headers)
    assert r1.status_code == 200

    # Even exceeding rate limit should still pass due to admin bypass
    r2 = client.get("/", headers=headers)
    assert r2.status_code == 200
    r3 = client.get("/", headers=headers)
    assert r3.status_code == 200


def test_non_admin_requires_api_key(make_app):
    app = make_app()
    client = TestClient(app)

    # Missing API key should be rejected for non-admin IP
    r = client.get("/", headers={"X-Real-IP": NON_ADMIN_IP})
    assert r.status_code == 401


def test_non_admin_rate_limited(make_app):
    app = make_app()
    client = TestClient(app)

    headers = {"X-Real-IP": NON_ADMIN_IP, "X-API-Key": "valid-key"}

    # Within limit
    assert client.get("/", headers=headers).status_code == 200
    assert client.get("/", headers=headers).status_code == 200

    # Exceeding limit should return 429 for non-admin
    r = client.get("/", headers=headers)
    assert r.status_code == 429
