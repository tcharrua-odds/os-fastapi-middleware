import pytest
import time
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from os_fastapi_middleware.dependencies.rate_limit import RateLimitDependency
from os_fastapi_middleware.providers.memory import InMemoryRateLimitProvider


@pytest.fixture
def app():
    provider = InMemoryRateLimitProvider()
    dep = RateLimitDependency(provider, requests_per_window=2, window_seconds=1)

    app = FastAPI()

    @app.get("/limited")
    async def limited(_: bool = Depends(dep)):
        return {"ok": True}

    return app


def test_rate_limit_dependency_within_limit(app):
    client = TestClient(app)
    assert client.get("/limited").status_code == 200
    assert client.get("/limited").status_code == 200


def test_rate_limit_dependency_exceeded_and_resets(app):
    client = TestClient(app)
    # Hit limit
    client.get("/limited")
    client.get("/limited")
    res = client.get("/limited")
    assert res.status_code == 429
    assert "rate limit exceeded" in res.json()["detail"].lower()

    # Wait for window to reset
    time.sleep(1.1)
    res2 = client.get("/limited")
    assert res2.status_code == 200
