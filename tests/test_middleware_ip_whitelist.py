import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from os_fastapi_middleware import IPWhitelistMiddleware
from os_fastapi_middleware import InMemoryIPWhitelistProvider
from fastapi import status


@pytest.fixture()
def make_app():
    def _factory(provider, **mw_kwargs):
        app = FastAPI()

        @app.get("/health")
        async def health():
            return {"ok": True}

        @app.get("/protected")
        async def protected():
            return {"protected": True}

        app.add_middleware(IPWhitelistMiddleware, provider=provider, **mw_kwargs)
        return app

    return _factory


def test_allowed_ip_via_header(make_app):
    provider = InMemoryIPWhitelistProvider(["203.0.113.10"])
    app = make_app(provider)
    client = TestClient(app)

    r = client.get("/protected", headers={"X-Forwarded-For": "203.0.113.10"})
    assert r.status_code == status.HTTP_200_OK
    assert r.json() == {"protected": True}


def test_blocked_ip_via_header(make_app):
    provider = InMemoryIPWhitelistProvider(["203.0.113.9"])
    app = make_app(provider)
    client = TestClient(app)

    r = client.get("/protected", headers={"X-Forwarded-For": "203.0.113.10"})
    assert r.status_code == status.HTTP_403_FORBIDDEN
    assert r.json()["detail"].startswith("IP 203.0.113.10 is not whitelisted")


def test_exempt_path_bypasses_check(make_app):
    provider = InMemoryIPWhitelistProvider([])
    app = make_app(provider)
    client = TestClient(app)

    r = client.get("/health")
    assert r.status_code == status.HTTP_200_OK
    assert r.json() == {"ok": True}


def test_trust_proxy_headers_false_uses_client_host(make_app):
    provider = InMemoryIPWhitelistProvider(["127.0.0.1"])
    app = make_app(provider, trust_proxy_headers=False)
    client = TestClient(app)

    r = client.get("/protected", headers={"X-Forwarded-For": "203.0.113.10"})
    assert r.status_code == status.HTTP_200_OK
    assert r.json() == {"protected": True}


def test_trust_proxy_headers_false_blocks_when_client_host_not_allowed(make_app):
    provider = InMemoryIPWhitelistProvider(["203.0.113.10"])
    app = make_app(provider, trust_proxy_headers=False)
    client = TestClient(app)

    r = client.get("/protected")
    assert r.status_code == status.HTTP_403_FORBIDDEN
    assert r.json()["detail"].startswith("IP 127.0.0.1 is not whitelisted")


def test_provider_error_results_in_500(make_app, monkeypatch):
    provider = InMemoryIPWhitelistProvider(["127.0.0.1"])

    async def boom(_ip: str):
        raise RuntimeError("failure inside provider")

    monkeypatch.setattr(provider, "is_ip_allowed", boom)

    app = make_app(provider)
    client = TestClient(app)

    r = client.get("/protected")
    assert r.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert r.json()["detail"] == "Error checking IP whitelist"