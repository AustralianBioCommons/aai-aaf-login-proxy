from prometheus_client.registry import CollectorRegistry
from prometheus_fastapi_instrumentator import Instrumentator


def setup_metrics(app, registry: CollectorRegistry | None = None) -> Instrumentator:
    instrumentator = Instrumentator(
        should_respect_env_var=True,
        env_var_name="ENABLE_METRICS",
        registry=registry,
    )
    instrumentator.instrument(app).expose(app)
    return instrumentator
