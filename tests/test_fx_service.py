"""Tests for FxService: rate lookup, historical conversion, caching."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from fin_trade.services.fx import FxService


def _mk_history(dates, closes):
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d in dates])
    return pd.DataFrame({"Close": closes}, index=idx)


@pytest.fixture
def fx_service(tmp_path):
    """FxService with an isolated cache directory."""
    return FxService(cache_dir=tmp_path / "fx_cache")


class TestIdentity:
    def test_same_currency_returns_one(self, fx_service):
        assert fx_service.get_rate("USD", "USD") == 1.0

    def test_same_currency_case_insensitive(self, fx_service):
        assert fx_service.get_rate("eur", "EUR") == 1.0

    def test_convert_same_currency_passes_amount_through(self, fx_service):
        assert fx_service.convert(123.45, "USD", "USD") == 123.45

    def test_convert_zero_amount_short_circuits(self, fx_service):
        # Zero should skip FX lookups entirely
        assert fx_service.convert(0.0, "EUR", "GBP") == 0.0


class TestLatestRate:
    def test_returns_latest_close_when_at_is_none(self, fx_service):
        df = _mk_history(
            ["2024-01-02", "2024-01-03", "2024-01-04"],
            [1.10, 1.11, 1.12],
        )
        ticker = MagicMock()
        ticker.history.return_value = df
        with patch("fin_trade.services.fx.yf.Ticker", return_value=ticker):
            rate = fx_service.get_rate("EUR", "USD")
        assert rate == pytest.approx(1.12)

    def test_convert_uses_latest_rate(self, fx_service):
        df = _mk_history(["2024-01-02"], [1.25])
        ticker = MagicMock()
        ticker.history.return_value = df
        with patch("fin_trade.services.fx.yf.Ticker", return_value=ticker):
            result = fx_service.convert(100.0, "EUR", "USD")
        assert result == pytest.approx(125.0)

    def test_uses_short_form_pair_for_usd_to_other(self, fx_service):
        df = _mk_history(["2024-01-02"], [0.85])
        ticker = MagicMock()
        ticker.history.return_value = df
        with patch("fin_trade.services.fx.yf.Ticker", return_value=ticker) as mock_tkr:
            fx_service.get_rate("USD", "EUR")
        # USD→EUR should use EUR=X, not USDEUR=X
        mock_tkr.assert_called_once_with("EUR=X")

    def test_uses_long_form_pair_for_non_usd_base(self, fx_service):
        df = _mk_history(["2024-01-02"], [1.10])
        ticker = MagicMock()
        ticker.history.return_value = df
        with patch("fin_trade.services.fx.yf.Ticker", return_value=ticker) as mock_tkr:
            fx_service.get_rate("EUR", "USD")
        mock_tkr.assert_called_once_with("EURUSD=X")


class TestHistoricalLookup:
    def test_returns_exact_date_close(self, fx_service):
        df = _mk_history(
            ["2024-01-02", "2024-01-03", "2024-01-04"],
            [1.10, 1.11, 1.12],
        )
        ticker = MagicMock()
        ticker.history.return_value = df
        with patch("fin_trade.services.fx.yf.Ticker", return_value=ticker):
            rate = fx_service.get_rate(
                "EUR", "USD", at=datetime(2024, 1, 3)
            )
        assert rate == pytest.approx(1.11)

    def test_weekend_falls_back_to_prior_trading_day(self, fx_service):
        # Friday 2024-01-05, Saturday 2024-01-06, Sunday 2024-01-07, Monday 2024-01-08
        df = _mk_history(
            ["2024-01-04", "2024-01-05", "2024-01-08"],
            [1.10, 1.12, 1.13],
        )
        ticker = MagicMock()
        ticker.history.return_value = df
        with patch("fin_trade.services.fx.yf.Ticker", return_value=ticker):
            # Sunday — should fall back to Friday
            rate = fx_service.get_rate(
                "EUR", "USD", at=datetime(2024, 1, 7)
            )
        assert rate == pytest.approx(1.12)

    def test_date_before_history_uses_earliest_close(self, fx_service):
        df = _mk_history(
            ["2024-01-02", "2024-01-03"],
            [1.10, 1.11],
        )
        ticker = MagicMock()
        ticker.history.return_value = df
        with patch("fin_trade.services.fx.yf.Ticker", return_value=ticker):
            rate = fx_service.get_rate(
                "EUR", "USD", at=datetime(2020, 1, 1)
            )
        assert rate == pytest.approx(1.10)

    def test_timezone_aware_datetime_is_normalized(self, fx_service):
        df = _mk_history(
            ["2024-01-02", "2024-01-03"],
            [1.10, 1.11],
        )
        ticker = MagicMock()
        ticker.history.return_value = df
        with patch("fin_trade.services.fx.yf.Ticker", return_value=ticker):
            rate = fx_service.get_rate(
                "EUR", "USD", at=datetime(2024, 1, 3, 15, tzinfo=timezone.utc)
            )
        assert rate == pytest.approx(1.11)


class TestCrossCurrencyRouting:
    def test_eur_to_gbp_routes_through_usd(self, fx_service):
        # EUR→USD = 1.10, USD→GBP = 0.80 → EUR→GBP = 0.88
        eur_usd = _mk_history(["2024-01-02"], [1.10])
        gbp_from_usd = _mk_history(["2024-01-02"], [0.80])

        def fake_ticker(pair):
            m = MagicMock()
            if pair == "EURUSD=X":
                m.history.return_value = eur_usd
            elif pair == "GBP=X":
                m.history.return_value = gbp_from_usd
            else:
                raise AssertionError(f"Unexpected pair: {pair}")
            return m

        with patch("fin_trade.services.fx.yf.Ticker", side_effect=fake_ticker):
            rate = fx_service.get_rate("EUR", "GBP")
        assert rate == pytest.approx(1.10 * 0.80)

    def test_convert_cross_currency(self, fx_service):
        eur_usd = _mk_history(["2024-01-02"], [1.10])
        gbp_from_usd = _mk_history(["2024-01-02"], [0.80])

        def fake_ticker(pair):
            m = MagicMock()
            m.history.return_value = eur_usd if pair == "EURUSD=X" else gbp_from_usd
            return m

        with patch("fin_trade.services.fx.yf.Ticker", side_effect=fake_ticker):
            result = fx_service.convert(100.0, "EUR", "GBP")
        assert result == pytest.approx(100.0 * 1.10 * 0.80)


class TestCaching:
    def test_second_call_uses_in_memory_cache(self, fx_service):
        df = _mk_history(["2024-01-02"], [1.10])
        ticker = MagicMock()
        ticker.history.return_value = df
        with patch("fin_trade.services.fx.yf.Ticker", return_value=ticker) as mock_tkr:
            fx_service.get_rate("EUR", "USD")
            fx_service.get_rate("EUR", "USD")
        # yfinance should only be hit once thanks to the in-memory cache
        assert mock_tkr.call_count == 1

    def test_writes_csv_to_cache_dir(self, fx_service, tmp_path):
        df = _mk_history(["2024-01-02"], [1.10])
        ticker = MagicMock()
        ticker.history.return_value = df
        with patch("fin_trade.services.fx.yf.Ticker", return_value=ticker):
            fx_service.get_rate("EUR", "USD")
        cache_file = fx_service.cache_dir / "EURUSD_X_prices.csv"
        assert cache_file.exists()

    def test_reads_fresh_csv_without_hitting_yfinance(self, tmp_path):
        # Pre-populate the cache directory with a fresh CSV
        cache_dir = tmp_path / "fx_cache"
        cache_dir.mkdir()
        df = _mk_history(["2024-01-02"], [1.25])
        df.to_csv(cache_dir / "EURUSD_X_prices.csv")

        service = FxService(cache_dir=cache_dir)
        with patch("fin_trade.services.fx.yf.Ticker") as mock_tkr:
            rate = service.get_rate("EUR", "USD")
        assert rate == pytest.approx(1.25)
        mock_tkr.assert_not_called()

    def test_empty_history_raises(self, fx_service):
        ticker = MagicMock()
        ticker.history.return_value = pd.DataFrame()
        with patch("fin_trade.services.fx.yf.Ticker", return_value=ticker):
            with pytest.raises(ValueError, match="No FX data"):
                fx_service.get_rate("EUR", "USD")
