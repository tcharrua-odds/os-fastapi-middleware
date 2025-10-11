"""Fixtures compartilhadas para os testes."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def app():
    """Cria uma aplicação FastAPI para testes."""
    app = FastAPI()
    
    @app.get("/")
    async def root():
        return {"message": "Hello World"}
    
    @app.get("/secure")
    async def secure():
        return {"message": "Secure endpoint"}
    
    @app.get("/health")
    async def health():
        return {"status": "ok"}
    
    return app


@pytest.fixture
def client(app):
    """Cria um cliente de teste."""
    return TestClient(app)