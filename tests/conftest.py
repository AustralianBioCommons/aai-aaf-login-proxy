from fastapi.testclient import TestClient
from fastapi import FastAPI
from unittest.mock import AsyncMock

import pytest

from application import create_app
from config import AppConfig
from proxy.dependencies import (
    get_config,
    get_valkey_connection,
    get_domain_map,
    get_aaf_domains,
)


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
        proxy_authorize_url="https://proxy.example/authorize",
        allowed_origins="http://localhost",
    )


@pytest.fixture(autouse=True)
def override_app_config(app, mock_app_config):
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
def override_valkey_connection(app, mock_valkey):
    app.dependency_overrides[get_valkey_connection] = lambda: mock_valkey
    yield
    app.dependency_overrides.pop(get_valkey_connection)


@pytest.fixture
def override_domain_map(app):
    def _override(domain_map):
        app.dependency_overrides[get_domain_map] = lambda: domain_map

    yield _override
    app.dependency_overrides.pop(get_domain_map, None)


@pytest.fixture
def override_aaf_domains(app):
    def _override(domains):
        app.dependency_overrides[get_aaf_domains] = lambda: domains

    yield _override
    app.dependency_overrides.pop(get_aaf_domains, None)


@pytest.fixture
def app(mock_app_config) -> FastAPI:
    return create_app(config=mock_app_config)


@pytest.fixture
def test_client(app, override_app_config, override_valkey_connection) -> TestClient:
    return TestClient(app=app)
