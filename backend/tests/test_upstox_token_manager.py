import threading
from datetime import datetime as RealDateTime, timedelta

import backend.shared.upstox_token_manager as token_module
from backend.shared.upstox_token_manager import UpstoxTokenManager


class FixedDateTime(RealDateTime):
    current = RealDateTime(2026, 9, 27, 3, 0, 0)

    @classmethod
    def now(cls, tz=None):
        value = cls.current
        if tz is not None:
            return value.replace(tzinfo=tz)
        return value


def bare_manager():
    manager = object.__new__(UpstoxTokenManager)
    manager.refresh_threshold_minutes = 15
    manager._lock = threading.RLock()
    manager.access_token = "existing-token"
    manager.refresh_token = "refresh-token"
    manager.client_id = "client-id"
    manager.client_secret = "client-secret"
    manager.redirect_uri = "http://localhost:3000"
    return manager


def test_missing_expiry_is_treated_as_expired():
    manager = bare_manager()
    manager.token_expiry = None

    assert manager.is_token_expired() is True
    assert manager.needs_daily_token_refresh() is True


def test_token_outside_refresh_window_is_fresh(monkeypatch):
    monkeypatch.setattr(token_module, "datetime", FixedDateTime)
    FixedDateTime.current = RealDateTime(2026, 9, 27, 3, 0, 0)

    manager = bare_manager()
    manager.token_expiry = FixedDateTime.current + timedelta(minutes=16)

    assert manager.is_token_expired() is False


def test_token_at_refresh_threshold_needs_refresh(monkeypatch):
    monkeypatch.setattr(token_module, "datetime", FixedDateTime)
    FixedDateTime.current = RealDateTime(2026, 9, 27, 3, 0, 0)

    manager = bare_manager()
    manager.token_expiry = FixedDateTime.current + timedelta(minutes=15)

    assert manager.is_token_expired() is True


def test_token_from_before_daily_expiry_is_stale_after_330(monkeypatch):
    monkeypatch.setattr(token_module, "datetime", FixedDateTime)
    FixedDateTime.current = RealDateTime(2026, 9, 27, 4, 0, 0)

    manager = bare_manager()
    manager.token_expiry = RealDateTime(2026, 9, 27, 3, 29, 0)

    assert manager.needs_daily_token_refresh() is True
    assert manager.is_token_expired() is True


def test_fresh_token_does_not_trigger_refresh(monkeypatch):
    manager = bare_manager()
    manager.token_expiry = RealDateTime.now() + timedelta(hours=1)

    monkeypatch.setattr(manager, "is_token_expired", lambda: False)
    monkeypatch.setattr(
        manager,
        "refresh_access_token",
        lambda: (_ for _ in ()).throw(AssertionError("refresh should not run")),
    )

    assert manager.get_valid_token() == "existing-token"


def test_expired_token_refreshes_proactively(monkeypatch):
    manager = bare_manager()
    manager.token_expiry = RealDateTime.now() - timedelta(minutes=1)
    refreshed = []

    monkeypatch.setattr(manager, "is_token_expired", lambda: True)
    monkeypatch.setattr(
        manager,
        "refresh_access_token",
        lambda: refreshed.append(True) or True,
    )

    assert manager.get_valid_token() == "existing-token"
    assert refreshed == [True]
