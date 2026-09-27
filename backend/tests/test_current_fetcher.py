import requests

from backend.data_fetching.current_fetcher import CurrentFetcher


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def bare_fetcher():
    fetcher = object.__new__(CurrentFetcher)
    fetcher.finnhub_api_key = "TEST_KEY"
    return fetcher


def test_finnhub_quote_url_and_response_parsing(monkeypatch):
    fetcher = bare_fetcher()
    calls = []

    def fake_get(url, timeout):
        calls.append((url, timeout))
        if "/quote?" in url:
            return FakeResponse({"c": 123.45})
        return FakeResponse({"name": "Apple Inc."})

    monkeypatch.setattr(
        "backend.data_fetching.current_fetcher.requests.get",
        fake_get,
    )

    price, company, data_date = fetcher._fetch_from_finnhub(" aapl ")

    assert price == 123.45
    assert company == "Apple Inc."
    assert data_date is None
    assert calls == [
        (
            "https://finnhub.io/api/v1/quote?symbol=AAPL&token=TEST_KEY",
            10,
        ),
        (
            "https://finnhub.io/api/v1/stock/profile2?symbol=AAPL&token=TEST_KEY",
            10,
        ),
    ]


def test_finnhub_http_error_is_propagated(monkeypatch):
    fetcher = bare_fetcher()

    monkeypatch.setattr(
        "backend.data_fetching.current_fetcher.requests.get",
        lambda *_args, **_kwargs: FakeResponse({}, status_code=429),
    )

    try:
        fetcher._fetch_from_finnhub("AAPL")
    except requests.HTTPError as error:
        assert "429" in str(error)
    else:
        raise AssertionError("expected Finnhub HTTP error to propagate")


def test_finnhub_requires_api_key():
    fetcher = bare_fetcher()
    fetcher.finnhub_api_key = None

    try:
        fetcher._fetch_from_finnhub("AAPL")
    except ValueError as error:
        assert "API key not configured" in str(error)
    else:
        raise AssertionError("expected missing API key to be rejected")
