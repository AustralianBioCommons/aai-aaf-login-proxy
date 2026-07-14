from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    valkey_host: str = "localhost"
    valkey_port: int = 6379
    aaf_metadata_url: str
    aaf_pubkey_url: str
    aaf_authorize_url: str

    model_config = SettingsConfigDict(env_file=".env")