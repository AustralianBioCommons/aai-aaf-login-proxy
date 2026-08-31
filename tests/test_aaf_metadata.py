from httpx import Response
from lxml import etree
import pytest

from tests.datagen import AafProviderFactory

from aaf.metadata import (
    _single_string_validator,
    fetch_oidc_configuration,
    get_all_domains,
    get_overridden_oidc_configuration,
)
from aaf.metadata import get_aaf_metadata, get_domain_entity_map, get_identity_providers
from aaf.metadata import get_provider_info
from aaf.xml import NAMESPACES


def _minimal_metadata_xml():
    root = etree.Element(
        f"{{{NAMESPACES['md']}}}EntitiesDescriptor",
        nsmap={
            "md": NAMESPACES["md"],
            "shibmd": NAMESPACES["shibmd"],
            "mdui": NAMESPACES["mdui"],
        },
    )
    root.set("validUntil", "2099-01-01T00:00:00+00:00")

    idp = etree.SubElement(root, f"{{{NAMESPACES['md']}}}EntityDescriptor")
    idp.set("entityID", "https://idp.example.edu.au/idp/shibboleth")

    idp_descriptor = etree.SubElement(idp, f"{{{NAMESPACES['md']}}}IDPSSODescriptor")
    extensions = etree.SubElement(idp_descriptor, f"{{{NAMESPACES['md']}}}Extensions")
    scope = etree.SubElement(extensions, f"{{{NAMESPACES['shibmd']}}}Scope")
    scope.text = "example.edu.au"

    ui_info = etree.SubElement(extensions, f"{{{NAMESPACES['mdui']}}}UIInfo")
    display_name = etree.SubElement(
        ui_info,
        f"{{{NAMESPACES['mdui']}}}DisplayName",
        {f"{{{NAMESPACES['xml']}}}lang": "en"},
    )
    display_name.text = "Example University"

    organization = etree.SubElement(idp, f"{{{NAMESPACES['md']}}}Organization")
    organization_name = etree.SubElement(
        organization,
        f"{{{NAMESPACES['md']}}}OrganizationName",
        {f"{{{NAMESPACES['xml']}}}lang": "en"},
    )
    organization_name.text = "Example University"
    organization_display_name = etree.SubElement(
        organization,
        f"{{{NAMESPACES['md']}}}OrganizationDisplayName",
        {f"{{{NAMESPACES['xml']}}}lang": "en"},
    )
    organization_display_name.text = "Example Uni"

    non_idp = etree.SubElement(root, f"{{{NAMESPACES['md']}}}EntityDescriptor")
    non_idp.set("entityID", "https://sp.example.edu.au/sp")

    return root


def _add_idp(root, entity_id: str, scope: str):
    idp = etree.SubElement(root, f"{{{NAMESPACES['md']}}}EntityDescriptor")
    idp.set("entityID", entity_id)

    idp_descriptor = etree.SubElement(idp, f"{{{NAMESPACES['md']}}}IDPSSODescriptor")
    extensions = etree.SubElement(idp_descriptor, f"{{{NAMESPACES['md']}}}Extensions")
    scope_element = etree.SubElement(extensions, f"{{{NAMESPACES['shibmd']}}}Scope")
    scope_element.text = scope

    organization = etree.SubElement(idp, f"{{{NAMESPACES['md']}}}Organization")
    organization_name = etree.SubElement(
        organization,
        f"{{{NAMESPACES['md']}}}OrganizationName",
        {f"{{{NAMESPACES['xml']}}}lang": "en"},
    )
    organization_name.text = "Example University"
    organization_display_name = etree.SubElement(
        organization,
        f"{{{NAMESPACES['md']}}}OrganizationDisplayName",
        {f"{{{NAMESPACES['xml']}}}lang": "en"},
    )
    organization_display_name.text = "Example Uni"


def test_get_identity_providers_returns_only_idp_entities():
    root = _minimal_metadata_xml()

    result = get_identity_providers(root)

    assert len(result) == 1
    assert result[0].get("entityID") == "https://idp.example.edu.au/idp/shibboleth"


def test_get_provider_info_parses_idp_entity_details():
    idp = get_identity_providers(_minimal_metadata_xml())[0]

    result = get_provider_info(idp)

    assert result.entity_id == "https://idp.example.edu.au/idp/shibboleth"
    assert result.scopes == ["example.edu.au"]
    assert result.organization_name == "Example University"
    assert result.organization_display_name == "Example Uni"


def test_get_aaf_metadata_parses_metadata_document():
    root = _minimal_metadata_xml()

    result = get_aaf_metadata(root)

    assert result.expires_at.isoformat() == "2099-01-01T00:00:00+00:00"
    assert set(result.providers) == {"https://idp.example.edu.au/idp/shibboleth"}
    assert result.domain_map == {
        "example.edu.au": "https://idp.example.edu.au/idp/shibboleth"
    }
    assert result.errors == {}


def test_get_aaf_metadata_logs_duplicate_domain_errors(mocker):
    root = _minimal_metadata_xml()
    _add_idp(
        root,
        entity_id="https://second-idp.example.edu.au/idp/shibboleth",
        scope="example.edu.au",
    )
    logger_warning = mocker.patch("aaf.metadata.logger.warning")

    result = get_aaf_metadata(root)

    assert result.domain_map == {}
    assert set(result.errors) == {"example.edu.au"}
    logger_warning.assert_called_once()
    assert "Duplicate entity IDs found" in logger_warning.call_args.args[0]


def test_get_aaf_metadata_raises_when_valid_until_is_missing():
    root = _minimal_metadata_xml()
    root.attrib.pop("validUntil")

    with pytest.raises(ValueError, match="validUntil"):
        get_aaf_metadata(root)


def test_single_string_validator_returns_only_list_item():
    assert _single_string_validator(["Example University"]) == "Example University"


def test_single_string_validator_raises_for_multiple_list_items():
    with pytest.raises(ValueError, match="Expected a single string"):
        _single_string_validator(["Example University", "Example College"])


def test_get_domain_entity_map_maps_unique_domains():
    providers = {
        "https://idp.example.edu.au/idp/shibboleth": AafProviderFactory.build(
            scopes=["example.edu.au"],
        ),
        "https://idp.example.org/idp/shibboleth": AafProviderFactory.build(
            scopes=["example.org"],
        ),
    }

    result = get_domain_entity_map(providers)

    assert result.domain_map == {
        "example.edu.au": "https://idp.example.edu.au/idp/shibboleth",
        "example.org": "https://idp.example.org/idp/shibboleth",
    }
    assert result.errors == {}


def test_get_domain_entity_map_adds_duplicate_domains_to_errors():
    providers = {
        "https://idp-one.example.edu.au/idp/shibboleth": AafProviderFactory.build(
            scopes=["example.edu.au"],
        ),
        "https://idp-two.example.edu.au/idp/shibboleth": AafProviderFactory.build(
            scopes=["example.edu.au"],
        ),
    }

    result = get_domain_entity_map(providers)

    assert result.domain_map == {}
    assert set(result.errors) == {"example.edu.au"}
    assert "Multiple entity IDs for example.edu.au" in result.errors["example.edu.au"]
    assert (
        "https://idp-one.example.edu.au/idp/shibboleth"
        in result.errors["example.edu.au"]
    )
    assert (
        "https://idp-two.example.edu.au/idp/shibboleth"
        in result.errors["example.edu.au"]
    )


def test_get_all_domains_returns_unique_sorted_domains():
    providers = {
        "https://idp-one.example.edu.au/idp/shibboleth": AafProviderFactory.build(
            scopes=["z.example.edu.au", "a.example.edu.au", "z.example.edu.au"],
        ),
        "https://idp-two.example.edu.au/idp/shibboleth": AafProviderFactory.build(
            scopes=["m.example.edu.au", "a.example.edu.au"],
        ),
    }

    result = get_all_domains(providers)

    assert result == [
        "a.example.edu.au",
        "m.example.edu.au",
        "z.example.edu.au",
    ]


@pytest.mark.asyncio
async def test_fetch_oidc_configuration(mock_app_config, respx_mock):
    request = respx_mock.get(mock_app_config.aaf_oidc_config_url)
    mock_data = {"issuer": "https://example.org"}
    request.return_value = Response(status_code=200, json=mock_data)
    resp = await fetch_oidc_configuration(mock_app_config)
    assert resp == mock_data
    assert request.called


@pytest.mark.asyncio
async def test_get_overridden_oidc_configuration_overrides_authorization_endpoint(
    mock_app_config, mocker
):
    """
    Test get_overridden_oidc_configuration overrides authorization_endpoint,
    but not other fields
    """
    upstream_config = {
        "issuer": "https://test.example/",
        "authorization_endpoint": "https://test.example/oidc/authorize",
        "token_endpoint": "https://test.example/oidc/token",
    }
    fetch_oidc_configuration_mock = mocker.patch(
        "aaf.metadata.fetch_oidc_configuration",
        new=mocker.AsyncMock(return_value=upstream_config),
    )

    result = await get_overridden_oidc_configuration(mock_app_config)

    assert result["authorization_endpoint"] == mock_app_config.proxy_authorize_url
    assert result["issuer"] == upstream_config["issuer"]
    assert result["token_endpoint"] == upstream_config["token_endpoint"]
    fetch_oidc_configuration_mock.assert_awaited_once_with(mock_app_config)
