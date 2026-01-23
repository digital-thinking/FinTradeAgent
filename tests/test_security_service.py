"""Tests for SecurityService."""

import json
import pytest
from unittest.mock import MagicMock, patch

from fin_trade.services.security import SecurityService, Security


class TestSecurityServiceInit:
    """Tests for SecurityService initialization."""

    def test_creates_data_directory(self, tmp_path):
        """Test creates data directory if it doesn't exist."""
        data_dir = tmp_path / "stock_data"
        mock_stock_service = MagicMock()

        assert not data_dir.exists()
        SecurityService(data_dir=data_dir, stock_data_service=mock_stock_service)
        assert data_dir.exists()

    def test_loads_persisted_securities(self, tmp_path):
        """Test loads securities from existing JSON files."""
        data_dir = tmp_path / "stock_data"
        data_dir.mkdir()

        # Create a persisted security file
        security_data = {
            "isin": "US0378331005",
            "ticker": "AAPL",
            "shortName": "Apple Inc.",
        }
        (data_dir / "US0378331005_data.json").write_text(json.dumps(security_data))

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=data_dir, stock_data_service=mock_stock_service)

        # Should have loaded the security
        security = service.get_by_ticker("AAPL")
        assert security is not None
        assert security.isin == "US0378331005"
        assert security.name == "Apple Inc."


class TestGetByIsin:
    """Tests for get_by_isin method."""

    def test_returns_security_when_found(self, tmp_path):
        """Test returns security when ISIN exists."""
        data_dir = tmp_path / "stock_data"
        data_dir.mkdir()

        security_data = {"isin": "US123", "ticker": "TEST", "shortName": "Test Co"}
        (data_dir / "US123_data.json").write_text(json.dumps(security_data))

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=data_dir, stock_data_service=mock_stock_service)

        security = service.get_by_isin("US123")
        assert security is not None
        assert security.ticker == "TEST"

    def test_returns_none_when_not_found(self, tmp_path):
        """Test returns None when ISIN doesn't exist."""
        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=tmp_path, stock_data_service=mock_stock_service)

        assert service.get_by_isin("NONEXISTENT") is None


class TestGetByTicker:
    """Tests for get_by_ticker method."""

    def test_returns_security_when_found(self, tmp_path):
        """Test returns security when ticker exists."""
        data_dir = tmp_path / "stock_data"
        data_dir.mkdir()

        security_data = {"isin": "US123", "ticker": "TEST", "shortName": "Test Co"}
        (data_dir / "US123_data.json").write_text(json.dumps(security_data))

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=data_dir, stock_data_service=mock_stock_service)

        security = service.get_by_ticker("test")  # lowercase should work
        assert security is not None
        assert security.isin == "US123"

    def test_returns_none_when_not_found(self, tmp_path):
        """Test returns None when ticker doesn't exist."""
        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=tmp_path, stock_data_service=mock_stock_service)

        assert service.get_by_ticker("NONEXISTENT") is None


class TestLookupTicker:
    """Tests for lookup_ticker method."""

    def test_returns_cached_security(self, tmp_path):
        """Test returns cached security without API call."""
        data_dir = tmp_path / "stock_data"
        data_dir.mkdir()

        security_data = {"isin": "US123", "ticker": "CACHED", "shortName": "Cached Co"}
        (data_dir / "US123_data.json").write_text(json.dumps(security_data))

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=data_dir, stock_data_service=mock_stock_service)

        with patch("fin_trade.services.security.yf") as mock_yf:
            security = service.lookup_ticker("CACHED")
            mock_yf.Ticker.assert_not_called()

        assert security.isin == "US123"

    @patch("fin_trade.services.security.yf")
    def test_fetches_from_yfinance_when_not_cached(self, mock_yf, tmp_path):
        """Test fetches from yfinance when ticker not in cache."""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "shortName": "New Stock",
            "isin": "US456789",
            "ticker": "NEW",
        }
        mock_yf.Ticker.return_value = mock_ticker

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=tmp_path, stock_data_service=mock_stock_service)

        security = service.lookup_ticker("NEW")

        assert security.ticker == "NEW"
        assert security.name == "New Stock"
        assert security.isin == "US456789"
        mock_yf.Ticker.assert_called_once_with("NEW")

    @patch("fin_trade.services.security.yf")
    def test_uses_unknown_isin_when_not_available(self, mock_yf, tmp_path):
        """Test uses UNKNOWN-{ticker} when no ISIN from yfinance."""
        mock_ticker = MagicMock()
        mock_ticker.info = {"shortName": "Unknown ISIN Stock"}  # No isin field
        mock_yf.Ticker.return_value = mock_ticker

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=tmp_path, stock_data_service=mock_stock_service)

        security = service.lookup_ticker("NOISIN")

        assert security.isin == "UNKNOWN-NOISIN"

    @patch("fin_trade.services.security.yf")
    def test_handles_yfinance_exception(self, mock_yf, tmp_path):
        """Test handles yfinance API errors gracefully."""
        mock_yf.Ticker.side_effect = Exception("API Error")

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=tmp_path, stock_data_service=mock_stock_service)

        security = service.lookup_ticker("ERROR")

        # Should still return a security with UNKNOWN ISIN
        assert security.ticker == "ERROR"
        assert security.isin == "UNKNOWN-ERROR"


class TestGetPrice:
    """Tests for get_price method."""

    def test_delegates_to_stock_data_service(self, tmp_path):
        """Test delegates price lookup to stock data service."""
        mock_stock_service = MagicMock()
        mock_stock_service.get_price.return_value = 150.50

        service = SecurityService(data_dir=tmp_path, stock_data_service=mock_stock_service)
        price = service.get_price("AAPL")

        assert price == 150.50
        mock_stock_service.get_price.assert_called_once_with("AAPL")


class TestForceUpdatePrice:
    """Tests for force_update_price method."""

    def test_calls_force_update_and_get_price(self, tmp_path):
        """Test calls both force_update and get_price on stock data service."""
        mock_stock_service = MagicMock()
        mock_stock_service.get_price.return_value = 200.00

        service = SecurityService(data_dir=tmp_path, stock_data_service=mock_stock_service)
        price = service.force_update_price("MSFT")

        assert price == 200.00
        mock_stock_service.force_update.assert_called_once_with("MSFT")
        mock_stock_service.get_price.assert_called_once_with("MSFT")


class TestUpdateIsin:
    """Tests for update_isin method."""

    def test_updates_existing_security_isin(self, tmp_path):
        """Test updates ISIN for existing security."""
        data_dir = tmp_path / "stock_data"
        data_dir.mkdir()

        # Create security with UNKNOWN ISIN
        security_data = {"isin": "UNKNOWN-TEST", "ticker": "TEST", "shortName": "Test Co"}
        (data_dir / "UNKNOWN-TEST_data.json").write_text(json.dumps(security_data))

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=data_dir, stock_data_service=mock_stock_service)

        # Update with real ISIN
        updated = service.update_isin("TEST", "US123456789")

        assert updated.isin == "US123456789"
        assert updated.ticker == "TEST"

        # Old file should be deleted
        assert not (data_dir / "UNKNOWN-TEST_data.json").exists()

        # New file should exist
        assert (data_dir / "US123456789_data.json").exists()

    def test_creates_new_security_when_not_exists(self, tmp_path):
        """Test creates new security when ticker doesn't exist."""
        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=tmp_path, stock_data_service=mock_stock_service)

        security = service.update_isin("NEWSTOCK", "US999888777")

        assert security.ticker == "NEWSTOCK"
        assert security.isin == "US999888777"
        assert security.name == "NEWSTOCK"  # Falls back to ticker as name


class TestGetFullInfo:
    """Tests for get_full_info method."""

    def test_returns_cached_info(self, tmp_path):
        """Test returns full info from cache."""
        data_dir = tmp_path / "stock_data"
        data_dir.mkdir()

        security_data = {
            "isin": "US123",
            "ticker": "INFO",
            "shortName": "Info Co",
            "sector": "Technology",
        }
        (data_dir / "US123_data.json").write_text(json.dumps(security_data))

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=data_dir, stock_data_service=mock_stock_service)

        info = service.get_full_info("INFO")
        assert info is not None
        assert info["sector"] == "Technology"

    def test_returns_none_when_not_cached(self, tmp_path):
        """Test returns None when no cached info."""
        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=tmp_path, stock_data_service=mock_stock_service)

        assert service.get_full_info("NOCACHE") is None


class TestGetStockInfo:
    """Tests for get_stock_info method."""

    def test_returns_cached_stock_info(self, tmp_path):
        """Test returns formatted stock info from cache."""
        data_dir = tmp_path / "stock_data"
        data_dir.mkdir()

        security_data = {
            "isin": "US123",
            "ticker": "STOCK",
            "shortName": "Stock Co",
            "currency": "EUR",
            "sector": "Finance",
            "industry": "Banking",
            "country": "Germany",
        }
        (data_dir / "US123_data.json").write_text(json.dumps(security_data))

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=data_dir, stock_data_service=mock_stock_service)

        info = service.get_stock_info("STOCK")

        assert info["name"] == "Stock Co"
        assert info["currency"] == "EUR"
        assert info["sector"] == "Finance"
        assert info["country"] == "Germany"

    @patch("fin_trade.services.security.yf")
    def test_fetches_from_yfinance_when_not_cached(self, mock_yf, tmp_path):
        """Test fetches stock info from yfinance when not cached."""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "shortName": "Fetched Stock",
            "isin": "US789",
            "currency": "USD",
            "sector": "Tech",
        }
        mock_yf.Ticker.return_value = mock_ticker

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=tmp_path, stock_data_service=mock_stock_service)

        info = service.get_stock_info("FETCH")

        assert info["name"] == "Fetched Stock"
        assert info["sector"] == "Tech"

    @patch("fin_trade.services.security.yf")
    def test_returns_minimal_info_on_error(self, mock_yf, tmp_path):
        """Test returns minimal info when yfinance fails."""
        mock_yf.Ticker.side_effect = Exception("API Error")

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=tmp_path, stock_data_service=mock_stock_service)

        info = service.get_stock_info("ERRORSTOCK")

        assert info["name"] == "ERRORSTOCK"
        assert info["ticker"] == "ERRORSTOCK"
        assert info["isin"] == "UNKNOWN-ERRORSTOCK"
        assert info["currency"] == "USD"
