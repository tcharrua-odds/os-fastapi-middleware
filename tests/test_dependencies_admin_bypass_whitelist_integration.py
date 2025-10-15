import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from os_fastapi_middleware import (
    AdminIPBypassDependency,
    IPWhitelistDependency,
    APIKeyDependency,
    InMemoryIPWhitelistProvider,
    InMemoryAPIKeyProvider,
)

ADMIN_IP = "127.0.0.1"
NON_ADMIN_IP = "198.51.100.23"


@pytest.fixture()
def make_app():
    def _factory():
        app = FastAPI()

        # Providers
        whitelist_provider = InMemoryIPWhitelistProvider(["203.0.113.10"])  # does NOT include admin IP
        api_key_provider = InMemoryAPIKeyProvider({"acct": "valid-key"})

        # Dependencies: admin first so others can observe bypass
        admin_dep = AdminIPBypassDependency(admin_ips=[ADMIN_IP], auto_error=False)
        whitelist_dep = IPWhitelistDependency(whitelist_provider)
        api_key_dep = APIKeyDependency(api_key_provider, auto_error=True)

        @app.get("/")
        async def root(
            _admin: bool = Depends(admin_dep),
            _ip: str = Depends(whitelist_dep),
            _api: str = Depends(api_key_dep),
        ):
            return {"ok": True}

        @app.get("/only_whitelist")
        async def only_whitelist(
            _admin: bool = Depends(admin_dep),
            _ip: str = Depends(whitelist_dep),
        ):
            return {"ok": True}

        return app

    return _factory


def test_admin_ip_ignores_whitelist_and_api_key(make_app):
    app = make_app()
    client = TestClient(app)

    # From ADMIN_IP, without API key and not whitelisted: should still pass due to admin bypass
    r = client.get("/", headers={"X-Real-IP": ADMIN_IP})
    assert r.status_code == 200


def test_non_admin_blocked_by_whitelist(make_app):
    app = make_app()
    client = TestClient(app)

    # From NON_ADMIN_IP, no API key, not whitelisted: should be blocked by whitelist dep (403)
    r = client.get("/only_whitelist", headers={"X-Real-IP": NON_ADMIN_IP})
    assert r.status_code == 403
    assert "IP address" in r.json()["detail"]
