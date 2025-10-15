import pytest
from fastapi import FastAPI, Depends, Request
from fastapi.testclient import TestClient

from os_fastapi_middleware.dependencies.admin_ip_bypass import AdminIPBypassDependency


ADMIN_IP = "203.0.113.10"
NON_ADMIN_IP = "198.51.100.23"


@pytest.fixture()
def app():
    app = FastAPI()

    optional_dep = AdminIPBypassDependency(admin_ips=[ADMIN_IP], auto_error=False)
    required_dep = AdminIPBypassDependency(admin_ips=[ADMIN_IP], auto_error=True)

    @app.get("/inspect")
    async def inspect(admin: bool = Depends(optional_dep), request: Request = None):
        # Returns both dependency result and the state flags for verification
        return {
            "dep_result": admin,
            "admin_bypass": bool(getattr(request.state, "admin_bypass", False)),
            "client_ip": getattr(request.state, "client_ip", None),
        }

    @app.get("/required")
    async def required(_: bool = Depends(required_dep)):
        return {"ok": True}

    return app


def test_admin_ip_dependency_sets_state_and_returns_true(app):
    client = TestClient(app)

    r = client.get("/inspect", headers={"X-Real-IP": ADMIN_IP})
    assert r.status_code == 200
    data = r.json()
    assert data["dep_result"] is True
    assert data["admin_bypass"] is True
    assert data["client_ip"] == ADMIN_IP


def test_non_admin_optional_returns_false_no_error(app):
    client = TestClient(app)

    r = client.get("/inspect", headers={"X-Real-IP": NON_ADMIN_IP})
    assert r.status_code == 200
    data = r.json()
    assert data["dep_result"] is False
    assert data["admin_bypass"] is False


def test_non_admin_required_errors(app):
    client = TestClient(app)

    # Non-admin must be rejected with Forbidden (403)
    r = client.get("/required", headers={"X-Real-IP": NON_ADMIN_IP})
    assert r.status_code == 403
    assert "admin ip required" in r.json()["detail"].lower()

    # Admin IP should pass
    r2 = client.get("/required", headers={"X-Real-IP": ADMIN_IP})
    assert r2.status_code == 200
