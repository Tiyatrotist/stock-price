import importlib.util
from pathlib import Path


MAIN_PATH = Path(__file__).resolve().parents[1] / "main.py"
_spec = importlib.util.spec_from_file_location("stock_price_backend_main", MAIN_PATH)
backend_main = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(backend_main)


def test_root_exposes_docs_and_health_links():
    client = backend_main.app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert response.get_json() == {
        "service": "Stock Prediction API",
        "documentation": "/docs",
        "health": "/api/health",
    }
