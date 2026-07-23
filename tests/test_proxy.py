from urllib.parse import parse_qs, urlparse

import pytest

from main import app
from proxy.dependencies import get_oidc_config


@pytest.fixture
def override_oidc_config():
    def _override(oidc_config):
        app.dependency_overrides[get_oidc_config] = lambda: oidc_config

    yield _override
    app.dependency_overrides.pop(get_oidc_config, None)


def get_url_and_query(response):
    """
    Returns the location header, parsed URL, and query parameters from a response.
    """
    location = response.headers["location"]
    parsed = urlparse(location)
    return location, parsed, parse_qs(parsed.query)


def test_authorize_adds_entity_id(test_client, override_domain_map):
    entity_id = "https://idp.sydney.edu.au/idp/shibboleth"
    override_domain_map({"sydney.edu.au": entity_id})

    response = test_client.get(
        "/authorize",
        params={
            "client_id": "test-client",
            "screen_name": "student@sydney.edu.au",
            "entityID": "https://malicious.example/idp",
        },
        follow_redirects=False,
    )

    location, parsed, query = get_url_and_query(response)
    assert response.status_code == 302
    assert response.headers["cache-control"] == "no-store"
    assert location.startswith("https://test.example/oidc/authorize?")
    assert parsed.scheme == "https"
    assert parsed.netloc == "test.example"
    assert parsed.path == "/oidc/authorize"
    assert query["client_id"] == ["test-client"]
    assert query["screen_name"] == ["student@sydney.edu.au"]
    assert query["entityID"] == [entity_id]


def test_authorize_falls_back_when_no_domain_map_available(
    test_client, override_domain_map
):
    override_domain_map(None)

    response = test_client.get(
        "/authorize",
        params={
            "client_id": "test-client",
            "screen_name": "student@sydney.edu.au",
            "entityID": "https://malicious.example/idp",
        },
        follow_redirects=False,
    )

    location, parsed, query = get_url_and_query(response)
    assert response.status_code == 302
    assert location.startswith("https://test.example/oidc/authorize?")
    assert parsed.path == "/oidc/authorize"
    assert query["client_id"] == ["test-client"]
    assert query["screen_name"] == ["student@sydney.edu.au"]
    assert "entityID" not in query


def test_authorize_falls_back_when_no_screen_name_provided(test_client):
    response = test_client.get(
        "/authorize",
        params={
            "client_id": "test-client",
            "entityID": "https://malicious.example/idp",
        },
        follow_redirects=False,
    )

    location, parsed, query = get_url_and_query(response)
    assert response.status_code == 302
    assert location.startswith("https://test.example/oidc/authorize?")
    assert parsed.path == "/oidc/authorize"
    assert query["client_id"] == ["test-client"]
    assert "screen_name" not in query
    assert "entityID" not in query


def test_authorize_falls_back_when_screen_name_is_not_email(
    test_client, override_domain_map
):
    override_domain_map({"sydney.edu.au": "https://idp.sydney.edu.au/idp/shibboleth"})

    response = test_client.get(
        "/authorize",
        params={
            "client_id": "test-client",
            "screen_name": "not-an-email",
            "entityID": "https://malicious.example/idp",
        },
        follow_redirects=False,
    )

    location, parsed, query = get_url_and_query(response)
    assert response.status_code == 302
    assert location.startswith("https://test.example/oidc/authorize?")
    assert parsed.path == "/oidc/authorize"
    assert query["client_id"] == ["test-client"]
    assert query["screen_name"] == ["not-an-email"]
    assert "entityID" not in query


def test_authorize_falls_back_when_entity_id_cannot_be_determined_from_email(
    test_client, override_domain_map
):
    override_domain_map({"sydney.edu.au": "https://idp.sydney.edu.au/idp/shibboleth"})

    response = test_client.get(
        "/authorize",
        params={
            "client_id": "test-client",
            "screen_name": "student@unknown.edu.au",
            "entityID": "https://malicious.example/idp",
        },
        follow_redirects=False,
    )

    location, parsed, query = get_url_and_query(response)
    assert response.status_code == 302
    assert location.startswith("https://test.example/oidc/authorize?")
    assert parsed.path == "/oidc/authorize"
    assert query["client_id"] == ["test-client"]
    assert query["screen_name"] == ["student@unknown.edu.au"]
    assert "entityID" not in query


def test_oidc_config_proxy_returns_cached_config_as_json(
    test_client, override_oidc_config
):
    oidc_config = {
        "issuer": "https://test.example/",
        "authorization_endpoint": "https://proxy.example/authorize",
        "token_endpoint": "https://test.example/oidc/token",
    }
    override_oidc_config(oidc_config)

    response = test_client.get("/.well-known/openid-configuration")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.headers["cache-control"] == "public, max-age=3600"
    assert response.json() == oidc_config


def test_oidc_config_proxy_redirects_to_aaf_when_no_cached_config_available(
    test_client, override_oidc_config, mock_app_config
):
    override_oidc_config(None)

    response = test_client.get(
        "/.well-known/openid-configuration",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == mock_app_config.aaf_oidc_config_url
    assert response.headers["cache-control"] == "no-store"
