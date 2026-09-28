from fastapi.testclient import TestClient

from app.main import app


def test_request_and_correlation_headers():
    response = TestClient(app).get(
        "/health",
        headers={"X-Correlation-ID": "incident-42"},
    )

    assert response.status_code == 200
    assert len(response.headers["X-Request-ID"]) == 32
    assert response.headers["X-Correlation-ID"] == "incident-42"


def test_api_errors_use_shared_model():
    response = TestClient(app).get(
        "/api/v1/platform/runs/999999",
        headers={"X-Correlation-ID": "incident-42"},
    )

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "NOT_FOUND"
    assert error["message"] == "Run 不存在"
    assert error["request_id"] == response.headers["X-Request-ID"]
    assert error["correlation_id"] == "incident-42"


def test_validation_errors_use_shared_model():
    response = TestClient(app).get("/api/v1/platform/runs?limit=0")

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["request_id"] == response.headers["X-Request-ID"]
    assert error["details"]
