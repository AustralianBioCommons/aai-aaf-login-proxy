from starlette.testclient import TestClient

from main import APP_VERSION


def test_healthcheck(test_client: TestClient):
    response = test_client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_default_returns_app_version(test_client: TestClient):
    response = test_client.get("/")

    assert response.status_code == 200
    assert response.json()["version"] == APP_VERSION
