"""Tests for StockDataService."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd

from fin_trade.services.stock_data import StockDataService, PriceContext
from fin_trade.models import Holding


class TestStockDataServiceInit:
    """Tests for StockDataService initialization."""

    def test_creates_data_directory(self, tmp_path):
        """Test creates data directory if it doesn't exist."""
        data_dir = tmp_path / "stock_data"
        assert not data_dir.exists()

        StockDataService(data_dir=data_dir)

        assert data_dir.exists()

    def test_initializes_empty_cache(self, tmp_path):
        """Test initializes with empty in-memory cache."""
        service = StockDataService(data_dir=tmp_path)
        assert service._cache == {}


class TestIsCacheValid:
    """Tests for _is_cache_valid method."""

    def test_returns_false_when_file_not_exists(self, tmp_path):
        """Test returns False when cache file doesn't exist."""
        service = StockDataService(data_dir=tmp_path)
        cache_path = tmp_path / "NONEXISTENT_prices.csv"

        assert service._is_cache_valid(cache_path) is False

    def test_returns_true_for_recent_file(self, tmp_path):
        """Test returns True for recently modified file."""
        service = StockDataService(data_dir=tmp_path)
        cache_path = tmp_path / "RECENT_prices.csv"
        cache_path.write_text("Date,Close\n2024-01-01,100.0")

        assert service._is_cache_valid(cache_path) is True

    def test_returns_false_for_old_file(self, tmp_path):
        """Test returns False for file older than max_age_hours."""
        import os
        import time

        service = StockDataService(data_dir=tmp_path)
        cache_path = tmp_path / "OLD_prices.csv"
        cache_path.write_text("Date,Close\n2024-01-01,100.0")

        # Set modification time to 25 hours ago
        old_time = time.time() - (25 * 3600)
        os.utime(cache_path, (old_time, old_time))

        assert service._is_cache_valid(cache_path, max_age_hours=24) is False


class TestUpdateData:
    """Tests for update_data method."""

    @patch("fin_trade.services.stock_data.yf")
    def test_fetches_and_caches_data(self, mock_yf, tmp_path):
        """Test fetches data from yfinance and saves to cache."""
        # Create mock DataFrame
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        mock_df = pd.DataFrame(
            {"Close": [100.0, 101.0, 102.0, 103.0, 104.0]},
            index=dates,
        )

        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_df
        mock_yf.Ticker.return_value = mock_ticker

        service = StockDataService(data_dir=tmp_path)
        result = service.update_data("TEST")

        assert len(result) == 5
        assert "TEST" in service._cache

        # Check file was created
        cache_path = tmp_path / "TEST_prices.csv"
        assert cache_path.exists()

    @patch("fin_trade.services.stock_data.yf")
    def test_raises_error_for_empty_data(self, mock_yf, tmp_path):
        """Test raises error when no data returned."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame(columns=["Close"])
        mock_yf.Ticker.return_value = mock_ticker

        service = StockDataService(data_dir=tmp_path)

        with pytest.raises((ValueError, RuntimeError)):
            service.update_data("EMPTY")

    @patch("fin_trade.services.stock_data.yf")
    def test_raises_runtime_error_on_api_failure(self, mock_yf, tmp_path):
        """Test raises RuntimeError when API fails."""
        mock_yf.Ticker.side_effect = Exception("API Error")

        service = StockDataService(data_dir=tmp_path)

        with pytest.raises(RuntimeError, match="Failed to fetch data"):
            service.update_data("ERROR")


class TestForceUpdate:
    """Tests for force_update method."""

    @patch("fin_trade.services.stock_data.yf")
    def test_calls_update_data(self, mock_yf, tmp_path):
        """Test force_update delegates to update_data."""
        dates = pd.date_range("2024-01-01", periods=3, freq="D")
        mock_df = pd.DataFrame({"Close": [100.0, 101.0, 102.0]}, index=dates)

        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_df
        mock_yf.Ticker.return_value = mock_ticker

        service = StockDataService(data_dir=tmp_path)
        result = service.force_update("FORCE")

        assert len(result) == 3
        mock_yf.Ticker.assert_called_with("FORCE")


class TestGetHistory:
    """Tests for get_history method."""

    def test_returns_cached_data(self, tmp_path):
        """Test returns data from in-memory cache."""
        service = StockDataService(data_dir=tmp_path)

        # Pre-populate cache with recent dates
        dates = pd.date_range(end=datetime.now(), periods=10, freq="D")
        cached_df = pd.DataFrame({"Close": range(100, 110)}, index=dates)
        service._cache["CACHED"] = cached_df

        result = service.get_history("CACHED", days=365)

        assert len(result) == 10

    def test_loads_from_file_when_not_in_memory(self, tmp_path):
        """Test loads data from CSV file when not in memory cache."""
        # Create a cache file with recent dates
        dates = pd.date_range(end=datetime.now(), periods=5, freq="D")
        df = pd.DataFrame({"Close": [100.0, 101.0, 102.0, 103.0, 104.0]}, index=dates)
        cache_path = tmp_path / "FROMFILE_prices.csv"
        df.to_csv(cache_path)

        service = StockDataService(data_dir=tmp_path)
        result = service.get_history("FROMFILE", days=365)

        assert len(result) == 5
        assert "FROMFILE" in service._cache

    @patch("fin_trade.services.stock_data.yf")
    def test_fetches_when_cache_invalid(self, mock_yf, tmp_path):
        """Test fetches from yfinance when cache is stale."""
        import os
        import time

        # Create an old cache file
        dates = pd.date_range(end=datetime.now(), periods=3, freq="D")
        old_df = pd.DataFrame({"Close": [90.0, 91.0, 92.0]}, index=dates)
        cache_path = tmp_path / "STALE_prices.csv"
        old_df.to_csv(cache_path)

        # Make file old
        old_time = time.time() - (48 * 3600)
        os.utime(cache_path, (old_time, old_time))

        # Mock fresh data
        fresh_dates = pd.date_range(end=datetime.now(), periods=5, freq="D")
        fresh_df = pd.DataFrame({"Close": [100.0, 101.0, 102.0, 103.0, 104.0]}, index=fresh_dates)

        mock_ticker = MagicMock()
        mock_ticker.history.return_value = fresh_df
        mock_yf.Ticker.return_value = mock_ticker

        service = StockDataService(data_dir=tmp_path)
        result = service.get_history("STALE", days=365)

        assert len(result) == 5
        mock_yf.Ticker.assert_called()

    def test_filters_by_days(self, tmp_path):
        """Test filters data to specified number of days."""
        service = StockDataService(data_dir=tmp_path)

        # Create data spanning 30 days ending today
        dates = pd.date_range(end=datetime.now(), periods=30, freq="D")
        df = pd.DataFrame({"Close": range(100, 130)}, index=dates)
        service._cache["FILTER"] = df

        result = service.get_history("FILTER", days=7)

        # Should only have entries from last 7 days (could be 7 or 8 depending on timing)
        assert len(result) <= 8


class TestGetPrice:
    """Tests for get_price method."""

    def test_returns_latest_close_price(self, tmp_path):
        """Test returns the most recent close price."""
        service = StockDataService(data_dir=tmp_path)

        # Create cache with known prices
        dates = pd.date_range(end=datetime.now(), periods=5, freq="D")
        df = pd.DataFrame({"Close": [100.0, 101.0, 102.0, 103.0, 150.0]}, index=dates)
        service._cache["PRICE"] = df

        price = service.get_price("PRICE")

        assert price == 150.0

    def test_raises_error_for_empty_data(self, tmp_path):
        """Test raises error when no price data available."""
        service = StockDataService(data_dir=tmp_path)

        # Empty DataFrame
        service._cache["EMPTY"] = pd.DataFrame(columns=["Close"])

        with pytest.raises(ValueError, match="No price data available"):
            service.get_price("EMPTY")

    def test_uppercases_ticker(self, tmp_path):
        """Test converts ticker to uppercase."""
        service = StockDataService(data_dir=tmp_path)

        dates = pd.date_range(end=datetime.now(), periods=3, freq="D")
        df = pd.DataFrame({"Close": [100.0, 101.0, 102.0]}, index=dates)
        service._cache["UPPER"] = df

        # Call with lowercase
        price = service.get_price("upper")

        assert price == 102.0


class TestCalculateRsi:
    """Tests for _calculate_rsi method."""

    def test_calculates_rsi_correctly(self, tmp_path):
        """Test RSI calculation with known values."""
        service = StockDataService(data_dir=tmp_path)

        # Create a series with alternating gains/losses
        prices = pd.Series([100, 102, 101, 103, 102, 104, 103, 105, 104, 106,
                           105, 107, 106, 108, 107, 109])

        rsi = service._calculate_rsi(prices, period=14)

        # RSI should be between 0 and 100
        assert rsi is not None
        assert 0 <= rsi <= 100

    def test_returns_none_for_insufficient_data(self, tmp_path):
        """Test returns None when not enough data for RSI."""
        service = StockDataService(data_dir=tmp_path)

        # Only 10 prices, need 15 for RSI-14
        prices = pd.Series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109])

        rsi = service._calculate_rsi(prices, period=14)

        assert rsi is None

    def test_returns_100_for_all_gains(self, tmp_path):
        """Test RSI is 100 when all movements are gains."""
        service = StockDataService(data_dir=tmp_path)

        # Monotonically increasing prices
        prices = pd.Series(list(range(100, 120)))

        rsi = service._calculate_rsi(prices, period=14)

        assert rsi == 100.0


class TestCalculateChangePct:
    """Tests for _calculate_change_pct method."""

    def test_calculates_positive_change(self, tmp_path):
        """Test calculates positive percentage change."""
        service = StockDataService(data_dir=tmp_path)

        dates = pd.date_range(end=datetime.now(), periods=10, freq="D")
        df = pd.DataFrame({"Close": [100, 102, 104, 106, 108, 110, 112, 114, 116, 120]}, index=dates)

        change = service._calculate_change_pct(df, 5)

        # Should be positive
        assert change is not None
        assert change > 0

    def test_calculates_negative_change(self, tmp_path):
        """Test calculates negative percentage change."""
        service = StockDataService(data_dir=tmp_path)

        dates = pd.date_range(end=datetime.now(), periods=10, freq="D")
        df = pd.DataFrame({"Close": [120, 118, 116, 114, 112, 110, 108, 106, 104, 100]}, index=dates)

        change = service._calculate_change_pct(df, 5)

        # Should be negative
        assert change is not None
        assert change < 0

    def test_returns_none_for_insufficient_data(self, tmp_path):
        """Test returns None when not enough data."""
        service = StockDataService(data_dir=tmp_path)

        dates = pd.date_range(end=datetime.now(), periods=1, freq="D")
        df = pd.DataFrame({"Close": [100]}, index=dates)

        change = service._calculate_change_pct(df, 5)

        assert change is None


class TestGetPriceContext:
    """Tests for get_price_context method."""

    def test_returns_price_context_object(self, tmp_path):
        """Test returns PriceContext with all fields."""
        service = StockDataService(data_dir=tmp_path)

        # Create mock data with all required columns
        dates = pd.date_range(end=datetime.now(), periods=60, freq="D")
        df = pd.DataFrame({
            "Close": [100 + i for i in range(60)],
            "High": [105 + i for i in range(60)],
            "Low": [95 + i for i in range(60)],
            "Volume": [1000000 for _ in range(60)],
        }, index=dates)
        service._cache["TEST"] = df

        ctx = service.get_price_context("TEST")

        assert isinstance(ctx, PriceContext)
        assert ctx.ticker == "TEST"
        assert ctx.current_price > 0
        assert ctx.change_5d_pct is not None
        assert ctx.change_30d_pct is not None
        assert ctx.high_52w is not None
        assert ctx.low_52w is not None
        assert ctx.rsi_14 is not None
        assert ctx.ma_20 is not None

    def test_to_context_string_includes_price(self, tmp_path):
        """Test context string includes current price."""
        service = StockDataService(data_dir=tmp_path)

        dates = pd.date_range(end=datetime.now(), periods=60, freq="D")
        df = pd.DataFrame({
            "Close": [100 + i * 0.5 for i in range(60)],
            "High": [105 + i * 0.5 for i in range(60)],
            "Low": [95 + i * 0.5 for i in range(60)],
            "Volume": [1000000 for _ in range(60)],
        }, index=dates)
        service._cache["CTX"] = df

        ctx = service.get_price_context("CTX")
        ctx_str = ctx.to_context_string()

        assert "$" in ctx_str  # Has price
        assert "RSI" in ctx_str  # Has RSI

    def test_raises_for_no_data(self, tmp_path):
        """Test raises ValueError when no data available."""
        service = StockDataService(data_dir=tmp_path)
        service._cache["EMPTY"] = pd.DataFrame(columns=["Close"])

        with pytest.raises(ValueError, match="No price data available"):
            service.get_price_context("EMPTY")


class TestGetHoldingsContext:
    """Tests for get_holdings_context method."""

    def test_returns_dict_of_price_contexts(self, tmp_path):
        """Test returns dict mapping tickers to PriceContext."""
        service = StockDataService(data_dir=tmp_path)

        # Create data for two tickers
        dates = pd.date_range(end=datetime.now(), periods=60, freq="D")
        for ticker in ["AAPL", "MSFT"]:
            df = pd.DataFrame({
                "Close": [100 + i for i in range(60)],
                "High": [105 + i for i in range(60)],
                "Low": [95 + i for i in range(60)],
                "Volume": [1000000 for _ in range(60)],
            }, index=dates)
            service._cache[ticker] = df

        result = service.get_holdings_context(["AAPL", "MSFT"])

        assert "AAPL" in result
        assert "MSFT" in result
        assert isinstance(result["AAPL"], PriceContext)
        assert isinstance(result["MSFT"], PriceContext)

    def test_skips_failed_tickers(self, tmp_path):
        """Test skips tickers that fail to fetch."""
        service = StockDataService(data_dir=tmp_path)

        # Only create data for one ticker
        dates = pd.date_range(end=datetime.now(), periods=60, freq="D")
        df = pd.DataFrame({
            "Close": [100 + i for i in range(60)],
            "High": [105 + i for i in range(60)],
            "Low": [95 + i for i in range(60)],
            "Volume": [1000000 for _ in range(60)],
        }, index=dates)
        service._cache["GOOD"] = df
        service._cache["BAD"] = pd.DataFrame(columns=["Close"])  # Empty

        result = service.get_holdings_context(["GOOD", "BAD"])

        assert "GOOD" in result
        assert "BAD" not in result  # Should be skipped


class TestFormatHoldingsForPrompt:
    """Tests for format_holdings_for_prompt method."""

    def test_formats_empty_holdings(self, tmp_path):
        """Test formats empty holdings list."""
        service = StockDataService(data_dir=tmp_path)

        result = service.format_holdings_for_prompt([])

        assert "None (empty portfolio)" in result

    def test_formats_holdings_with_context(self, tmp_path):
        """Test formats holdings with rich context."""
        service = StockDataService(data_dir=tmp_path)

        # Create mock data
        dates = pd.date_range(end=datetime.now(), periods=60, freq="D")
        df = pd.DataFrame({
            "Close": [150 + i * 0.5 for i in range(60)],
            "High": [155 + i * 0.5 for i in range(60)],
            "Low": [145 + i * 0.5 for i in range(60)],
            "Volume": [1000000 for _ in range(60)],
        }, index=dates)
        service._cache["AAPL"] = df

        holdings = [
            Holding(ticker="AAPL",
                name="Apple Inc.",
                quantity=10,
                avg_price=150.0,
            )
        ]

        result = service.format_holdings_for_prompt(holdings)

        assert "AAPL" in result
        assert "Apple Inc." in result
        assert "10 shares" in result
        assert "$150.00" in result  # avg price
        assert "P/L" in result  # gain/loss

    def test_calculates_gain_percentage(self, tmp_path):
        """Test calculates gain percentage correctly."""
        service = StockDataService(data_dir=tmp_path)

        # Create data where current price is 20% above avg
        dates = pd.date_range(end=datetime.now(), periods=60, freq="D")
        df = pd.DataFrame({
            "Close": [180.0 for _ in range(60)],  # Current price = 180
            "High": [185.0 for _ in range(60)],
            "Low": [175.0 for _ in range(60)],
            "Volume": [1000000 for _ in range(60)],
        }, index=dates)
        service._cache["GAIN"] = df

        holdings = [
            Holding(ticker="GAIN",
                name="Gain Stock",
                quantity=10,
                avg_price=150.0,  # 180/150 = 20% gain
            )
        ]

        result = service.format_holdings_for_prompt(holdings)

        assert "+20.0%" in result

    def test_uses_provided_price_contexts(self, tmp_path):
        """Test uses provided price contexts instead of fetching."""
        service = StockDataService(data_dir=tmp_path)

        # Don't add to cache - should use provided context
        price_ctx = PriceContext(
            ticker="TEST",
            current_price=200.0,
            change_5d_pct=5.0,
            change_30d_pct=10.0,
            high_52w=220.0,
            low_52w=180.0,
            pct_from_52w_high=-9.1,
            pct_from_52w_low=11.1,
            rsi_14=55.0,
            volume_avg_20d=1000000.0,
            volume_ratio=1.0,
            ma_20=195.0,
            ma_50=190.0,
            trend_summary="↗+5.0% (5d), above 20-MA",
        )

        holdings = [
            Holding(ticker="TEST",
                name="Test Stock",
                quantity=10,
                avg_price=100.0,
            )
        ]

        result = service.format_holdings_for_prompt(holdings, {"TEST": price_ctx})

        assert "+100.0%" in result  # (200-100)/100 = 100% gain
        assert "$200.00" in result  # Current price from context


class TestPriceContextShortInterest:
    """Tests for short interest formatting in PriceContext."""

    def test_shows_short_interest_when_above_threshold(self):
        """Test shows SI% when above 10%."""
        ctx = PriceContext(
            ticker="GME",
            current_price=25.0,
            change_5d_pct=5.0,
            change_30d_pct=10.0,
            high_52w=30.0,
            low_52w=10.0,
            pct_from_52w_high=-16.7,
            pct_from_52w_low=150.0,
            rsi_14=55.0,
            volume_avg_20d=1000000.0,
            volume_ratio=1.0,
            ma_20=24.0,
            ma_50=22.0,
            trend_summary="↗+5.0% (5d), above 20-MA",
            shares_short=10000000,
            short_ratio=5.5,
            short_percent_float=0.25,  # 25% - above 10% threshold
        )

        ctx_str = ctx.to_context_string()

        assert "SI:" in ctx_str
        assert "25.0%" in ctx_str
        assert "5.5 DTC" in ctx_str  # Days to cover

    def test_hides_short_interest_when_below_threshold(self):
        """Test hides SI% when below 10%."""
        ctx = PriceContext(
            ticker="AAPL",
            current_price=185.0,
            change_5d_pct=2.0,
            change_30d_pct=5.0,
            high_52w=200.0,
            low_52w=150.0,
            pct_from_52w_high=-7.5,
            pct_from_52w_low=23.3,
            rsi_14=60.0,
            volume_avg_20d=50000000.0,
            volume_ratio=1.0,
            ma_20=180.0,
            ma_50=175.0,
            trend_summary="↗+2.0% (5d), above 20-MA",
            shares_short=1000000,
            short_ratio=0.5,
            short_percent_float=0.05,  # 5% - below 10% threshold
        )

        ctx_str = ctx.to_context_string()

        assert "SI:" not in ctx_str  # Should not show

    def test_handles_none_short_interest(self):
        """Test handles None short interest values."""
        ctx = PriceContext(
            ticker="TEST",
            current_price=100.0,
            change_5d_pct=None,
            change_30d_pct=None,
            high_52w=None,
            low_52w=None,
            pct_from_52w_high=None,
            pct_from_52w_low=None,
            rsi_14=None,
            volume_avg_20d=None,
            volume_ratio=None,
            ma_20=None,
            ma_50=None,
            trend_summary="neutral",
            shares_short=None,
            short_ratio=None,
            short_percent_float=None,
        )

        # Should not raise
        ctx_str = ctx.to_context_string()

        assert "$100.00" in ctx_str
        assert "SI:" not in ctx_str
