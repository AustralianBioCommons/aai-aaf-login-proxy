from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

import pytest

from config import AppConfig
from proxy.dependencies import get_config, get_valkey_connection, get_domain_map
from main import app


class AppConfigNoEnv(AppConfig):
    """
    AppConfig for testing.
    Override the default env_file to None, so that the AppConfig doesn't try to load .env
    """

    model_config = {**AppConfig.model_config, "env_file": None}


@pytest.fixture
def mock_app_config():
    return AppConfigNoEnv(
        valkey_host="localhost",
        valkey_port=6379,
        valkey_password="dummy-password",
        aaf_metadata_url="https://test.example/metadata.xml",
        aaf_pubkey_url="https://test.example/pubkey.pem",
        aaf_oidc_url="https://test.example/",
    )


@pytest.fixture(autouse=True)
def override_app_config(mock_app_config):
    app.dependency_overrides[get_config] = lambda: mock_app_config
    yield
    app.dependency_overrides.pop(get_config, None)


@pytest.fixture
def mock_valkey():
    connection = AsyncMock()
    connection.get.return_value = None
    connection.set.return_value = True
    return connection


@pytest.fixture(autouse=True)
def override_valkey_connection(mock_valkey):
    app.dependency_overrides[get_valkey_connection] = lambda: mock_valkey
    yield
    app.dependency_overrides.pop(get_valkey_connection)


@pytest.fixture
def override_domain_map():
    def _override(domain_map):
        app.dependency_overrides[get_domain_map] = lambda: domain_map

    yield _override
    app.dependency_overrides.pop(get_domain_map, None)


@pytest.fixture
def test_client(override_app_config, override_valkey_connection) -> TestClient:
    return TestClient(app=app)
