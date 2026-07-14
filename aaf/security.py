import asyncio
from datetime import datetime, timezone

import httpx
from loguru import logger
from lxml.etree import _Element
from signxml import XMLVerifier, SignatureConfiguration

from aaf.xml import NAMESPACES


async def get_metadata_and_pubkey(
    metadata_url: str, pubkey_url: str
) -> tuple[bytes, bytes]:
    async with httpx.AsyncClient(verify=True) as client:
        metadata_response, pubkey_response = await asyncio.gather(
            client.get(metadata_url),
            client.get(pubkey_url),
        )
    metadata_response.raise_for_status()
    pubkey_response.raise_for_status()
    return metadata_response.content, pubkey_response.content


async def get_verified_metadata(
    metadata_url: str,
    pubkey_url: str,
) -> _Element:
    logger.info("Fetching metadata and public key...")
    metadata_bytes, pubkey_bytes = await get_metadata_and_pubkey(
        metadata_url, pubkey_url
    )
    verifier = XMLVerifier()
    config = SignatureConfiguration(location="./", expect_references=1)
    logger.info("Verifying metadata...")
    verified = verifier.verify(
        metadata_bytes,
        # bytes work fine here, ignore the error
        x509_cert=pubkey_bytes, # ty: ignore[invalid-argument-type]
        expect_config=config
    )
    if isinstance(verified, list):
        raise ValueError(f"Got a list from XMLVerifier: {verified}")
    logger.info("Metadata verified")

    verified_root = verified.signed_xml
    if verified_root is None:
        raise ValueError("No signed root found")
    if verified_root.tag != f"{{{NAMESPACES['md']}}}EntitiesDescriptor":
        raise ValueError(f"Unexpected signed root: {verified_root.tag}")

    metadata_id = verified_root.get("ID")
    if not metadata_id:
        raise ValueError("Signed metadata root has no ID")
    print(f"Metadata ID: {metadata_id}")

    valid_until = verified_root.get("validUntil")
    if valid_until:
        expires_at = datetime.fromisoformat(valid_until.replace("Z", "+00:00"))
        if expires_at <= datetime.now(timezone.utc):
            raise ValueError(f"Metadata expired at {valid_until}")
    return verified_root
