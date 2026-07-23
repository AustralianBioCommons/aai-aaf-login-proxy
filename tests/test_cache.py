from datetime import UTC, datetime, timedelta

import fakeredis
import pytest
from lxml import etree

from aaf.metadata import AafMetadata, AafProvider
from cache import (
    METADATA_CACHE_KEY,
    OIDC_CONFIG_CACHE_KEY,
    ExpiredMetadataError,
    MetadataCache,
    get_cached_oidc_config,
    get_cached_metadata,
    OidcConfigCache,
    update_metadata_cache,
    update_oidc_config_cache,
)


@pytest.fixture
def fake_valkey():
    return fakeredis.FakeAsyncValkey()


@pytest.mark.asyncio
async def test_get_metadata_cache_returns_none_when_cache_is_empty(fake_valkey):
    result = await get_cached_metadata(fake_valkey)

    assert result is None


@pytest.mark.asyncio
async def test_get_metadata_cache_returns_cached_metadata(fake_valkey):
    now = datetime.now(UTC)
    cached_metadata = MetadataCache(
        domain_map={"example.edu.au": "https://idp.example.edu.au/idp/shibboleth"},
        updated_at=now,
        expires_at=now + timedelta(days=1),
    )
    await fake_valkey.set(METADATA_CACHE_KEY, cached_metadata.model_dump_json())

    result = await get_cached_metadata(fake_valkey)

    assert result == cached_metadata


@pytest.mark.asyncio
async def test_get_metadata_cache_raises_when_cached_metadata_is_expired(fake_valkey):
    now = datetime.now(UTC)
    cached_metadata = MetadataCache(
        domain_map={"example.edu.au": "https://idp.example.edu.au/idp/shibboleth"},
        updated_at=now - timedelta(days=2),
        expires_at=now - timedelta(days=1),
    )
    await fake_valkey.set(METADATA_CACHE_KEY, cached_metadata.model_dump_json())

    with pytest.raises(ExpiredMetadataError, match="Cached metadata expired at"):
        await get_cached_metadata(fake_valkey)


@pytest.mark.asyncio
async def test_update_metadata_cache_stores_verified_metadata(
    fake_valkey, mock_app_config, mocker
):
    verified_metadata = etree.Element("EntitiesDescriptor")
    expires_at = datetime.now(UTC) + timedelta(days=1)
    entity_id = "https://idp.example.edu.au/idp/shibboleth"
    parsed_metadata = AafMetadata(
        domain_map={"example.edu.au": "https://idp.example.edu.au/idp/shibboleth"},
        expires_at=expires_at,
        providers={
            entity_id: AafProvider(
                entity_id=entity_id,
                scopes=["example.edu.au"],
                organization_name="Example University",
                organization_display_name="Example Uni",
            )
        },
        errors={},
    )
    valkey_cls = mocker.patch("cache.valkey.Valkey", return_value=fake_valkey)
    get_verified_metadata = mocker.patch(
        "cache.get_verified_metadata",
        mocker.AsyncMock(return_value=verified_metadata),
    )
    get_aaf_metadata = mocker.patch(
        "cache.get_aaf_metadata",
        return_value=parsed_metadata,
    )
    mocker.patch("cache.AppConfig", return_value=mock_app_config)

    await update_metadata_cache()

    valkey_cls.assert_called_once_with(
        host=mock_app_config.valkey_host,
        port=mock_app_config.valkey_port,
        password=mock_app_config.valkey_password,
    )
    get_verified_metadata.assert_awaited_once_with(
        mock_app_config.aaf_metadata_url,
        mock_app_config.aaf_pubkey_url,
    )
    get_aaf_metadata.assert_called_once_with(verified_metadata)

    result = await get_cached_metadata(fake_valkey)
    assert result is not None
    assert result.domain_map == parsed_metadata.domain_map
    assert result.expires_at == expires_at


@pytest.mark.asyncio
async def test_update_oidc_config_cache_stores_oidc_config(
    fake_valkey, mock_app_config, mocker
):
    oidc_config = {
        "issuer": "https://test.example/",
        "authorization_endpoint": "https://proxy.example/authorize",
        "token_endpoint": "https://test.example/oidc/token",
    }
    valkey_cls = mocker.patch("cache.valkey.Valkey", return_value=fake_valkey)
    get_overridden_oidc_configuration = mocker.patch(
        "cache.get_overridden_oidc_configuration",
        mocker.AsyncMock(return_value=oidc_config),
    )
    mocker.patch("cache.AppConfig", return_value=mock_app_config)
    now = datetime(2026, 7, 23, 4, 2, 29, tzinfo=UTC)
    datetime_mock = mocker.patch("cache.datetime")
    datetime_mock.now.return_value = now

    await update_oidc_config_cache()

    valkey_cls.assert_called_once_with(
        host=mock_app_config.valkey_host,
        port=mock_app_config.valkey_port,
        password=mock_app_config.valkey_password,
    )
    get_overridden_oidc_configuration.assert_awaited_once_with(mock_app_config)

    result = await get_cached_oidc_config(fake_valkey)
    assert result is not None
    assert result.config == oidc_config
    assert result.updated_at == now
    assert result.expires_at == now + timedelta(days=1)


@pytest.mark.asyncio
async def test_get_cached_oidc_config_no_cache(fake_valkey):
    result = await get_cached_oidc_config(fake_valkey)
    assert result is None


@pytest.mark.asyncio
async def test_get_cached_oid_config_returns_cahed_data(fake_valkey):
    now = datetime.now(UTC)
    cached = OidcConfigCache(
        config={"issuer": "https://test.example.com"},
        updated_at=now,
        expires_at=now + timedelta(days=1),
    )
    await fake_valkey.set(OIDC_CONFIG_CACHE_KEY, cached.model_dump_json())
    result = await get_cached_oidc_config(fake_valkey)
    assert result == cached


@pytest.mark.asyncio
async def test_get_cached_oidc_config_expired(fake_valkey):
    now = datetime.now(UTC)
    cached_metadata = OidcConfigCache(
        config={"issuer": "https://test.example.com"},
        updated_at=now - timedelta(days=2),
        expires_at=now - timedelta(days=1),
    )
    await fake_valkey.set(OIDC_CONFIG_CACHE_KEY, cached_metadata.model_dump_json())

    with pytest.raises(ExpiredMetadataError, match="Cached OIDC config expired at"):
        await get_cached_oidc_config(fake_valkey)
