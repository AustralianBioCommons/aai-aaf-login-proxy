from polyfactory.factories.pydantic_factory import ModelFactory

from aaf.metadata import AafProvider


class AafProviderFactory(ModelFactory[AafProvider]):
    __model__ = AafProvider
