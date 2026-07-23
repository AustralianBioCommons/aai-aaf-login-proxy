from typing import Annotated

from pydantic import HttpUrl, BeforeValidator
from pydantic_settings import BaseSettings, SettingsConfigDict


def validate_https_url(value: str) -> str:
    parsed = HttpUrl(value)
    if parsed.scheme != "https":
        raise ValueError("URL must use https")
    return str(parsed)


HttpsUrlString = Annotated[str, BeforeValidator(validate_https_url)]


class AppConfig(BaseSettings):
    valkey_host: str = "localhost"
    valkey_port: int = 6379
    valkey_password: str
    aaf_metadata_url: HttpsUrlString
    aaf_pubkey_url: HttpsUrlString
    aaf_oidc_url: HttpsUrlString

    model_config = SettingsConfigDict(env_file=".env")

    @property
    def aaf_authorize_url(self) -> str:
        return f"{self.aaf_oidc_url.rstrip('/')}/oidc/authorize"
