"""Tests for MarketDataService."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from backend.fin_trade.models import AssetClass
from backend.fin_trade.services.market_data import (
    EarningsInfo,
    InsiderTrade,
    MacroData,
    MarketDataService,
    SECFiling,
)


class TestEarningsInfo:
    """Tests for EarningsInfo dataclass."""

    def test_to_context_string_with_full_data(self):
        """Test formatting with all data present."""
        info = EarningsInfo(
            ticker="AAPL",
            earnings_date=datetime(2025, 1, 30),
            eps_estimate=2.50,
            revenue_estimate=120e9,
            days_until_earnings=5,
        )

        result = info.to_context_string()

        assert "AAPL" in result
        assert "2025-01-30" in result
        assert "5 days away" in result
        assert "EPS est: $2.50" in result
        assert "Rev est: $120.00B" in result

    def test_to_context_string_with_no_date(self):
        """Test formatting when no earnings date available."""
        info = EarningsInfo(
            ticker="AAPL",
            earnings_date=None,
            eps_estimate=None,
            revenue_estimate=None,
            days_until_earnings=None,
        )

        result = info.to_context_string()

        assert "AAPL" in result
        assert "No upcoming earnings date available" in result


class TestInsiderTrade:
    """Tests for InsiderTrade dataclass."""

    def test_to_context_string_with_full_data(self):
        """Test formatting with all data present."""
        trade = InsiderTrade(
            ticker="NVDA",
            insider_name="Jensen Huang",
            position="CEO",
            transaction_type="Buy",
            shares=10000,
            value=1500000.0,
            date=datetime(2025, 1, 15),
        )

        result = trade.to_context_string()

        assert "NVDA" in result
        assert "Jensen Huang" in result
        assert "CEO" in result
        assert "Buy" in result
        assert "10,000" in result
        assert "$1,500,000" in result
        assert "2025-01-15" in result

    def test_to_context_string_with_no_value(self):
        """Test formatting when value is None."""
        trade = InsiderTrade(
            ticker="AAPL",
            insider_name="Tim Cook",
            position="CEO",
            transaction_type="Sell",
            shares=5000,
            value=None,
            date=None,
        )

        result = trade.to_context_string()

        assert "N/A" in result
        assert "Unknown date" in result


class TestSECFiling:
    """Tests for SECFiling dataclass."""

    def test_to_context_string(self):
        """Test formatting SEC filing."""
        filing = SECFiling(
            ticker="MSFT",
            filing_type="10-K",
            date=datetime(2025, 1, 20),
            title="Annual Report",
            url="https://sec.gov/...",
        )

        result = filing.to_context_string()

        assert "MSFT" in result
        assert "10-K" in result
        assert "2025-01-20" in result
        assert "Annual Report" in result


class TestMacroData:
    """Tests for MacroData dataclass."""

    def test_to_context_string_with_full_data(self):
        """Test formatting with all data present."""
        macro = MacroData(
            sp500_price=4800.0,
            sp500_change_pct=1.25,
            nasdaq_price=15000.0,
            nasdaq_change_pct=-0.5,
            dow_price=38000.0,
            dow_change_pct=0.75,
            treasury_10y=4.25,
            treasury_2y=4.50,
            vix=15.5,
            timestamp=datetime.now(),
        )

        result = macro.to_context_string()

        assert "MARKET OVERVIEW" in result
        assert "S&P 500" in result
        assert "4,800.00" in result
        assert "+1.25%" in result
        assert "NASDAQ" in result
        assert "DOW" in result
        assert "VIX" in result
        assert "15.50" in result
        assert "INTEREST RATES" in result
        assert "10-Year Treasury" in result
        assert "2-Year Treasury" in result
        assert "Yield Spread" in result
        assert "INVERTED" in result  # Since 2Y > 10Y

    def test_to_context_string_normal_yield_curve(self):
        """Test formatting with normal yield curve."""
        macro = MacroData(
            sp500_price=4800.0,
            sp500_change_pct=1.0,
            nasdaq_price=None,
            nasdaq_change_pct=None,
            dow_price=None,
            dow_change_pct=None,
            treasury_10y=4.50,
            treasury_2y=4.25,
            vix=None,
            timestamp=datetime.now(),
        )

        result = macro.to_context_string()

        assert "INVERTED" not in result


class TestMarketDataServiceInit:
    """Tests for MarketDataService initialization."""

    def test_creates_cache_directory(self, tmp_path):
        """Test creates cache directory if it doesn't exist."""
        cache_dir = tmp_path / "market_data"
        assert not cache_dir.exists()

        MarketDataService(cache_dir=cache_dir)

        assert cache_dir.exists()

    def test_initializes_empty_cache(self, tmp_path):
        """Test initializes with empty in-memory cache."""
        service = MarketDataService(cache_dir=tmp_path)
        assert service._cache == {}


class TestCaching:
    """Tests for caching behavior."""

    def test_cache_validity(self, tmp_path):
        """Test cache validity check."""
        service = MarketDataService(cache_dir=tmp_path)

        # Cache something
        service._set_cached("test_key", "test_data")

        assert service._is_cache_valid("test_key") is True
        assert service._get_cached("test_key") == "test_data"

    def test_cache_invalid_for_missing_key(self, tmp_path):
        """Test cache returns None for missing key."""
        service = MarketDataService(cache_dir=tmp_path)

        assert service._is_cache_valid("nonexistent") is False
        assert service._get_cached("nonexistent") is None


class TestGetEarningsInfo:
    """Tests for get_earnings_info method."""

    @patch("fin_trade.services.market_data.yf")
    def test_fetches_earnings_info(self, mock_yf, tmp_path):
        """Test fetches earnings calendar from yfinance."""
        mock_calendar = pd.DataFrame(
            {
                "Earnings Date": [datetime(2025, 2, 1)],
                "EPS Estimate": [2.50],
                "Revenue Estimate": [100e9],
            }
        ).T
        mock_calendar.columns = [0]

        mock_ticker = MagicMock()
        mock_ticker.calendar = mock_calendar
        mock_yf.Ticker.return_value = mock_ticker

        service = MarketDataService(cache_dir=tmp_path)
        result = service.get_earnings_info("AAPL")

        assert result.ticker == "AAPL"
        mock_yf.Ticker.assert_called_with("AAPL")

    @patch("fin_trade.services.market_data.yf")
    def test_handles_empty_calendar(self, mock_yf, tmp_path):
        """Test handles empty calendar gracefully."""
        mock_ticker = MagicMock()
        mock_ticker.calendar = pd.DataFrame()
        mock_yf.Ticker.return_value = mock_ticker

        service = MarketDataService(cache_dir=tmp_path)
        result = service.get_earnings_info("AAPL")

        assert result.ticker == "AAPL"
        assert result.earnings_date is None

    @patch("fin_trade.services.market_data.yf")
    def test_api_error_propagates(self, mock_yf, tmp_path):
        """Test that API errors propagate (fail fast per CLAUDE.md)."""
        mock_yf.Ticker.side_effect = Exception("API Error")

        service = MarketDataService(cache_dir=tmp_path)

        with pytest.raises(Exception, match="API Error"):
            service.get_earnings_info("AAPL")

    @patch("fin_trade.services.market_data.yf")
    def test_uses_cache(self, mock_yf, tmp_path):
        """Test uses cached data on subsequent calls."""
        mock_ticker = MagicMock()
        mock_ticker.calendar = pd.DataFrame()
        mock_yf.Ticker.return_value = mock_ticker

        service = MarketDataService(cache_dir=tmp_path)

        # First call
        service.get_earnings_info("AAPL")
        # Second call
        service.get_earnings_info("AAPL")

        # Should only call API once
        assert mock_yf.Ticker.call_count == 1


class TestGetInsiderTrades:
    """Tests for get_insider_trades method."""

    @patch("fin_trade.services.market_data.yf")
    def test_fetches_insider_trades(self, mock_yf, tmp_path):
        """Test fetches insider transactions from yfinance."""
        mock_df = pd.DataFrame(
            {
                "Insider": ["Tim Cook", "Jeff Williams"],
                "Position": ["CEO", "COO"],
                "Text": ["Purchase", "Sale"],
                "Shares": [1000, 500],
                "Value": [150000, 75000],
                "Start Date": [datetime(2025, 1, 10), datetime(2025, 1, 8)],
            }
        )

        mock_ticker = MagicMock()
        mock_ticker.insider_transactions = mock_df
        mock_yf.Ticker.return_value = mock_ticker

        service = MarketDataService(cache_dir=tmp_path)
        result = service.get_insider_trades("AAPL", limit=5)

        assert len(result) == 2
        assert result[0].ticker == "AAPL"
        assert result[0].transaction_type == "Buy"
        assert result[1].transaction_type == "Sell"

    @patch("fin_trade.services.market_data.yf")
    def test_handles_empty_insider_data(self, mock_yf, tmp_path):
        """Test handles no insider transactions gracefully."""
        mock_ticker = MagicMock()
        mock_ticker.insider_transactions = pd.DataFrame()
        mock_yf.Ticker.return_value = mock_ticker

        service = MarketDataService(cache_dir=tmp_path)
        result = service.get_insider_trades("AAPL")

        assert result == []


class TestGetSecFilings:
    """Tests for get_sec_filings method."""

    @patch("fin_trade.services.market_data.yf")
    def test_fetches_sec_filings(self, mock_yf, tmp_path):
        """Test fetches SEC filings from yfinance."""
        mock_df = pd.DataFrame(
            {
                "type": ["8-K", "10-Q", "4"],
                "date": [datetime(2025, 1, 15), datetime(2025, 1, 10), datetime(2025, 1, 5)],
                "title": ["Current Report", "Quarterly Report", "Insider Form"],
                "edgarUrl": ["https://...", "https://...", "https://..."],
            }
        )

        mock_ticker = MagicMock()
        mock_ticker.sec_filings = mock_df
        mock_yf.Ticker.return_value = mock_ticker

        service = MarketDataService(cache_dir=tmp_path)
        result = service.get_sec_filings("AAPL", filing_types=["8-K", "10-Q"], limit=5)

        # Should filter out the "4" filing
        assert len(result) == 2
        assert all(f.filing_type in ["8-K", "10-Q"] for f in result)

    @patch("fin_trade.services.market_data.yf")
    def test_handles_list_format(self, mock_yf, tmp_path):
        """Test handles list format from yfinance."""
        mock_filings = [
            {
                "type": "10-K",
                "date": "2025-01-20",
                "title": "Annual Report",
                "edgarUrl": "https://...",
            }
        ]

        mock_ticker = MagicMock()
        mock_ticker.sec_filings = mock_filings
        mock_yf.Ticker.return_value = mock_ticker

        service = MarketDataService(cache_dir=tmp_path)
        result = service.get_sec_filings("AAPL")

        assert len(result) == 1
        assert result[0].filing_type == "10-K"


class TestGetMacroData:
    """Tests for get_macro_data method."""

    @patch("fin_trade.services.market_data.yf")
    def test_fetches_macro_data(self, mock_yf, tmp_path):
        """Test fetches index and treasury data."""

        def mock_ticker_factory(symbol):
            mock = MagicMock()
            dates = pd.date_range("2025-01-20", periods=5, freq="D")
            if symbol == "^GSPC":
                mock.history.return_value = pd.DataFrame(
                    {"Close": [4700, 4720, 4750, 4780, 4800]}, index=dates
                )
            elif symbol == "^IXIC":
                mock.history.return_value = pd.DataFrame(
                    {"Close": [14800, 14850, 14900, 14950, 15000]}, index=dates
                )
            elif symbol == "^DJI":
                mock.history.return_value = pd.DataFrame(
                    {"Close": [37500, 37600, 37700, 37800, 38000]}, index=dates
                )
            elif symbol == "^VIX":
                mock.history.return_value = pd.DataFrame(
                    {"Close": [14, 15, 14.5, 15.5, 15]}, index=dates
                )
            elif symbol == "^TNX":
                mock.history.return_value = pd.DataFrame(
                    {"Close": [4.1, 4.15, 4.2, 4.22, 4.25]}, index=dates
                )
            elif symbol == "^IRX":
                mock.history.return_value = pd.DataFrame(
                    {"Close": [4.4, 4.42, 4.45, 4.48, 4.50]}, index=dates
                )
            else:
                mock.history.return_value = pd.DataFrame()
            return mock

        mock_yf.Ticker.side_effect = mock_ticker_factory

        service = MarketDataService(cache_dir=tmp_path)
        result = service.get_macro_data()

        assert result.sp500_price == 4800
        assert result.nasdaq_price == 15000
        assert result.dow_price == 38000
        assert result.vix == 15
        assert result.treasury_10y == 4.25
        assert result.treasury_2y == 4.50


class TestGetFullContextForHoldings:
    """Tests for get_full_context_for_holdings method."""

    @patch("fin_trade.services.market_data.yf")
    def test_returns_full_context(self, mock_yf, tmp_path):
        """Test returns combined context for multiple holdings."""
        # Create a simple mock that returns empty data for all
        mock_ticker = MagicMock()
        mock_ticker.calendar = pd.DataFrame()
        mock_ticker.insider_transactions = pd.DataFrame()
        mock_ticker.sec_filings = pd.DataFrame()
        mock_ticker.history.return_value = pd.DataFrame(
            {"Close": [100, 101]},
            index=pd.date_range("2025-01-20", periods=2, freq="D"),
        )
        mock_yf.Ticker.return_value = mock_ticker

        service = MarketDataService(cache_dir=tmp_path)
        result = service.get_full_context_for_holdings(["AAPL", "MSFT"])

        # Should at least have market overview
        assert "MARKET OVERVIEW" in result

    def test_returns_placeholder_for_empty_list(self, tmp_path):
        """Test returns placeholder for empty holdings list."""
        service = MarketDataService(cache_dir=tmp_path)

        # Patch the get_macro_data to avoid actual API calls
        with patch.object(service, "get_macro_data") as mock_macro:
            mock_macro.return_value = MacroData(
                sp500_price=4800,
                sp500_change_pct=1.0,
                nasdaq_price=None,
                nasdaq_change_pct=None,
                dow_price=None,
                dow_change_pct=None,
                treasury_10y=None,
                treasury_2y=None,
                vix=None,
                timestamp=datetime.now(),
            )

            result = service.get_full_context_for_holdings([])

            assert "MARKET OVERVIEW" in result


class TestGetHoldingsContextByAssetClass:
    """Tests for asset-class-aware holdings context."""

    def test_crypto_context_skips_stock_specific_calls(self, tmp_path):
        service = MarketDataService(cache_dir=tmp_path)
        service.get_macro_data = MagicMock(return_value=MacroData(
            sp500_price=4800.0,
            sp500_change_pct=1.0,
            nasdaq_price=None,
            nasdaq_change_pct=None,
            dow_price=None,
            dow_change_pct=None,
            treasury_10y=None,
            treasury_2y=None,
            vix=None,
            timestamp=datetime.now(),
        ))
        service.get_earnings_info = MagicMock()
        service.get_sec_filings = MagicMock()
        service.get_insider_trades = MagicMock()

        result = service.get_holdings_context(["BTC-USD"], AssetClass.CRYPTO)

        assert "CRYPTO NOTE" in result
        service.get_earnings_info.assert_not_called()
        service.get_sec_filings.assert_not_called()
        service.get_insider_trades.assert_not_called()

    def test_stock_context_uses_full_context(self, tmp_path):
        service = MarketDataService(cache_dir=tmp_path)
        service.get_full_context_for_holdings = MagicMock(return_value="stock context")

        result = service.get_holdings_context(["AAPL"], AssetClass.STOCKS)

        assert result == "stock context"
        service.get_full_context_for_holdings.assert_called_once_with(["AAPL"])
