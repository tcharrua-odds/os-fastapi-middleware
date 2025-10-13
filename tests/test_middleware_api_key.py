import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from os_fastapi_middleware import APIKeyMiddleware, InMemoryAPIKeyProvider


@pytest.fixture
def app_with_api_key():
    app = FastAPI()
    
    provider = InMemoryAPIKeyProvider(
        valid_keys={
            "account_john": "valid-key",
            "account_admin": "admin-key"
        }
    )
    
    app.add_middleware(
        APIKeyMiddleware,
        provider=provider,
        include_metadata=True,
        exempt_paths=["/health"]
    )
    
    @app.get("/")
    async def root():
        return {"message": "Hello"}
    
    @app.get("/health")
    async def health():
        return {"status": "ok"}
    
    return app


def test_api_key_missing(app_with_api_key):
    client = TestClient(app_with_api_key)
    response = client.get("/")
    assert response.status_code == 401
    assert "API key required" in response.json()["detail"]


def test_api_key_invalid(app_with_api_key):
    client = TestClient(app_with_api_key)
    response = client.get("/", headers={"X-API-Key": "invalid-key"})
    assert response.status_code == 403
    assert "Invalid API key" in response.json()["detail"]


def test_api_key_valid(app_with_api_key):
    client = TestClient(app_with_api_key)
    response = client.get("/", headers={"X-API-Key": "valid-key"})
    assert response.status_code == 200
    assert response.json() == {"message": "Hello"}


def test_health_endpoint_exempt(app_with_api_key):
    """Health endpoint não deve requerer API key."""
    client = TestClient(app_with_api_key)
    response = client.get("/health")
    assert response.status_code == 200