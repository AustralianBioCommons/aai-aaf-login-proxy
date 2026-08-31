from typing import Annotated

from pydantic import HttpUrl, BeforeValidator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def validate_https_url(value: str) -> str:
    parsed = HttpUrl(value)
    if parsed.scheme != "https":
        raise ValueError("URL must use https")
    return str(parsed)


def validate_allowed_origins(value: str | list[str]) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return value
    origins = []
    for origin in value.split(","):
        origin = origin.strip()
        if origin:
            origins.append(origin)
    return origins


HttpsUrlString = Annotated[str, BeforeValidator(validate_https_url)]


class AppConfig(BaseSettings):
    valkey_host: str = "localhost"
    valkey_port: int = 6379
    valkey_password: str
    aaf_metadata_url: HttpsUrlString
    aaf_pubkey_url: HttpsUrlString
    aaf_oidc_url: HttpsUrlString
    # Full URL to the proxy's authorize endpoint
    proxy_authorize_url: HttpsUrlString
    allowed_origins: Annotated[
        list[str], NoDecode, BeforeValidator(validate_allowed_origins)
    ] = []

    model_config = SettingsConfigDict(env_file=".env")

    @property
    def aaf_authorize_url(self) -> str:
        return f"{self.aaf_oidc_url.rstrip('/')}/oidc/authorize"

    @property
    def aaf_oidc_config_url(self) -> str:
        return f"{self.aaf_oidc_url.rstrip('/')}/.well-known/openid-configuration"
