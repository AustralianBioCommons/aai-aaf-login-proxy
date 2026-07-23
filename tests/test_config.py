from typing import Any

import pytest

from tests.conftest import AppConfigNoEnv


def test_app_config():
    """
    Test basic config validates
    """
    config = AppConfigNoEnv(
        valkey_host="localhost",
        valkey_port=6379,
        valkey_password="dummy-password",
        aaf_metadata_url="https://test.example/metadata.xml",
        aaf_pubkey_url="https://test.example/pubkey.pem",
        aaf_oidc_url="https://test.example/",
    )
    assert config.valkey_host == "localhost"
    assert config.aaf_authorize_url == "https://test.example/oidc/authorize"


def test_app_config_from_env_vars(monkeypatch):
    monkeypatch.setenv("VALKEY_HOST", "localhost")
    monkeypatch.setenv("VALKEY_PORT", "6379")
    monkeypatch.setenv("VALKEY_PASSWORD", "dummy-password")
    monkeypatch.setenv("AAF_METADATA_URL", "https://test.example/metadata.xml")
    monkeypatch.setenv("AAF_PUBKEY_URL", "https://test.example/pubkey.pem")
    monkeypatch.setenv("AAF_OIDC_URL", "https://test.example/")
    config = AppConfigNoEnv()
    assert config.valkey_host == "localhost"
    assert config.valkey_port == 6379
    assert config.aaf_metadata_url == "https://test.example/metadata.xml"
    assert config.aaf_pubkey_url == "https://test.example/pubkey.pem"
    assert config.aaf_authorize_url == "https://test.example/oidc/authorize"


@pytest.mark.parametrize(
    "field", ["aaf_metadata_url", "aaf_pubkey_url", "aaf_oidc_url"]
)
def test_app_config_requires_https_urls(field):
    defaults: dict[str, Any] = {
        "valkey_host": "localhost",
        "valkey_port": 6379,
        "aaf_metadata_url": "https://test.example/metadata.xml",
        "aaf_pubkey_url": "https://test.example/pubkey.pem",
        "aaf_oidc_url": "https://test.example/",
    }
    defaults[field] = "http://test.example/"
    with pytest.raises(ValueError, match=field):
        AppConfigNoEnv(**defaults)
