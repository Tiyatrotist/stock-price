from pathlib import Path

import pandas as pd

from backend.shared.index_manager import DynamicIndexManager


COLUMNS = [
    "symbol",
    "company_name",
    "sector",
    "market_cap",
    "headquarters",
    "exchange",
]


def write_permanent_index(root: Path, category: str, rows: list[dict]) -> None:
    path = root / "permanent" / category / f"index_{category}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=COLUMNS).to_csv(path, index=False)


def manager_for(tmp_path: Path) -> DynamicIndexManager:
    data_dir = tmp_path / "backend" / "data"
    data_dir.mkdir(parents=True)
    return DynamicIndexManager(str(data_dir))


def test_corrupt_dynamic_index_recovers_from_permanent(tmp_path):
    write_permanent_index(
        tmp_path,
        "us_stocks",
        [
            {
                "symbol": "AAPL",
                "company_name": "Apple",
                "sector": "Technology",
                "market_cap": "large",
                "headquarters": "Cupertino",
                "exchange": "NASDAQ",
            }
        ],
    )
    manager = manager_for(tmp_path)
    dynamic = Path(manager.us_index_path)
    dynamic.write_text('symbol,company_name\n"AAPL,broken', encoding="utf-8")

    recovered = manager._read_csv_safely("us_stocks")

    assert recovered["symbol"].tolist() == ["AAPL"]
    assert recovered["currency"].tolist() == ["USD"]
    assert dynamic.exists()


def test_add_stock_keeps_unique_symbols_and_sorted_order(tmp_path):
    write_permanent_index(
        tmp_path,
        "us_stocks",
        [
            {
                "symbol": "MSFT",
                "company_name": "Microsoft",
                "sector": "Technology",
                "market_cap": "large",
                "headquarters": "Redmond",
                "exchange": "NASDAQ",
            }
        ],
    )
    manager = manager_for(tmp_path)
    assert manager.initialize_from_permanent("us_stocks") is True

    manager.add_stock(
        "AAPL",
        {
            "company_name": "Apple",
            "sector": "Technology",
            "market_cap": "large",
            "headquarters": "Cupertino",
            "exchange": "NASDAQ",
        },
        "us_stocks",
    )
    manager.add_stock(
        "aapl",
        {"company_name": "Duplicate Apple"},
        "us_stocks",
    )

    saved = pd.read_csv(manager.us_index_path)
    assert saved["symbol"].tolist() == ["AAPL", "MSFT"]
    assert saved["symbol"].str.upper().is_unique
