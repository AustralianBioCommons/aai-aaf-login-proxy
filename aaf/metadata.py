from collections import defaultdict
from typing import Annotated

from loguru import logger
from lxml import etree
from lxml.etree import _Element
from pydantic import BaseModel, BeforeValidator, AwareDatetime

from aaf.xml import NAMESPACES


def _single_string_validator(value: str | list[str]) -> str:
    """
    XML values might be returned as a list, even if there's only one value.
    If there's only one string value, return it. Otherwise, raise an error.
    """
    if isinstance(value, list):
        if len(value) == 1:
            return value[0]
        else:
            raise ValueError(f"Expected a single string, got {value}")
    return value

SingleString = Annotated[str, BeforeValidator(_single_string_validator)]

class AafMetadata(BaseModel):
    expires_at: AwareDatetime
    providers: dict[str, AafProvider]
    domain_map: dict[str, str]
    errors: dict[str, str]

class AafProvider(BaseModel):
    entity_id: SingleString
    scopes: list[str]
    organization_name: SingleString
    organization_display_name: SingleString


class DomainMapResult(BaseModel):
    """
    Returned by get_domain_entity_map
    """
    domain_map: dict[str, str]
    errors: dict[str, str]

def get_identity_providers(root: _Element) -> list[etree.Element]:
    """
    Find identity providers: entities with an IDPSSODescriptor
    """
    return root.xpath(
        "//md:EntityDescriptor[md:IDPSSODescriptor]",
        namespaces=NAMESPACES,
    )


def get_provider_info(idp: etree.Element) -> AafProvider:
    paths = {
        "entity_id": "string(./@entityID)",
        "scopes": "./md:IDPSSODescriptor/md:Extensions/shibmd:Scope/text()",
        "organization_name": "string(./md:Organization/md:OrganizationName[@xml:lang='en'])",
        "organization_display_name": "string(./md:Organization/md:OrganizationDisplayName[@xml:lang='en'])",
        "idp_display_name": "string(./md:IDPSSODescriptor/md:Extensions/mdui:UIInfo/mdui:DisplayName[@xml:lang='en'])",
    }
    values = {key: idp.xpath(path, namespaces=NAMESPACES)
              for key, path in paths.items()}
    return AafProvider(**values)



def get_domain_entity_map(providers: dict[str, AafProvider]) -> DomainMapResult:
    """
    Map scopes (domains) to entity IDs. In AAF production, these are unique (which is what we want),
    but in test we need to allow duplicates
    """
    domain_entities = defaultdict(set)

    for entity_id, provider in providers.items():
        for scope in provider.scopes:
            domain_entities[scope].add(entity_id)

    domain_map = {}
    errors = {}
    for scope, entity_ids in domain_entities.items():
        if len(entity_ids) == 1:
            domain_map[scope] = entity_ids.pop()
        if len(entity_ids) > 1:
            errors[scope] = f"Multiple entity IDs for {scope}: {entity_ids}"
    return DomainMapResult(domain_map=domain_map, errors=errors)


def get_aaf_metadata(verified_xml: _Element) -> AafMetadata:
    """
    Parse the AAF metadata and return info about the identity providers and their
    AAF entity IDs.

    You must verify the metadata against AAF's public key before calling this function -
    use security.get_verified_metadata
    """
    providers = get_identity_providers(verified_xml)
    provider_info = {}
    for idp in providers:
        idp_info = get_provider_info(idp)
        provider_info[idp_info.entity_id] = idp_info

    domain_map_result = get_domain_entity_map(provider_info)
    if domain_map_result.errors:
        logger.warning(f"Duplicate entity IDs found: {domain_map_result.errors}")
    expiry = verified_xml.get("validUntil")
    return AafMetadata(
        expires_at=expiry,
        providers=provider_info,
        domain_map=domain_map_result.domain_map,
        errors=domain_map_result.errors
    )