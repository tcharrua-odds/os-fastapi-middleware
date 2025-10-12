import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from os_fastapi_middleware import RateLimitMiddleware, InMemoryRateLimitProvider


@pytest.fixture
def app_with_rate_limit():
    app = FastAPI()
    
    provider = InMemoryRateLimitProvider()
    
    app.add_middleware(
        RateLimitMiddleware,
        provider=provider,
        requests_per_window=5,
        window_seconds=60,
        add_headers=True
    )
    
    @app.get("/")
    async def root():
        return {"message": "Hello"}
    
    return app


def test_rate_limit_within_limit(app_with_rate_limit):
    client = TestClient(app_with_rate_limit)

    for i in range(5):
        response = client.get("/")
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers


def test_rate_limit_exceeded(app_with_rate_limit):
    client = TestClient(app_with_rate_limit)

    for _ in range(5):
        client.get("/")

    response = client.get("/")
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["detail"]
    assert "Retry-After" in response.headers


def test_rate_limit_headers(app_with_rate_limit):
    client = TestClient(app_with_rate_limit)
    
    response = client.get("/")
    assert response.headers["X-RateLimit-Limit"] == "5"
    assert int(response.headers["X-RateLimit-Remaining"]) <= 5