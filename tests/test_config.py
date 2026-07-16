from typing import Any

import pytest

from config import AppConfig


def test_app_config():
    """
    Test basic config validates
    """
    config = AppConfig(
        valkey_host="localhost",
        valkey_port=6379,
        aaf_metadata_url="https://test.example/metadata.xml",
        aaf_pubkey_url="https://test.example/pubkey.pem",
        aaf_authorize_url="https://test.example/authorize",
    )
    assert config.valkey_host == "localhost"


def test_app_config_from_env_vars(monkeypatch):
    monkeypatch.setenv("VALKEY_HOST", "localhost")
    monkeypatch.setenv("VALKEY_PORT", "6379")
    monkeypatch.setenv("AAF_METADATA_URL", "https://test.example/metadata.xml")
    monkeypatch.setenv("AAF_PUBKEY_URL", "https://test.example/pubkey.pem")
    monkeypatch.setenv("AAF_AUTHORIZE_URL", "https://test.example/authorize")
    config = AppConfig()
    assert config.valkey_host == "localhost"
    assert config.valkey_port == 6379
    assert config.aaf_metadata_url == "https://test.example/metadata.xml"
    assert config.aaf_pubkey_url == "https://test.example/pubkey.pem"
    assert config.aaf_authorize_url == "https://test.example/authorize"


@pytest.mark.parametrize(
    "field", ["aaf_metadata_url", "aaf_pubkey_url", "aaf_authorize_url"]
)
def test_app_config_requires_https_urls(field):
    defaults: dict[str, Any] = {
        "valkey_host": "localhost",
        "valkey_port": 6379,
        "aaf_metadata_url": "https://test.example/metadata.xml",
        "aaf_pubkey_url": "https://test.example/pubkey.pem",
        "aaf_authorize_url": "https://test.example/authorize",
    }
    defaults[field] = "http://test.example/"
    with pytest.raises(ValueError, match=field):
        AppConfig(**defaults)
