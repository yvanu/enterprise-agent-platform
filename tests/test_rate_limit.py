from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.platform.observability import install_observability


def test_api_rate_limit_uses_shared_error_model():
    app = FastAPI()
    install_observability(app, rate_limit_per_minute=2)

    @app.get("/api/v1/ping")
    def ping():
        return {"status": "ok"}

    client = TestClient(app)
    assert client.get("/api/v1/ping").status_code == 200
    assert client.get("/api/v1/ping").status_code == 200

    response = client.get("/api/v1/ping")

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"
    assert response.json()["error"]["code"] == "RATE_LIMITED"
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]


def test_health_paths_are_not_rate_limited():
    app = FastAPI()
    install_observability(app, rate_limit_per_minute=1)

    @app.get("/health/live")
    def live():
        return {"status": "ok"}

    client = TestClient(app)
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/live").status_code == 200
