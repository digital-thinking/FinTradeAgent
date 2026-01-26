"""Reusable ticker correction component for handling invalid/missing tickers."""

from dataclasses import dataclass

import streamlit as st

from fin_trade.services.security import SecurityService


@dataclass
class TickerCorrectionResult:
    """Result of ticker correction attempt."""

    corrected_ticker: str
    price: float | None
    is_valid: bool
    error_message: str | None


def render_ticker_correction(
    original_ticker: str,
    key_prefix: str,
    security_service: SecurityService,
) -> TickerCorrectionResult:
    """Render ticker correction UI and return the result.

    Args:
        original_ticker: The original ticker symbol that may need correction
        key_prefix: Unique prefix for session state keys (e.g., "pending_0")
        security_service: Service for price lookups

    Returns:
        TickerCorrectionResult with the corrected ticker and lookup results
    """
    # Session state keys
    correction_key = f"{key_prefix}_ticker_correction"

    # Get corrected ticker from session state or use original
    corrected_ticker = st.session_state.get(correction_key, original_ticker)

    # Try to look up the ticker
    price = None
    error_message = None

    try:
        price = security_service.get_price(corrected_ticker)
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

    return TickerCorrectionResult(
        corrected_ticker=corrected_ticker,
        price=price,
        is_valid=is_valid,
        error_message=error_message,
    )


def clear_ticker_corrections(key_prefixes: list[str]) -> None:
    """Clear ticker correction session state for given prefixes.

    Call this after trades are executed to reset the UI state.

    Args:
        key_prefixes: List of key prefixes to clear
    """
    for prefix in key_prefixes:
        keys_to_clear = [
            f"{prefix}_ticker_correction",
            f"{prefix}_ticker_input",
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
