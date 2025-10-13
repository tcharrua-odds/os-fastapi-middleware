import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from os_fastapi_middleware.dependencies.api_key import APIKeyDependency
from os_fastapi_middleware.providers.memory import InMemoryAPIKeyProvider


@pytest.fixture
def app():
    provider = InMemoryAPIKeyProvider(valid_keys={"account_alice": "valid"})
    api_key_dep = APIKeyDependency(provider)

    app = FastAPI()

    @app.get("/secure")
    async def secure_route(api_key: str = Depends(api_key_dep)):
        return {"ok": True, "api_key": api_key}

    return app


def test_api_key_dependency_success(app):
    client = TestClient(app)
    res = client.get("/secure", headers={"X-API-Key": "valid"})
    assert res.status_code == 200
    assert res.json()["ok"] is True
    assert res.json()["api_key"] == "valid"


def test_api_key_dependency_missing(app):
    client = TestClient(app)
    res = client.get("/secure")
    assert res.status_code == 401
    assert "API key required" in res.json()["detail"]


def test_api_key_dependency_invalid(app):
    client = TestClient(app)
    res = client.get("/secure", headers={"X-API-Key": "invalid"})
    assert res.status_code == 403
    assert res.json()["detail"] == "Invalid API key"
