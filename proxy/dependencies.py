from typing import Annotated

import valkey.asyncio as valkey_async
from fastapi import Depends
from loguru import logger

from cache import get_cached_metadata, get_cached_oidc_config
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
    metadata = await get_cached_metadata(connection=valkey_connection)
    if metadata is None:
        logger.warning("Failed to get metadata cache, domain map unavailable")
        return None
    return metadata.domain_map


async def get_oidc_config(
    valkey_connection: Annotated[valkey_async.Valkey, Depends(get_valkey_connection)],
):
    config = await get_cached_oidc_config(connection=valkey_connection)
    # TODO: retry/fallback
    # Could fall back to just returning the raw response from upstream OIDC
    if config is None:
        logger.warning("Failed to get oidc config from cache")
        return None
    return config.config
