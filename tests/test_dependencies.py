from unittest.mock import Mock
import pytest

from cache import ExpiredMetadataError
from proxy.dependencies import (
    get_config,
    get_valkey_connection,
    get_domain_map,
    get_oidc_config,
)


def test_get_config(mock_app_config, mocker):
    """
    Test get_config calls AppConfig and returns the result
    """
    mocker.patch("proxy.dependencies.AppConfig", return_value=mock_app_config)
    assert get_config() == mock_app_config


def test_get_valkey_connection(mock_app_config, mocker):
    """
    Test get_valkey_connection calls Valkey with the correct parameters
    """
    valkey_cls = mocker.patch("proxy.dependencies.valkey_async.Valkey")

    get_valkey_connection(mock_app_config)

    valkey_cls.assert_called_once_with(
        host=mock_app_config.valkey_host,
        port=mock_app_config.valkey_port,
        password=mock_app_config.valkey_password,
    )


@pytest.mark.asyncio
async def test_get_domain_map(mock_valkey, mocker):
    mock_map = Mock(domain_map={"sydney.edu": "https://sydney.edu.au/login"})
    get_metadata_cache = mocker.patch(
        "proxy.dependencies.get_cached_metadata",
        mocker.AsyncMock(return_value=mock_map),
    )
    result = await get_domain_map(mock_valkey)
    assert result == mock_map.domain_map
    get_metadata_cache.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_domain_map_no_cache(mock_valkey, mocker):
    """
    Test get_domain_map returns None if no metadata cache is available
    """
    mocker.patch(
        "proxy.dependencies.get_cached_metadata", mocker.AsyncMock(return_value=None)
    )
    result = await get_domain_map(mock_valkey)
    assert result is None


@pytest.mark.asyncio
async def test_get_oidc_config(mock_valkey, mocker):
    mock_config = Mock(
        config={"authorization_endpoint": "https://proxy.example/authorize"}
    )
    get_cached_oidc = mocker.patch(
        "proxy.dependencies.get_cached_oidc_config",
        mocker.AsyncMock(return_value=mock_config),
    )
    result = await get_oidc_config(mock_valkey)
    assert result == mock_config.config
    get_cached_oidc.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_oidc_config_no_cache(mock_valkey, mocker):
    """
    Test get_oidc_config returns None if no metadata cache is available
    """
    get_cached_oidc = mocker.patch(
        "proxy.dependencies.get_cached_oidc_config", mocker.AsyncMock(return_value=None)
    )
    result = await get_oidc_config(mock_valkey)
    assert result is None
    get_cached_oidc.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_oidc_config_returns_none_when_cache_expired(mock_valkey, mocker):
    get_cached_oidc = mocker.patch(
        "proxy.dependencies.get_cached_oidc_config",
        mocker.AsyncMock(side_effect=ExpiredMetadataError("expired")),
    )
    result = await get_oidc_config(mock_valkey)
    assert result is None
    get_cached_oidc.assert_awaited_once_with(connection=mock_valkey)
