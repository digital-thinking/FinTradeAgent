"""Tests for SecurityService."""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from fin_trade.models import AssetClass
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

        # Create a persisted security file (ticker-based naming)
        security_data = {
            "ticker": "AAPL",
            "shortName": "Apple Inc.",
        }
        (data_dir / "AAPL_data.json").write_text(json.dumps(security_data))

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=data_dir, stock_data_service=mock_stock_service)

        # Should have loaded the security
        security = service.get_by_ticker("AAPL")
        assert security is not None
        assert security.ticker == "AAPL"
        assert security.name == "Apple Inc."


class TestGetByTicker:
    """Tests for get_by_ticker method."""

    def test_returns_security_when_found(self, tmp_path):
        """Test returns security when ticker exists."""
        data_dir = tmp_path / "stock_data"
        data_dir.mkdir()

        security_data = {"ticker": "TEST", "shortName": "Test Co"}
        (data_dir / "TEST_data.json").write_text(json.dumps(security_data))

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=data_dir, stock_data_service=mock_stock_service)

        security = service.get_by_ticker("test")  # lowercase should work
        assert security is not None
        assert security.ticker == "TEST"

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

        security_data = {"ticker": "CACHED", "shortName": "Cached Co"}
        (data_dir / "CACHED_data.json").write_text(json.dumps(security_data))

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=data_dir, stock_data_service=mock_stock_service)

        with patch("fin_trade.services.security.yf") as mock_yf:
            security = service.lookup_ticker("CACHED")
            mock_yf.Ticker.assert_not_called()

        assert security.ticker == "CACHED"

    @patch("fin_trade.services.security.yf")
    def test_fetches_from_yfinance_when_not_cached(self, mock_yf, tmp_path):
        """Test fetches from yfinance when ticker not in cache."""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "shortName": "New Stock",
            "ticker": "NEW",
        }
        mock_yf.Ticker.return_value = mock_ticker

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=tmp_path, stock_data_service=mock_stock_service)

        security = service.lookup_ticker("NEW")

        assert security.ticker == "NEW"
        assert security.name == "New Stock"
        mock_yf.Ticker.assert_called_once_with("NEW")

    @patch("fin_trade.services.security.yf")
    def test_yfinance_exception_propagates(self, mock_yf, tmp_path):
        """Test that yfinance API errors propagate (fail fast per CLAUDE.md)."""
        mock_yf.Ticker.side_effect = Exception("API Error")

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=tmp_path, stock_data_service=mock_stock_service)

        with pytest.raises(Exception, match="API Error"):
            service.lookup_ticker("ERROR")


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


class TestGetFullInfo:
    """Tests for get_full_info method."""

    def test_returns_cached_info(self, tmp_path):
        """Test returns full info from cache."""
        data_dir = tmp_path / "stock_data"
        data_dir.mkdir()

        security_data = {
            "ticker": "INFO",
            "shortName": "Info Co",
            "sector": "Technology",
        }
        (data_dir / "INFO_data.json").write_text(json.dumps(security_data))

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
            "ticker": "STOCK",
            "shortName": "Stock Co",
            "currency": "EUR",
            "sector": "Finance",
            "industry": "Banking",
            "country": "Germany",
        }
        (data_dir / "STOCK_data.json").write_text(json.dumps(security_data))

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
    def test_yfinance_error_propagates(self, mock_yf, tmp_path):
        """Test that yfinance errors propagate (fail fast per CLAUDE.md)."""
        mock_yf.Ticker.side_effect = Exception("API Error")

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=tmp_path, stock_data_service=mock_stock_service)

        with pytest.raises(Exception, match="API Error"):
            service.get_stock_info("ERRORSTOCK")

    @patch("fin_trade.services.security.yf")
    def test_uses_fundamentals_ticker_when_provided(self, mock_yf, tmp_path):
        """Test get_stock_info merges fundamentals data from the override ticker."""

        listing_info = {
            "shortName": "ING AS Listing",
            "currency": "EUR",
            "sector": None,
            "industry": None,
            "country": None,
        }
        fundamentals_info = {
            "shortName": "ING Group",
            "currency": "USD",
            "sector": "Financial Services",
            "industry": "Banks—Diversified",
            "country": "Netherlands",
            "marketCap": 100,
        }

        def make_ticker(symbol):
            ticker = MagicMock()
            ticker.info = fundamentals_info if symbol == "ING" else listing_info
            return ticker

        mock_yf.Ticker.side_effect = make_ticker

        mock_stock_service = MagicMock()
        service = SecurityService(
            data_dir=tmp_path,
            stock_data_service=mock_stock_service,
        )

        info = service.get_stock_info("INGA.AS", fundamentals_ticker="ING")

        # Both listings are fetched and cached independently
        called_symbols = {call.args[0] for call in mock_yf.Ticker.call_args_list}
        assert called_symbols == {"INGA.AS", "ING"}

        assert info["ticker"] == "INGA.AS"
        assert info["fundamentals_ticker"] == "ING"
        # Currency is always the listing's native currency
        assert info["currency"] == "EUR"
        # Business fields come from the fundamentals ticker
        assert info["sector"] == "Financial Services"
        assert info["country"] == "Netherlands"
        assert info["marketCap"] == 100

        assert (tmp_path / "INGA.AS_data.json").exists()
        assert (tmp_path / "ING_data.json").exists()

    @patch("fin_trade.services.security.yf")
    def test_lookup_ticker_preloads_fundamentals_symbol(self, mock_yf, tmp_path):
        """lookup_ticker pre-fetches the fundamentals ticker but keeps the listing identity."""
        listing_info = {"shortName": "Cameco Frankfurt", "sector": None}
        fundamentals_info = {"shortName": "Cameco Corporation", "sector": "Energy"}

        def make_ticker(symbol):
            ticker = MagicMock()
            ticker.info = (
                fundamentals_info if symbol == "CCJ" else listing_info
            )
            return ticker

        mock_yf.Ticker.side_effect = make_ticker

        mock_stock_service = MagicMock()
        service = SecurityService(
            data_dir=tmp_path,
            stock_data_service=mock_stock_service,
        )

        security = service.lookup_ticker("CJ6.F", fundamentals_ticker="CCJ")

        # Listing identity is kept — Security.ticker is the traded symbol
        assert security.ticker == "CJ6.F"
        assert security.name == "Cameco Frankfurt"

        # Both symbols cached under their own files
        assert (tmp_path / "CCJ_data.json").exists()
        assert (tmp_path / "CJ6.F_data.json").exists()

        # Subsequent fundamentals lookups return CCJ info
        fundamentals = service.get_full_info("CJ6.F", fundamentals_ticker="CCJ")
        assert fundamentals is not None
        assert fundamentals["sector"] == "Energy"


class TestIsDataStale:
    """Tests for is_data_stale method."""

    def test_returns_true_when_ticker_not_found(self, tmp_path):
        """Test returns True when ticker has no stored data."""
        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=tmp_path, stock_data_service=mock_stock_service)

        assert service.is_data_stale("UNKNOWN") is True

    def test_returns_true_when_no_saved_at(self, tmp_path):
        """Test returns True when _saved_at is missing."""
        data_dir = tmp_path / "stock_data"
        data_dir.mkdir()

        security_data = {"ticker": "TEST", "shortName": "Test"}
        (data_dir / "TEST_data.json").write_text(json.dumps(security_data))

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=data_dir, stock_data_service=mock_stock_service)

        assert service.is_data_stale("TEST") is True

    def test_returns_false_when_data_is_fresh(self, tmp_path):
        """Test returns False when data is within max_age_hours."""
        data_dir = tmp_path / "stock_data"
        data_dir.mkdir()

        security_data = {
            "ticker": "FRESH",
            "shortName": "Fresh Co",
            "_saved_at": datetime.now().isoformat(),
        }
        (data_dir / "FRESH_data.json").write_text(json.dumps(security_data))

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=data_dir, stock_data_service=mock_stock_service)

        assert service.is_data_stale("FRESH") is False

    def test_returns_true_when_data_is_old(self, tmp_path):
        """Test returns True when data is older than max_age_hours."""
        data_dir = tmp_path / "stock_data"
        data_dir.mkdir()

        old_time = datetime.now() - timedelta(hours=48)
        security_data = {
            "ticker": "OLD",
            "shortName": "Old Co",
            "_saved_at": old_time.isoformat(),
        }
        (data_dir / "OLD_data.json").write_text(json.dumps(security_data))

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=data_dir, stock_data_service=mock_stock_service)

        assert service.is_data_stale("OLD", max_age_hours=24) is True


class TestRefreshSecurityData:
    """Tests for refresh_security_data method."""

    @patch("fin_trade.services.security.yf")
    def test_refreshes_and_saves_data(self, mock_yf, tmp_path):
        """Test refreshes data from yfinance and saves to file."""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "shortName": "Refreshed Stock",
            "sector": "Tech",
        }
        mock_yf.Ticker.return_value = mock_ticker

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=tmp_path, stock_data_service=mock_stock_service)

        info = service.refresh_security_data("REFRESH")

        assert info is not None
        assert info["shortName"] == "Refreshed Stock"

        # Should save to file
        data_file = tmp_path / "REFRESH_data.json"
        assert data_file.exists()

    @patch("fin_trade.services.security.yf")
    def test_yfinance_error_propagates(self, mock_yf, tmp_path):
        """Test that yfinance errors propagate (fail fast per CLAUDE.md)."""
        mock_yf.Ticker.side_effect = Exception("API Error")

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=tmp_path, stock_data_service=mock_stock_service)

        with pytest.raises(Exception, match="API Error"):
            service.refresh_security_data("ERROR")


class TestGetShortInterest:
    """Tests for get_short_interest method."""

    def test_returns_short_interest_data(self, tmp_path):
        """Test returns short interest when available."""
        data_dir = tmp_path / "stock_data"
        data_dir.mkdir()

        security_data = {
            "ticker": "GME",
            "shortName": "GameStop",
            "sharesShort": 10000000,
            "shortRatio": 5.5,
            "shortPercentOfFloat": 0.25,
        }
        (data_dir / "GME_data.json").write_text(json.dumps(security_data))

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=data_dir, stock_data_service=mock_stock_service)

        si = service.get_short_interest("GME")
        assert si is not None
        assert si["shares_short"] == 10000000
        assert si["short_ratio"] == 5.5
        assert si["short_percent_float"] == 0.25

    def test_returns_none_when_no_data(self, tmp_path):
        """Test returns None when no short interest data."""
        data_dir = tmp_path / "stock_data"
        data_dir.mkdir()

        security_data = {"ticker": "AAPL", "shortName": "Apple"}
        (data_dir / "AAPL_data.json").write_text(json.dumps(security_data))

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=data_dir, stock_data_service=mock_stock_service)

        assert service.get_short_interest("AAPL") is None


class TestGet52wRange:
    """Tests for get_52w_range method."""

    def test_returns_range_data(self, tmp_path):
        """Test returns 52-week range when available."""
        data_dir = tmp_path / "stock_data"
        data_dir.mkdir()

        security_data = {
            "ticker": "NVDA",
            "shortName": "NVIDIA",
            "fiftyTwoWeekHigh": 212.19,
            "fiftyTwoWeekLow": 86.62,
        }
        (data_dir / "NVDA_data.json").write_text(json.dumps(security_data))

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=data_dir, stock_data_service=mock_stock_service)

        range_data = service.get_52w_range("NVDA")
        assert range_data is not None
        assert range_data["high_52w"] == 212.19
        assert range_data["low_52w"] == 86.62

    def test_returns_range_from_explicit_fundamentals_ticker(self, tmp_path):
        """Test range data resolves through the fundamentals_ticker argument."""
        data_dir = tmp_path / "stock_data"
        data_dir.mkdir()

        security_data = {
            "ticker": "ING",
            "shortName": "ING Group",
            "currency": "USD",
            "fiftyTwoWeekHigh": 25.0,
            "fiftyTwoWeekLow": 15.0,
        }
        (data_dir / "ING_data.json").write_text(json.dumps(security_data))

        mock_stock_service = MagicMock()
        service = SecurityService(
            data_dir=data_dir,
            stock_data_service=mock_stock_service,
        )

        range_data = service.get_52w_range("INGA.AS", fundamentals_ticker="ING")
        assert range_data == {
            "high_52w": 25.0,
            "low_52w": 15.0,
            "currency": "USD",
        }


class TestGetMovingAverages:
    """Tests for get_moving_averages method."""

    def test_returns_ma_data(self, tmp_path):
        """Test returns moving averages when available."""
        data_dir = tmp_path / "stock_data"
        data_dir.mkdir()

        security_data = {
            "ticker": "AAPL",
            "shortName": "Apple",
            "fiftyDayAverage": 180.50,
            "twoHundredDayAverage": 175.25,
        }
        (data_dir / "AAPL_data.json").write_text(json.dumps(security_data))

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=data_dir, stock_data_service=mock_stock_service)

        ma = service.get_moving_averages("AAPL")
        assert ma is not None
        assert ma["ma_50"] == 180.50
        assert ma["ma_200"] == 175.25


class TestGetAnalystData:
    """Tests for get_analyst_data method."""

    def test_returns_analyst_data(self, tmp_path):
        """Test returns analyst ratings when available."""
        data_dir = tmp_path / "stock_data"
        data_dir.mkdir()

        security_data = {
            "ticker": "MSFT",
            "shortName": "Microsoft",
            "targetMeanPrice": 450.0,
            "recommendationKey": "buy",
            "numberOfAnalystOpinions": 35,
        }
        (data_dir / "MSFT_data.json").write_text(json.dumps(security_data))

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=data_dir, stock_data_service=mock_stock_service)

        analyst = service.get_analyst_data("MSFT")
        assert analyst is not None
        assert analyst["target_price"] == 450.0
        assert analyst["recommendation"] == "buy"
        assert analyst["num_analysts"] == 35


class TestGetVolumeData:
    """Tests for get_volume_data method."""

    def test_returns_volume_data(self, tmp_path):
        """Test returns volume metrics when available."""
        data_dir = tmp_path / "stock_data"
        data_dir.mkdir()

        security_data = {
            "ticker": "AMD",
            "shortName": "AMD",
            "averageVolume": 50000000,
            "averageVolume10days": 55000000,
        }
        (data_dir / "AMD_data.json").write_text(json.dumps(security_data))

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=data_dir, stock_data_service=mock_stock_service)

        vol = service.get_volume_data("AMD")
        assert vol is not None
        assert vol["avg_volume"] == 50000000
        assert vol["avg_volume_10d"] == 55000000


class TestGetEarningsTimestamp:
    """Tests for get_earnings_timestamp method."""

    def test_returns_earnings_datetime(self, tmp_path):
        """Test returns earnings timestamp as datetime."""
        data_dir = tmp_path / "stock_data"
        data_dir.mkdir()

        # Timestamp for 2026-01-26 00:00:00 UTC
        security_data = {
            "ticker": "NVDA",
            "shortName": "NVIDIA",
            "earningsTimestamp": 1772053200,
        }
        (data_dir / "NVDA_data.json").write_text(json.dumps(security_data))

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=data_dir, stock_data_service=mock_stock_service)

        earnings = service.get_earnings_timestamp("NVDA")
        assert earnings is not None
        assert isinstance(earnings, datetime)

    def test_returns_none_when_no_earnings(self, tmp_path):
        """Test returns None when no earnings timestamp."""
        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=tmp_path, stock_data_service=mock_stock_service)

        assert service.get_earnings_timestamp("UNKNOWN") is None


class TestGetValuationMetrics:
    """Tests for get_valuation_metrics method."""

    def test_returns_valuation_metrics(self, tmp_path):
        """Test returns valuation metrics when available."""
        data_dir = tmp_path / "stock_data"
        data_dir.mkdir()

        security_data = {
            "ticker": "NVDA",
            "shortName": "NVIDIA",
            "beta": 2.314,
            "trailingPE": 44.58,
            "forwardPE": 23.57,
            "priceToBook": 36.82,
            "marketCap": 4385041022976,
        }
        (data_dir / "NVDA_data.json").write_text(json.dumps(security_data))

        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=data_dir, stock_data_service=mock_stock_service)

        metrics = service.get_valuation_metrics("NVDA")
        assert metrics is not None
        assert metrics["beta"] == 2.314
        assert metrics["pe_trailing"] == 44.58
        assert metrics["pe_forward"] == 23.57


class TestCryptoTickerValidation:
    """Tests for crypto ticker helpers."""

    def test_is_crypto_ticker_true_for_supported_suffixes(self, tmp_path):
        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=tmp_path, stock_data_service=mock_stock_service)

        assert service.is_crypto_ticker("BTC-USD") is True
        assert service.is_crypto_ticker("eth-eur") is True
        assert service.is_crypto_ticker("SOL-GBP") is True

    def test_is_crypto_ticker_false_for_stock_ticker(self, tmp_path):
        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=tmp_path, stock_data_service=mock_stock_service)

        assert service.is_crypto_ticker("AAPL") is False

    def test_validate_ticker_for_crypto_portfolio_rejects_stock(self, tmp_path):
        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=tmp_path, stock_data_service=mock_stock_service)

        with pytest.raises(ValueError, match="not a crypto ticker"):
            service.validate_ticker_for_asset_class("AAPL", AssetClass.CRYPTO)

    def test_validate_ticker_for_stock_portfolio_rejects_crypto(self, tmp_path):
        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=tmp_path, stock_data_service=mock_stock_service)

        with pytest.raises(ValueError, match="crypto ticker"):
            service.validate_ticker_for_asset_class("BTC-USD", AssetClass.STOCKS)

    def test_validate_ticker_for_matching_asset_class_passes(self, tmp_path):
        mock_stock_service = MagicMock()
        service = SecurityService(data_dir=tmp_path, stock_data_service=mock_stock_service)

        assert service.validate_ticker_for_asset_class("AAPL", AssetClass.STOCKS) is True
        assert service.validate_ticker_for_asset_class("BTC-USD", AssetClass.CRYPTO) is True
