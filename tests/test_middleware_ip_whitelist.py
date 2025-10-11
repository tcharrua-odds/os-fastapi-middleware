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

        # Rota pública (exempt por padrão no middleware, mas aqui garantimos)
        @app.get("/health")
        async def health():
            return {"ok": True}

        # Rota protegida por IP
        @app.get("/protected")
        async def protected():
            return {"protected": True}

        app.add_middleware(IPWhitelistMiddleware, provider=provider, **mw_kwargs)
        return app

    return _factory


def test_allowed_ip_via_header(make_app):
    provider = InMemoryIPWhitelistProvider(["203.0.113.10"])  # IP permitido só se vier no header
    app = make_app(provider)
    client = TestClient(app)

    # Simula proxy: header é respeitado por padrão (trust_proxy_headers=True)
    r = client.get("/protected", headers={"X-Forwarded-For": "203.0.113.10"})
    assert r.status_code == status.HTTP_200_OK
    assert r.json() == {"protected": True}


def test_blocked_ip_via_header(make_app):
    provider = InMemoryIPWhitelistProvider(["203.0.113.9"])  # Diferente do que enviaremos
    app = make_app(provider)
    client = TestClient(app)

    r = client.get("/protected", headers={"X-Forwarded-For": "203.0.113.10"})
    assert r.status_code == status.HTTP_403_FORBIDDEN
    assert r.json()["detail"].startswith("IP 203.0.113.10 is not whitelisted")


def test_exempt_path_bypasses_check(make_app):
    provider = InMemoryIPWhitelistProvider([])  # Ninguém permitido
    app = make_app(provider)
    client = TestClient(app)

    # /health está na lista de exempts por padrão
    r = client.get("/health")
    assert r.status_code == status.HTTP_200_OK
    assert r.json() == {"ok": True}


def test_trust_proxy_headers_false_uses_client_host(make_app):
    # Não permitimos X-Forwarded-For, então dependerá do client.host (127.0.0.1 no TestClient)
    provider = InMemoryIPWhitelistProvider(["127.0.0.1"])  # Permite o host local do TestClient
    app = make_app(provider, trust_proxy_headers=False)
    client = TestClient(app)

    # Header será ignorado com trust_proxy_headers=False
    r = client.get("/protected", headers={"X-Forwarded-For": "203.0.113.10"})
    assert r.status_code == status.HTTP_200_OK
    assert r.json() == {"protected": True}


def test_trust_proxy_headers_false_blocks_when_client_host_not_allowed(make_app):
    provider = InMemoryIPWhitelistProvider(["203.0.113.10"])  # Não inclui 127.0.0.1
    app = make_app(provider, trust_proxy_headers=False)
    client = TestClient(app)

    r = client.get("/protected")
    assert r.status_code == status.HTTP_403_FORBIDDEN
    # client_ip deve ser 127.0.0.1 no ambiente de teste
    assert r.json()["detail"].startswith("IP 127.0.0.1 is not whitelisted")


def test_provider_error_results_in_500(make_app, monkeypatch):
    provider = InMemoryIPWhitelistProvider(["127.0.0.1"])  # Não importa, vamos falhar

    async def boom(_ip: str):
        raise RuntimeError("failure inside provider")

    # monkeypatch no método
    monkeypatch.setattr(provider, "is_ip_allowed", boom)

    app = make_app(provider)
    client = TestClient(app)

    r = client.get("/protected")
    assert r.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert r.json()["detail"] == "Error checking IP whitelist"