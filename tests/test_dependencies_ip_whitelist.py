import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from os_fastapi_middleware.dependencies.ip_whitelist import IPWhitelistDependency
from os_fastapi_middleware.providers.memory import InMemoryIPWhitelistProvider


@pytest.fixture
def app():
    provider = InMemoryIPWhitelistProvider(allowed_ips={"127.0.0.1", "10.0.0.1"})
    dep = IPWhitelistDependency(provider)

    app = FastAPI()

    @app.get("/secure-ip")
    async def secure_route(client_ip: str = Depends(dep)):
        return {"ok": True, "ip": client_ip}

    return app


def test_ip_whitelist_dependency_allowed_localhost(app):
    client = TestClient(app)
    res = client.get("/secure-ip")
    assert res.status_code == 200
    assert res.json()["ok"] is True


def test_ip_whitelist_dependency_blocked(app):
    client = TestClient(app)
    # Simulate different client IP using X-Real-IP
    res = client.get("/secure-ip", headers={"X-Real-IP": "192.168.1.100"})
    assert res.status_code == 403
    assert "not allowed" in res.json()["detail"].lower() or "not whitelisted" in res.json()["detail"].lower()
