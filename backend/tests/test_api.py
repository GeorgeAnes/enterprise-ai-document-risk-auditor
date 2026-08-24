from fastapi.testclient import TestClient

from backend.app.main import _cors_allowed_origins, app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_audit_endpoint_with_text():
    payload = {
        "filename": "demo.md",
        "text": (
            "The analytics program reduced rework by 25 percent in Q1 2026. "
            "The pilot evidence states that rework decreased from 120 cases to 90 cases in Q1 2026. "
            "The model is guaranteed to be fully compliant in all cases."
        ),
    }
    response = client.post("/audit", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["total_claims"] >= 2
    assert data["claims"]
    assert "markdown_report" in data


def test_cors_allowed_origins_default_is_localhost_only(monkeypatch):
    monkeypatch.delenv("FRONTEND_ORIGIN", raising=False)
    assert _cors_allowed_origins() == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_cors_allowed_origins_includes_frontend_origin_when_set(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://example-swa.azurestaticapps.net")
    origins = _cors_allowed_origins()
    assert "https://example-swa.azurestaticapps.net" in origins
    assert "http://localhost:5173" in origins
    assert "http://127.0.0.1:5173" in origins


def test_cors_allowed_origins_never_includes_wildcard(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://example-swa.azurestaticapps.net")
    assert "*" not in _cors_allowed_origins()
