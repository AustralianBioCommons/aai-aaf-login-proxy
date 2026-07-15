from unittest.mock import Mock
import pytest

from proxy.dependencies import get_config, get_valkey_connection, get_domain_map


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
    )


@pytest.mark.asyncio
async def test_get_domain_map(mock_valkey, mocker):
    mock_map = Mock(domain_map={"sydney.edu": "https://sydney.edu.au/login"})
    get_metadata_cache = mocker.patch(
        "proxy.dependencies.get_metadata_cache",
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
        "proxy.dependencies.get_metadata_cache", mocker.AsyncMock(return_value=None)
    )
    result = await get_domain_map(mock_valkey)
    assert result is None
