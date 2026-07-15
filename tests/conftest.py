from unittest.mock import AsyncMock

import pytest

from config import AppConfig
from proxy.dependencies import get_config, get_valkey_connection
from main import app


@pytest.fixture
def mock_app_config():
    return AppConfig(
        valkey_host="localhost",
        valkey_port=6379,
        aaf_metadata_url="https://test.example/metadata.xml",
        aaf_pubkey_url="https://test.example/pubkey.pem",
        aaf_authorize_url="https://test.example/authorize",
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
