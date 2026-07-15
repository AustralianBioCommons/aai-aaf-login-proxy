from tests.datagen import AafProviderFactory

from aaf.metadata import get_domain_entity_map


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
