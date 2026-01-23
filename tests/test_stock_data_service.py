"""Tests for StockDataService."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd

from fin_trade.services.stock_data import StockDataService


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
