from polyfactory.factories.pydantic_factory import ModelFactory

from aaf.metadata import AafProvider
from config import AppConfig


class AafProviderFactory(ModelFactory[AafProvider]):
    __model__ = AafProvider


class AppConfigFactory(ModelFactory[AppConfig]):
    __model__ = AppConfig
