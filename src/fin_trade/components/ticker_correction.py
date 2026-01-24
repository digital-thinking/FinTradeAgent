"""Reusable ticker correction component for handling invalid/missing tickers."""

from dataclasses import dataclass

import streamlit as st

from fin_trade.services.security import SecurityService


@dataclass
class TickerCorrectionResult:
    """Result of ticker correction attempt."""

    corrected_ticker: str
    price: float | None
    isin: str | None
    is_valid: bool
    error_message: str | None


def render_ticker_correction(
    original_ticker: str,
    key_prefix: str,
    security_service: SecurityService,
    show_isin_input: bool = True,
) -> TickerCorrectionResult:
    """Render ticker correction UI and return the result.

    Args:
        original_ticker: The original ticker symbol that may need correction
        key_prefix: Unique prefix for session state keys (e.g., "pending_0")
        security_service: Service for price/ISIN lookups
        show_isin_input: Whether to show ISIN input for unknown ISINs

    Returns:
        TickerCorrectionResult with the corrected ticker and lookup results
    """
    # Session state keys
    correction_key = f"{key_prefix}_ticker_correction"
    isin_key = f"{key_prefix}_isin_input"

    # Get corrected ticker from session state or use original
    corrected_ticker = st.session_state.get(correction_key, original_ticker)

    # Try to look up the ticker
    price = None
    isin = None
    error_message = None
    security_info = None

    try:
        price = security_service.get_price(corrected_ticker)
        security_info = security_service.lookup_ticker(corrected_ticker)
        if security_info:
            isin = security_info.isin
    except Exception as e:
        error_message = str(e)

    is_valid = price is not None and price > 0

    # If ticker lookup failed, show correction UI
    if error_message or not is_valid:
        st.error(f"Could not find price for '{corrected_ticker}'.")

        # Inline correction UI
        col_label, col_input, col_btn = st.columns([2, 3, 1])
        with col_label:
            st.markdown("**Did you mean?**")
        with col_input:
            new_ticker = st.text_input(
                "Correct ticker",
                value=corrected_ticker,
                key=f"{key_prefix}_ticker_input",
                label_visibility="collapsed",
                placeholder="e.g., AAPL, MSFT, BAS.DE",
            )
        with col_btn:
            if st.button("Verify", key=f"{key_prefix}_verify_btn", type="secondary"):
                st.session_state[correction_key] = new_ticker.upper()
                st.rerun()

    # Check if ISIN is missing/unknown and show input if requested
    if show_isin_input and security_info and security_info.isin.startswith("UNKNOWN-"):
        with st.expander("ISIN Missing - Please Provide", expanded=False):
            st.caption(
                f"yfinance couldn't find the ISIN for {corrected_ticker}. "
                "Please enter it manually for better tracking:"
            )
            user_isin = st.text_input(
                "ISIN",
                value=st.session_state.get(isin_key, ""),
                key=f"{key_prefix}_isin_field",
                placeholder="e.g., US0378331005",
            )
            if user_isin:
                st.session_state[isin_key] = user_isin
                isin = user_isin

    # Get user-provided ISIN from session state
    user_provided_isin = st.session_state.get(isin_key)
    if user_provided_isin:
        isin = user_provided_isin

    return TickerCorrectionResult(
        corrected_ticker=corrected_ticker,
        price=price,
        isin=isin,
        is_valid=is_valid,
        error_message=error_message,
    )


def apply_isin_corrections(
    key_prefixes: list[str],
    tickers: list[str],
    security_service: SecurityService,
) -> None:
    """Apply any user-provided ISINs to the security service.

    Call this before executing trades to persist ISIN corrections.

    Args:
        key_prefixes: List of key prefixes used in render_ticker_correction
        tickers: Corresponding list of tickers
        security_service: Service to update ISINs in
    """
    for prefix, ticker in zip(key_prefixes, tickers):
        isin_key = f"{prefix}_isin_input"
        correction_key = f"{prefix}_ticker_correction"

        # Get the corrected ticker if any
        actual_ticker = st.session_state.get(correction_key, ticker)

        # Get user-provided ISIN if any
        user_isin = st.session_state.get(isin_key)

        if user_isin:
            try:
                security_service.update_isin(actual_ticker, user_isin)
            except Exception:
                pass  # Ignore errors, the trade will still work


def clear_ticker_corrections(key_prefixes: list[str]) -> None:
    """Clear ticker correction session state for given prefixes.

    Call this after trades are executed to reset the UI state.

    Args:
        key_prefixes: List of key prefixes to clear
    """
    for prefix in key_prefixes:
        keys_to_clear = [
            f"{prefix}_ticker_correction",
            f"{prefix}_isin_input",
            f"{prefix}_ticker_input",
            f"{prefix}_isin_field",
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
