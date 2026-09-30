import pytest

from backend.shared.utilities import DataValidator, format_price, get_currency_for_category


@pytest.mark.parametrize(
    ("symbol", "expected"),
    [
        ("AAPL", True),
        (" RELIANCE ", True),
        ("ABCDEFGHIJ", True),
        ("", False),
        ("   ", False),
        ("ABCDEFGHIJK", False),
        (None, False),
        (123, False),
    ],
)
def test_validate_symbol(symbol, expected):
    assert DataValidator.validate_symbol(symbol) is expected


@pytest.mark.parametrize(
    ("price", "expected"),
    [
        (1, True),
        (12.5, True),
        ("99.95", True),
        (0, False),
        (-1, False),
        ("not-a-price", False),
        (None, False),
    ],
)
def test_validate_price(price, expected):
    assert DataValidator.validate_price(price) is expected


@pytest.mark.parametrize(
    ("date_string", "expected"),
    [
        ("2024-02-29", True),
        ("2025-02-29", False),
        ("2026-09-27", True),
        ("27-09-2026", False),
        ("2026/09/27", False),
    ],
)
def test_validate_date_format(date_string, expected):
    assert DataValidator.validate_date_format(date_string) is expected


@pytest.mark.parametrize(
    ("price", "currency", "expected"),
    [
        (123.456, "USD", "$123.46"),
        (123.456, "INR", "₹123.46"),
        (123.456, "EUR", "123.46 EUR"),
    ],
)
def test_format_price(price, currency, expected):
    assert format_price(price, currency) == expected


@pytest.mark.parametrize(
    ("category", "expected"),
    [
        ("us_stocks", "USD"),
        ("ind_stocks", "INR"),
        ("unknown", "USD"),
    ],
)
def test_get_currency_for_category(category, expected):
    assert get_currency_for_category(category) == expected
