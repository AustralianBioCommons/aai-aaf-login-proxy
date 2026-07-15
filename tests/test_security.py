from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from lxml import etree
from signxml import XMLSigner
from signxml.exceptions import InvalidSignature

from aaf.security import get_verified_metadata, get_metadata_and_pubkey
from aaf.xml import NAMESPACES


def _certificate_pair() -> tuple[bytes, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "aaf-discovery-test")]
    )
    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(private_key, hashes.SHA256())
    )
    private_key_bytes = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    certificate_pem = certificate.public_bytes(serialization.Encoding.PEM).decode()
    return private_key_bytes, certificate_pem


def _signed_metadata() -> tuple[bytes, bytes]:
    private_key_bytes, certificate_pem = _certificate_pair()
    valid_until = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    root = etree.Element(
        f"{{{NAMESPACES['md']}}}EntitiesDescriptor",
        nsmap={"md": NAMESPACES["md"]},
    )
    root.set("ID", "metadata")
    root.set("validUntil", valid_until)

    signed_root = XMLSigner().sign(
        root,
        key=private_key_bytes,
        cert=certificate_pem,
        reference_uri="#metadata",
    )
    return etree.tostring(signed_root), certificate_pem.encode()


@pytest.mark.asyncio
async def test_get_verified_metadata_verifies_signed_xml_against_public_key(
    monkeypatch,
):
    metadata_bytes, certificate_bytes = _signed_metadata()

    async def fake_get_metadata_and_pubkey(
        metadata_url: str,
        pubkey_url: str,
    ) -> tuple[bytes, bytes]:
        return metadata_bytes, certificate_bytes

    monkeypatch.setattr(
        "aaf.security.get_metadata_and_pubkey",
        fake_get_metadata_and_pubkey,
    )

    verified_root = await get_verified_metadata(
        "https://example.test/metadata.xml",
        "https://example.test/pubkey.pem",
    )

    assert verified_root.tag == f"{{{NAMESPACES['md']}}}EntitiesDescriptor"
    assert verified_root.get("ID") == "metadata"


@pytest.mark.asyncio
async def test_get_verified_metadata_raises_if_signed_xml_is_tampered(monkeypatch):
    metadata_bytes, certificate_bytes = _signed_metadata()
    tampered_root = etree.fromstring(metadata_bytes)
    tampered_root.set(
        "validUntil",
        (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
    )
    tampered_metadata_bytes = etree.tostring(tampered_root)

    async def fake_get_metadata_and_pubkey(
        metadata_url: str,
        pubkey_url: str,
    ) -> tuple[bytes, bytes]:
        return tampered_metadata_bytes, certificate_bytes

    monkeypatch.setattr(
        "aaf.security.get_metadata_and_pubkey",
        fake_get_metadata_and_pubkey,
    )

    with pytest.raises(InvalidSignature):
        await get_verified_metadata(
            "https://example.test/metadata.xml",
            "https://example.test/pubkey.pem",
        )


@pytest.mark.asyncio
async def test_get_metadata_and_pubkey(respx_mock):
    """
    Test get_metadata_and_pubkey calls the expected URLs and returns bytes
    """
    metadata_url = "https://example.test/metadata.xml"
    pubkey_url = "https://example.test/pubkey.pem"
    metadata_content = b"<tag>text</tag>"
    pubkey_content = b"Y2VydGlmaWNhdGUgZXhhbXBsZQo="
    metadata_mock = respx_mock.get(metadata_url).respond(content=metadata_content)
    pubkey_mock = respx_mock.get(pubkey_url).respond(content=pubkey_content)
    result = await get_metadata_and_pubkey(metadata_url, pubkey_url)
    assert result == (metadata_content, pubkey_content)
    assert metadata_mock.called
    assert pubkey_mock.called
