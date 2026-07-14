from datetime import datetime, UTC

from loguru import logger
from pydantic import BaseModel, AwareDatetime
import valkey.asyncio as valkey

from aaf.security import get_verified_metadata
from aaf.metadata import get_aaf_metadata
from config import AppConfig

METADATA_CACHE_KEY = "aaf_metadata"


class ExpiredMetadataError(RuntimeError):
    pass


class MetadataCache(BaseModel):
    domain_map: dict[str, str]
    updated_at: AwareDatetime
    expires_at: AwareDatetime


async def update_metadata_cache():
    settings = AppConfig()
    connection = valkey.Valkey(host=settings.valkey_host, port=6379)

    now = datetime.now(UTC)
    metadata_xml = await get_verified_metadata(settings.aaf_metadata_url, settings.aaf_pubkey_url)
    metadata = get_aaf_metadata(metadata_xml)
    cache_data = MetadataCache(domain_map=metadata.domain_map, updated_at=now, expires_at=metadata.expires_at)
    logger.info("Updating metadata cache")
    await connection.set(METADATA_CACHE_KEY, cache_data.model_dump_json())


async def get_metadata_cache(connection: valkey.Valkey):
    cache_data = await connection.get(METADATA_CACHE_KEY)
    if cache_data is None:
        return None
    parsed = MetadataCache.model_validate_json(cache_data)
    now = datetime.now(UTC)
    if now > parsed.expires_at:
        raise ExpiredMetadataError(f"Cached metadata expired at {parsed.expires_at}")
    return parsed




