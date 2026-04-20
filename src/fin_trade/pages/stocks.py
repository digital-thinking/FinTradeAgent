"""Stocks overview and management page."""

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from fin_trade.services import PortfolioService
from fin_trade.services.security import SecurityService


def _display_persistent_messages() -> None:
    messages = st.session_state.pop("stocks_messages", None)
    if not messages:
        return
    for msg in messages:
        if msg["type"] == "success":
            st.success(msg["text"])
        elif msg["type"] == "error":
            st.error(msg["text"])
        elif msg["type"] == "info":
            st.info(msg["text"])


def _portfolio_ticker_usage(
    portfolio_service: PortfolioService,
) -> dict[str, list[str]]:
    """Return mapping of ticker -> portfolio names that currently hold it."""
    usage: dict[str, list[str]] = {}
    for filename in portfolio_service.list_portfolios():
        config, state = portfolio_service.load_portfolio(filename)
        for holding in state.holdings:
            usage.setdefault(holding.ticker.upper(), []).append(config.name)
    return usage


def render_stocks_page(
    security_service: SecurityService,
    portfolio_service: PortfolioService,
) -> None:
    """Render the stocks overview and management page."""
    st.title("📈 Stocks")
    st.caption("Manage cached symbols, view data, and refresh prices.")

    _display_persistent_messages()

    _render_add_symbol(security_service)

    st.divider()

    usage = _portfolio_ticker_usage(portfolio_service)
    tickers = sorted(security_service._by_ticker.keys())

    if not tickers:
        st.info("No cached symbols yet. Add one above to get started.")
        return

    _render_symbol_table(security_service, tickers, usage)

    st.divider()
    _render_symbol_detail(security_service, tickers, usage)


def _render_add_symbol(security_service: SecurityService) -> None:
    with st.expander("➕ Add Symbol", expanded=False):
        with st.form("add_symbol_form", clear_on_submit=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                ticker_input = st.text_input(
                    "Ticker",
                    placeholder="e.g. AAPL or BTC-USD",
                )
            with col2:
                st.write("")
                st.write("")
                submitted = st.form_submit_button("Add", type="primary")

            if submitted:
                ticker = ticker_input.strip().upper()
                if not ticker:
                    st.error("Ticker is required.")
                    return
                try:
                    security = security_service.lookup_ticker(ticker)
                except Exception as e:
                    st.error(f"Could not add '{ticker}': {e}")
                    return
                st.session_state["stocks_messages"] = [{
                    "type": "success",
                    "text": f"Added {security.ticker} — {security.name}",
                }]
                st.session_state["stocks_selected_ticker"] = security.ticker
                st.rerun()


def _render_symbol_table(
    security_service: SecurityService,
    tickers: list[str],
    usage: dict[str, list[str]],
) -> None:
    st.subheader(f"Cached Symbols ({len(tickers)})")

    rows = []
    for ticker in tickers:
        info = security_service.get_full_info(ticker) or {}
        saved_at_str = info.get("_saved_at")
        try:
            saved_at = (
                datetime.fromisoformat(saved_at_str) if saved_at_str else None
            )
        except ValueError:
            saved_at = None

        price = security_service._stock_data_service.get_cached_price(ticker)

        rows.append({
            "Ticker": ticker,
            "Name": info.get("shortName") or info.get("longName") or ticker,
            "Sector": info.get("sector") or "—",
            "Currency": info.get("currency") or "—",
            "Price": price,
            "Stale": security_service.is_data_stale(ticker),
            "Last Updated": saved_at.strftime("%Y-%m-%d %H:%M") if saved_at else "—",
            "In Portfolios": ", ".join(usage.get(ticker, [])) or "—",
        })

    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        width="stretch",
        hide_index=True,
        column_config={
            "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
            "Stale": st.column_config.CheckboxColumn("Stale"),
        },
    )


def _render_symbol_detail(
    security_service: SecurityService,
    tickers: list[str],
    usage: dict[str, list[str]],
) -> None:
    st.subheader("Symbol Detail")

    default_ticker = st.session_state.get("stocks_selected_ticker")
    default_index = tickers.index(default_ticker) if default_ticker in tickers else 0

    selected = st.selectbox(
        "Select a symbol",
        options=tickers,
        index=default_index,
        key="stocks_selected_ticker",
    )

    if not selected:
        return

    info = security_service.get_full_info(selected) or {}

    # Header with metadata and action buttons
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown(
            f"### {selected} — {info.get('shortName') or info.get('longName') or selected}"
        )
        meta_parts = []
        if info.get("sector"):
            meta_parts.append(f"**Sector:** {info['sector']}")
        if info.get("industry"):
            meta_parts.append(f"**Industry:** {info['industry']}")
        if info.get("country"):
            meta_parts.append(f"**Country:** {info['country']}")
        if info.get("currency"):
            meta_parts.append(f"**Currency:** {info['currency']}")
        if meta_parts:
            st.caption(" · ".join(meta_parts))
        if info.get("website"):
            st.caption(info["website"])

    with col2:
        if st.button("🔄 Reload", key=f"reload_{selected}", width="stretch"):
            try:
                security_service.refresh_security_data(selected)
                security_service.force_update_price(selected)
            except Exception as e:
                st.session_state["stocks_messages"] = [{
                    "type": "error",
                    "text": f"Failed to reload {selected}: {e}",
                }]
                st.rerun()
            st.session_state["stocks_messages"] = [{
                "type": "success",
                "text": f"Reloaded data for {selected}.",
            }]
            st.rerun()

    with col3:
        in_use = usage.get(selected, [])
        delete_disabled = bool(in_use)
        delete_help = (
            f"Held in: {', '.join(in_use)}" if in_use else "Remove cached data"
        )
        if st.button(
            "🗑️ Delete",
            key=f"delete_{selected}",
            width="stretch",
            disabled=delete_disabled,
            help=delete_help,
        ):
            st.session_state[f"confirm_delete_{selected}"] = True

        if st.session_state.get(f"confirm_delete_{selected}"):
            st.warning(f"Delete cached data for {selected}?")
            if st.button("Confirm delete", key=f"confirm_{selected}", type="primary"):
                try:
                    security_service.delete_security(selected)
                except Exception as e:
                    st.session_state["stocks_messages"] = [{
                        "type": "error",
                        "text": f"Failed to delete {selected}: {e}",
                    }]
                else:
                    st.session_state["stocks_messages"] = [{
                        "type": "info",
                        "text": f"Deleted cached data for {selected}.",
                    }]
                st.session_state.pop(f"confirm_delete_{selected}", None)
                st.session_state.pop("stocks_selected_ticker", None)
                st.rerun()

    # Key stats
    stats_cols = st.columns(4)
    with stats_cols[0]:
        price = security_service._stock_data_service.get_cached_price(selected)
        st.metric("Price", f"${price:.2f}" if price is not None else "—")
    with stats_cols[1]:
        market_cap = info.get("marketCap")
        st.metric(
            "Market Cap",
            f"${market_cap/1e9:.2f}B" if market_cap else "—",
        )
    with stats_cols[2]:
        range_data = security_service.get_52w_range(selected)
        if range_data:
            st.metric(
                "52w Range",
                f"${range_data['low_52w']:.2f} – ${range_data['high_52w']:.2f}",
            )
        else:
            st.metric("52w Range", "—")
    with stats_cols[3]:
        stale = security_service.is_data_stale(selected)
        st.metric("Data Freshness", "Stale" if stale else "Fresh")

    _render_price_chart(security_service, selected)

    with st.expander("Raw cached data"):
        filtered_info = {k: v for k, v in info.items() if not k.startswith("_")}
        st.json(filtered_info)


def _render_price_chart(security_service: SecurityService, ticker: str) -> None:
    stock_data_service = security_service._stock_data_service
    cache_path = stock_data_service._get_cache_path(ticker)

    if not cache_path.exists():
        st.info("No cached price history. Click Reload to fetch from yfinance.")
        return

    period_options = {"1M": 30, "3M": 90, "6M": 180, "1Y": 365, "MAX": 0}
    period_label = st.radio(
        "Period",
        options=list(period_options.keys()),
        index=3,
        horizontal=True,
        key=f"stocks_period_{ticker}",
    )
    days = period_options[period_label]

    try:
        df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
    except Exception as e:
        st.warning(f"Could not load price history: {e}")
        return

    df.index = pd.to_datetime(df.index, utc=True, errors="coerce").tz_localize(None)
    df = df[df.index.notna()]

    if days > 0:
        cutoff = datetime.now() - pd.Timedelta(days=days)
        df = df[df.index >= cutoff]

    if df.empty:
        st.info("No price history in the selected period.")
        return

    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name=ticker,
        )
    )
    fig.update_layout(
        height=450,
        margin={"l": 10, "r": 10, "t": 30, "b": 10},
        xaxis_rangeslider_visible=False,
        yaxis_title="Price",
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": True})
