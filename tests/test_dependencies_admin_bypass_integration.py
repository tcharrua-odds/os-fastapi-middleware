import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from os_fastapi_middleware import (
    AdminIPBypassDependency,
    APIKeyDependency,
    RateLimitDependency,
    InMemoryAPIKeyProvider,
    InMemoryRateLimitProvider,
)

ADMIN_IP = "127.0.0.1"
NON_ADMIN_IP = "198.51.100.23"


@pytest.fixture()
def make_app():
    def _factory():
        app = FastAPI()

        # Providers
        api_key_provider = InMemoryAPIKeyProvider({"acct": "valid-key"})
        rate_limit_provider = InMemoryRateLimitProvider()

        # Dependencies
        admin_dep = AdminIPBypassDependency(admin_ips=[ADMIN_IP], auto_error=False)
        api_key_dep = APIKeyDependency(api_key_provider, header_name="X-API-Key", auto_error=True)
        rate_dep = RateLimitDependency(rate_limit_provider, requests_per_window=2, window_seconds=60)

        @app.get("/")
        async def root(
            _admin: bool = Depends(admin_dep),
            _api: str = Depends(api_key_dep),
            _rate: bool = Depends(rate_dep),
        ):
            return {"ok": True}

        return app

    return _factory


def test_admin_ip_bypasses_other_dependencies(make_app):
    app = make_app()
    client = TestClient(app)

    # No API key header, but from ADMIN_IP should still pass due to bypass
    r1 = client.get("/", headers={"X-Real-IP": ADMIN_IP})
    assert r1.status_code == 200

    # Also should not be rate limited
    r2 = client.get("/", headers={"X-Real-IP": ADMIN_IP})
    assert r2.status_code == 200


def test_non_admin_requires_api_key(make_app):
    app = make_app()
    client = TestClient(app)

    # Missing API key from non-admin IP should be rejected
    r = client.get("/", headers={"X-Real-IP": NON_ADMIN_IP})
    assert r.status_code == 401


def test_non_admin_is_rate_limited(make_app):
    app = make_app()
    client = TestClient(app)

    headers = {"X-Real-IP": NON_ADMIN_IP, "X-API-Key": "valid-key"}

    assert client.get("/", headers=headers).status_code == 200
    assert client.get("/", headers=headers).status_code == 200

    r = client.get("/", headers=headers)
    assert r.status_code == 429
