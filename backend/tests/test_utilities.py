"""Focused tests for shared validation and formatting utilities."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.utilities import DataValidator, format_price, get_currency_for_category


@pytest.mark.parametrize(
    ("symbol", "expected"),
    [
        ("AAPL", True),
        (" RELIANCE ", True),
        ("1234567890", True),
        ("", False),
        ("   ", False),
        ("12345678901", False),
        (None, False),
    ],
)
def test_validate_symbol(symbol, expected):
    assert DataValidator.validate_symbol(symbol) is expected


@pytest.mark.parametrize(
    ("price", "expected"),
    [
        (1, True),
        (0.01, True),
        ("12.50", True),
        (0, False),
        (-1, False),
        ("not-a-price", False),
        (None, False),
    ],
)
def test_validate_price(price, expected):
    assert DataValidator.validate_price(price) is expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-09-25", True),
        ("2024-02-29", True),
        ("2025-02-29", False),
        ("25-09-2026", False),
        ("", False),
    ],
)
def test_validate_date_format(value, expected):
    assert DataValidator.validate_date_format(value) is expected


@pytest.mark.parametrize(
    ("price", "currency", "expected"),
    [
        (1234.5, "USD", "$1234.50"),
        (1234.5, "INR", "₹1234.50"),
        (12, "EUR", "12.00 EUR"),
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
        ("", "USD"),
    ],
)
def test_get_currency_for_category(category, expected):
    assert get_currency_for_category(category) == expected
