from typing import Any

import pytest

from tests.conftest import AppConfigNoEnv


CONFIG_DEFAULTS: dict[str, Any] = {
    "valkey_host": "localhost",
    "valkey_port": 6379,
    "valkey_password": "dummy-password",
    "aaf_metadata_url": "https://test.example/metadata.xml",
    "aaf_pubkey_url": "https://test.example/pubkey.pem",
    "aaf_oidc_url": "https://test.example/",
    "proxy_authorize_url": "https://proxy.example/authorize",
}


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
        proxy_authorize_url="https://proxy.example/authorize",
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
    monkeypatch.setenv("PROXY_AUTHORIZE_URL", "https://proxy.example/authorize")
    config = AppConfigNoEnv()
    assert config.valkey_host == "localhost"
    assert config.valkey_port == 6379
    assert config.aaf_metadata_url == "https://test.example/metadata.xml"
    assert config.aaf_pubkey_url == "https://test.example/pubkey.pem"
    assert config.aaf_authorize_url == "https://test.example/oidc/authorize"
    assert config.proxy_authorize_url == "https://proxy.example/authorize"


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


def test_app_config_allowed_origins():
    """
    Test allowed_origins splits by comma and trims whitespace when passed directly
    """
    config = AppConfigNoEnv(
        **CONFIG_DEFAULTS,
        allowed_origins="https://example.com , https://other.org  ",
    )
    assert config.allowed_origins == ["https://example.com", "https://other.org"]


def test_app_config_allowed_origins_from_env_var(monkeypatch):
    monkeypatch.setenv("VALKEY_HOST", "localhost")
    monkeypatch.setenv("VALKEY_PORT", "6379")
    monkeypatch.setenv("VALKEY_PASSWORD", "dummy-password")
    monkeypatch.setenv("AAF_METADATA_URL", "https://test.example/metadata.xml")
    monkeypatch.setenv("AAF_PUBKEY_URL", "https://test.example/pubkey.pem")
    monkeypatch.setenv("AAF_OIDC_URL", "https://test.example/")
    monkeypatch.setenv("PROXY_AUTHORIZE_URL", "https://proxy.example/authorize")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://example.com , https://other.org  ")

    config = AppConfigNoEnv()

    assert config.allowed_origins == ["https://example.com", "https://other.org"]
