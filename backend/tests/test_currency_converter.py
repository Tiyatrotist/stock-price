from datetime import datetime

import pytest

from backend.shared.currency_converter import CurrencyConverter


def test_cached_rate_skips_all_network_sources(monkeypatch):
    converter = CurrencyConverter()
    converter.cache = {"rate": 84.25, "timestamp": datetime.now()}

    def unexpected_call():
        raise AssertionError("network source should not be called for a valid cache")

    monkeypatch.setattr(converter, "_fetch_from_forex_python", unexpected_call)
    monkeypatch.setattr(converter, "_fetch_from_exchangerate_api", unexpected_call)
    monkeypatch.setattr(converter, "_fetch_from_yahoo_finance", unexpected_call)

    assert converter.get_live_exchange_rate() == 84.25


def test_fallback_chain_stops_after_first_success(monkeypatch):
    converter = CurrencyConverter()
    yahoo_calls = []

    monkeypatch.setattr(converter, "_fetch_from_forex_python", lambda: None)
    monkeypatch.setattr(converter, "_fetch_from_exchangerate_api", lambda: 84.1)
    monkeypatch.setattr(
        converter,
        "_fetch_from_yahoo_finance",
        lambda: yahoo_calls.append(True) or 85.0,
    )

    assert converter.get_live_exchange_rate() == 84.1
    assert yahoo_calls == []
    assert converter.cache["rate"] == 84.1


def test_yahoo_is_used_after_first_two_sources_fail(monkeypatch):
    converter = CurrencyConverter()

    monkeypatch.setattr(converter, "_fetch_from_forex_python", lambda: None)
    monkeypatch.setattr(converter, "_fetch_from_exchangerate_api", lambda: None)
    monkeypatch.setattr(converter, "_fetch_from_yahoo_finance", lambda: 84.75)

    assert converter.get_live_exchange_rate() == 84.75
    assert converter.cache["rate"] == 84.75


def test_hardcoded_rate_is_used_when_all_sources_fail(monkeypatch):
    converter = CurrencyConverter()

    monkeypatch.setattr(converter, "_fetch_from_forex_python", lambda: None)
    monkeypatch.setattr(converter, "_fetch_from_exchangerate_api", lambda: None)
    monkeypatch.setattr(converter, "_fetch_from_yahoo_finance", lambda: None)

    assert converter.get_live_exchange_rate() == converter.hardcoded_rate


def test_cached_network_result_is_reused(monkeypatch):
    converter = CurrencyConverter()
    calls = []

    monkeypatch.setattr(
        converter,
        "_fetch_from_forex_python",
        lambda: calls.append("forex") or 83.9,
    )
    monkeypatch.setattr(
        converter,
        "_fetch_from_exchangerate_api",
        lambda: pytest.fail("fallback should not be reached"),
    )
    monkeypatch.setattr(
        converter,
        "_fetch_from_yahoo_finance",
        lambda: pytest.fail("fallback should not be reached"),
    )

    assert converter.get_live_exchange_rate() == 83.9
    assert converter.get_live_exchange_rate() == 83.9
    assert calls == ["forex"]
