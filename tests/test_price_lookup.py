"""Tests for price lookup tools."""

import pytest
from unittest.mock import MagicMock, patch

from fin_trade.agents.tools.price_lookup import (
    extract_tickers_from_text,
    fetch_buy_candidate_data,
    format_buy_candidates_for_prompt,
    get_stock_price,
    get_stock_prices,
)


class TestExtractTickersFromText:
    """Tests for extract_tickers_from_text function."""

    def test_extracts_simple_tickers(self):
        """Test extraction of simple ticker symbols."""
        text = "I recommend buying AAPL and MSFT for growth potential."
        tickers = extract_tickers_from_text(text)

        assert "AAPL" in tickers
        assert "MSFT" in tickers

    def test_extracts_tickers_with_exchange_suffix(self):
        """Test extraction of tickers with exchange suffix."""
        text = "Consider SAP.DE and BAS.DE for European exposure."
        tickers = extract_tickers_from_text(text)

        assert "SAP.DE" in tickers
        assert "BAS.DE" in tickers

    def test_extracts_crypto_tickers_with_quote_suffix(self):
        """Test extraction of crypto tickers with fiat quote suffix."""
        text = "Momentum is strongest in BTC-USD and ETH-USD today."
        tickers = extract_tickers_from_text(text)

        assert "BTC-USD" in tickers
        assert "ETH-USD" in tickers

    def test_excludes_common_words(self):
        """Test that common words are excluded."""
        text = "THE BUY signal for NVDA is strong AND NOT to be ignored."
        tickers = extract_tickers_from_text(text)

        assert "THE" not in tickers
        assert "BUY" not in tickers
        assert "AND" not in tickers
        assert "NOT" not in tickers
        assert "NVDA" in tickers

    def test_excludes_financial_acronyms(self):
        """Test that financial acronyms are excluded."""
        text = "The EPS and RSI for GOOGL indicate momentum. FED policy affects USD."
        tickers = extract_tickers_from_text(text)

        assert "EPS" not in tickers
        assert "RSI" not in tickers
        assert "FED" not in tickers
        assert "USD" not in tickers
        assert "GOOGL" in tickers

    def test_deduplicates_tickers(self):
        """Test that duplicate tickers are removed."""
        text = "AAPL is strong. Buy AAPL now. AAPL to the moon!"
        tickers = extract_tickers_from_text(text)

        assert tickers.count("AAPL") == 1

    def test_handles_empty_text(self):
        """Test handling of empty text."""
        tickers = extract_tickers_from_text("")

        assert tickers == []

    def test_handles_no_tickers(self):
        """Test handling of text without tickers."""
        text = "The market is doing well today with good economic data."
        tickers = extract_tickers_from_text(text)

        # Should only contain uppercase words that aren't excluded
        # In this case, there are no valid tickers
        assert len(tickers) == 0

    def test_extracts_single_letter_tickers(self):
        """Test extraction of single letter tickers (like V for Visa)."""
        text = "Consider V for payments exposure."
        tickers = extract_tickers_from_text(text)

        assert "V" in tickers


class TestFetchBuyCandidateData:
    """Tests for fetch_buy_candidate_data function."""

    def test_fetches_data_for_valid_tickers(self):
        """Test fetching data for valid tickers."""
        mock_security = MagicMock()
        mock_security.name = "Apple Inc."

        mock_service = MagicMock()
        mock_service.lookup_ticker.return_value = mock_security
        mock_service.get_price.return_value = 185.50
        mock_service.get_full_info.return_value = {
            "bid": 185.45,
            "ask": 185.55,
        }

        result = fetch_buy_candidate_data(["AAPL"], mock_service)

        assert "AAPL" in result
        assert result["AAPL"]["name"] == "Apple Inc."
        assert result["AAPL"]["price"] == 185.50
        assert result["AAPL"]["bid"] == 185.45
        assert result["AAPL"]["ask"] == 185.55

    def test_skips_failed_lookups(self):
        """Test that failed lookups are skipped."""
        mock_service = MagicMock()
        mock_service.lookup_ticker.side_effect = Exception("Ticker not found")

        result = fetch_buy_candidate_data(["INVALID"], mock_service)

        assert result == {}

    def test_handles_missing_price(self):
        """Test handling when price lookup fails."""
        mock_security = MagicMock()
        mock_security.name = "Unknown Corp"

        mock_service = MagicMock()
        mock_service.lookup_ticker.return_value = mock_security
        mock_service.get_price.side_effect = Exception("Price not available")
        mock_service.get_full_info.return_value = {}

        result = fetch_buy_candidate_data(["XYZ"], mock_service)

        assert "XYZ" in result
        assert result["XYZ"]["price"] is None

    def test_handles_missing_bid_ask(self):
        """Test handling when bid/ask not available."""
        mock_security = MagicMock()
        mock_security.name = "Test Corp"

        mock_service = MagicMock()
        mock_service.lookup_ticker.return_value = mock_security
        mock_service.get_price.return_value = 100.0
        mock_service.get_full_info.return_value = {}  # No bid/ask

        result = fetch_buy_candidate_data(["TEST"], mock_service)

        assert result["TEST"]["bid"] is None
        assert result["TEST"]["ask"] is None


class TestFormatBuyCandidatesForPrompt:
    """Tests for format_buy_candidates_for_prompt function."""

    def test_formats_candidates_with_bid_ask(self):
        """Test formatting candidates with bid/ask spread."""
        candidates = {
            "AAPL": {
                "name": "Apple Inc.",
                "price": 185.50,
                "bid": 185.40,
                "ask": 185.60,
            }
        }

        result = format_buy_candidates_for_prompt(candidates)

        assert "BUY CANDIDATE PRICES" in result
        assert "AAPL" in result
        assert "Apple Inc." in result
        assert "$185.50" in result
        assert "bid $185.40" in result
        assert "ask $185.60" in result

    def test_formats_candidates_without_bid_ask(self):
        """Test formatting candidates without bid/ask."""
        candidates = {
            "MSFT": {
                "name": "Microsoft Corp.",
                "price": 420.00,
                "bid": None,
                "ask": None,
            }
        }

        result = format_buy_candidates_for_prompt(candidates)

        assert "MSFT" in result
        assert "$420.00" in result
        assert "bid" not in result  # No bid/ask section

    def test_returns_empty_for_no_candidates(self):
        """Test that empty dict returns empty string."""
        result = format_buy_candidates_for_prompt({})

        assert result == ""

    def test_skips_candidates_without_price(self):
        """Test that candidates without price are skipped."""
        candidates = {
            "NOPRICE": {
                "name": "No Price Corp",
                "price": None,
                "bid": None,
                "ask": None,
            }
        }

        result = format_buy_candidates_for_prompt(candidates)

        # Should be empty since no valid candidates
        assert result == ""


class TestGetStockPrice:
    """Tests for get_stock_price function."""

    def test_returns_price_from_service(self):
        """Test that price is returned from security service."""
        mock_service = MagicMock()
        mock_service.get_price.return_value = 150.25

        result = get_stock_price("AAPL", mock_service)

        assert result == 150.25
        mock_service.get_price.assert_called_once_with("AAPL")

    def test_creates_service_if_not_provided(self):
        """Test that SecurityService is created if not provided."""
        with patch("fin_trade.agents.tools.price_lookup.SecurityService") as mock_class:
            mock_instance = MagicMock()
            mock_instance.get_price.return_value = 100.0
            mock_class.return_value = mock_instance

            result = get_stock_price("TEST")

            assert result == 100.0
            mock_class.assert_called_once()


class TestGetStockPrices:
    """Tests for get_stock_prices function."""

    def test_returns_prices_for_multiple_tickers(self):
        """Test getting prices for multiple tickers."""
        mock_service = MagicMock()
        mock_service.get_price.side_effect = lambda t: {"AAPL": 185.0, "MSFT": 420.0}.get(t)

        result = get_stock_prices(["AAPL", "MSFT"], mock_service)

        assert result == {"AAPL": 185.0, "MSFT": 420.0}

    def test_skips_failed_lookups(self):
        """Test that failed lookups are skipped."""
        mock_service = MagicMock()

        def get_price(ticker):
            if ticker == "GOOD":
                return 100.0
            raise Exception("Not found")

        mock_service.get_price.side_effect = get_price

        result = get_stock_prices(["GOOD", "BAD"], mock_service)

        assert result == {"GOOD": 100.0}
        assert "BAD" not in result

    def test_uppercases_tickers(self):
        """Test that tickers are uppercased."""
        mock_service = MagicMock()
        mock_service.get_price.return_value = 100.0

        result = get_stock_prices(["aapl"], mock_service)

        assert "AAPL" in result
