from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry

from utils.metrics import setup_metrics


def test_setup_metrics_enabled_and_collects_metrics(monkeypatch):
    monkeypatch.setenv("ENABLE_METRICS", "true")
    app = FastAPI()

    @app.get("/ping")
    def ping():
        return {"ok": True}

    setup_metrics(app, registry=CollectorRegistry())
    client = TestClient(app)

    assert client.get("/ping").status_code == 200
    response = client.get("/metrics")

    assert response.status_code == 200
    assert (
        'http_requests_total{handler="/ping",method="GET",status="2xx"}'
        in response.text
    )


def test_setup_metrics_disabled_without_enable_metrics_env(monkeypatch):
    monkeypatch.delenv("ENABLE_METRICS", raising=False)
    app = FastAPI()

    @app.get("/ping")
    def ping():
        return {"ok": True}

    setup_metrics(app, registry=CollectorRegistry())
    client = TestClient(app)

    assert client.get("/ping").status_code == 200
    assert client.get("/metrics").status_code == 404
