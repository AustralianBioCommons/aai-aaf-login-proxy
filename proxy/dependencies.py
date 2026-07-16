from typing import Annotated

import valkey.asyncio as valkey_async
from fastapi import Depends
from loguru import logger

from cache import get_metadata_cache
from config import AppConfig


def get_config():
    return AppConfig()


def get_valkey_connection(
    config: Annotated[AppConfig, Depends(get_config)],
) -> valkey_async.Valkey:
    return valkey_async.Valkey(
        host=config.valkey_host,
        port=config.valkey_port,
        password=config.valkey_password,
    )


async def get_domain_map(
    valkey_connection: Annotated[valkey_async.Valkey, Depends(get_valkey_connection)],
) -> dict[str, str] | None:
    # TODO: retry/fallback behaviour?
    metadata = await get_metadata_cache(connection=valkey_connection)
    if metadata is None:
        logger.warning("Failed to get metadata cache, domain map unavailable")
        return None
    return metadata.domain_map
