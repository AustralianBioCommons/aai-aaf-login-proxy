from datetime import datetime, UTC, timedelta

from loguru import logger
from pydantic import BaseModel, AwareDatetime
import valkey.asyncio as valkey

from aaf.security import get_verified_metadata
from aaf.metadata import get_aaf_metadata, get_overridden_oidc_configuration
from config import AppConfig

METADATA_CACHE_KEY = "aaf_metadata"
OIDC_CONFIG_CACHE_KEY = "oidc_config"


class ExpiredMetadataError(RuntimeError):
    pass


class MetadataCache(BaseModel):
    domain_map: dict[str, str]
    updated_at: AwareDatetime
    expires_at: AwareDatetime


class OidcConfigCache(BaseModel):
    config: dict
    updated_at: AwareDatetime
    expires_at: AwareDatetime


async def update_metadata_cache():
    """
    Fetch metadata from AAF and store in cache. Intended to be run via the scheduler,
    so intentionally has no arguments.
    """
    settings = AppConfig()
    connection = valkey.Valkey(
        host=settings.valkey_host,
        port=settings.valkey_port,
        password=settings.valkey_password,
    )

    now = datetime.now(UTC)
    metadata_xml = await get_verified_metadata(
        settings.aaf_metadata_url, settings.aaf_pubkey_url
    )
    metadata = get_aaf_metadata(metadata_xml)
    cache_data = MetadataCache(
        domain_map=metadata.domain_map, updated_at=now, expires_at=metadata.expires_at
    )
    logger.info("Updating metadata cache")
    await connection.set(METADATA_CACHE_KEY, cache_data.model_dump_json())
    logger.info("Metadata cache updated successfully")


async def update_oidc_config_cache():
    """
    Fetch OIDC configuration from AAF and store in cache (overriden
    with our authorize endpoint).
    """
    settings = AppConfig()
    connection = valkey.Valkey(
        host=settings.valkey_host,
        port=settings.valkey_port,
        password=settings.valkey_password,
    )
    now = datetime.now(UTC)
    expiry = now + timedelta(days=1)
    oidc_config = await get_overridden_oidc_configuration(settings)
    cache_data = OidcConfigCache(config=oidc_config, updated_at=now, expires_at=expiry)
    logger.info("Updating OIDC config cache")
    await connection.set(OIDC_CONFIG_CACHE_KEY, cache_data.model_dump_json())
    logger.info("OIDC config cached successfully")


async def get_cached_metadata(connection: valkey.Valkey) -> MetadataCache | None:
    cache_data = await connection.get(METADATA_CACHE_KEY)
    if cache_data is None:
        return None
    parsed = MetadataCache.model_validate_json(cache_data)
    now = datetime.now(UTC)
    if now > parsed.expires_at:
        raise ExpiredMetadataError(f"Cached metadata expired at {parsed.expires_at}")
    return parsed


async def get_cached_oidc_config(connection: valkey.Valkey) -> OidcConfigCache | None:
    cache_data = await connection.get(OIDC_CONFIG_CACHE_KEY)
    if cache_data is None:
        return None
    parsed = OidcConfigCache.model_validate_json(cache_data)
    now = datetime.now(UTC)
    if now > parsed.expires_at:
        raise ExpiredMetadataError(f"Cached OIDC config expired at {parsed.expires_at}")
    return parsed
