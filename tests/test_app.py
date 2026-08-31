from fastapi.middleware.cors import CORSMiddleware
from starlette.testclient import TestClient

from main import APP_VERSION, app
from proxy.dependencies import get_config


def test_healthcheck(test_client: TestClient):
    response = test_client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_default_returns_app_version(test_client: TestClient):
    response = test_client.get("/")

    assert response.status_code == 200
    assert response.json()["version"] == APP_VERSION


def test_cors_middleware_uses_allowed_origins_from_config():
    cors_middleware = next(
        middleware
        for middleware in app.user_middleware
        if middleware.cls is CORSMiddleware
    )

    assert cors_middleware.kwargs["allow_origins"] == get_config().allowed_origins
