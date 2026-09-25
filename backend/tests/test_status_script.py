import importlib.util
import json
from pathlib import Path

import pytest


STATUS_PATH = Path(__file__).resolve().parents[2] / "status.py"
_spec = importlib.util.spec_from_file_location("stock_price_status", STATUS_PATH)
status = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(status)


def sample_summary():
    return {
        "total_models": 2,
        "completed": 1,
        "failed": 0,
        "pending": 1,
        "models": {
            "Linear Regression": {
                "details": {
                    "status": "completed",
                    "trained": True,
                    "stocks_trained": 12,
                    "r2_score": 0.81234,
                    "trained_date": "2026-09-25 12:00:00",
                    "last_updated": "2026-09-25 12:00:00",
                    "error": "",
                    "error_message": "",
                    "validation_metrics": {"avg_r2_score": 0.81234},
                }
            },
            "KNN": {
                "details": {
                    "status": "pending",
                    "trained": False,
                    "stocks_trained": 0,
                    "r2_score": None,
                    "trained_date": "",
                    "last_updated": "",
                    "error": "",
                    "error_message": "",
                    "validation_metrics": {},
                }
            },
        },
    }


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "N/A"),
        (0.81234, "0.812"),
        (0, "0.0"),
        (-0.25, "-0.2"),
        (1234.5, "1234"),
    ],
)
def test_format_r2_score(value, expected):
    assert status.format_r2_score(value) == expected


def test_get_training_summary_reads_saved_status(tmp_path, monkeypatch):
    models_dir = tmp_path / "backend" / "models"
    models_dir.mkdir(parents=True)
    (models_dir / "model_status.json").write_text(
        json.dumps(
            {
                "linear_regression": {
                    "trained": True,
                    "status": "completed",
                    "stocks_trained": 42,
                    "r2_score": 0.91,
                    "last_updated": "2026-09-25 10:30:00",
                },
                "knn": {
                    "trained": False,
                    "status": "failed",
                    "error_message": "training failed",
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(status, "__file__", str(tmp_path / "status.py"))

    summary = status.get_training_summary()

    assert summary["total_models"] == 7
    assert summary["completed"] == 1
    assert summary["failed"] == 1
    assert summary["pending"] == 5
    linear = summary["models"]["Linear Regression"]["details"]
    assert linear["stocks_trained"] == 42
    assert linear["r2_score"] == 0.91
    assert summary["models"]["KNN"]["details"]["error"] == "training failed"


def test_print_status_table_outputs_model_rows(capsys):
    status.print_status_table(sample_summary())

    output = capsys.readouterr().out
    assert "ML MODEL TRAINING STATUS" in output
    assert "Linear Regression" in output
    assert "0.812" in output
    assert "KNN" in output


def test_print_status_json_emits_parseable_json(capsys):
    status.print_status_json(sample_summary())

    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"] == {
        "total_models": 2,
        "completed": 1,
        "failed": 0,
        "pending": 1,
    }
    assert payload["models"]["Linear Regression"]["trained"] is True
    assert payload["models"]["Linear Regression"]["r2_score"] == 0.81234


def test_print_status_simple_outputs_one_line_per_model(capsys):
    status.print_status_simple(sample_summary())

    output = capsys.readouterr().out
    assert "Models: 1/2 completed, 0 failed, 1 pending" in output
    assert "Linear Regression: 12 stocks, R²=0.812" in output
    assert "KNN: 0 stocks, R²=N/A" in output
