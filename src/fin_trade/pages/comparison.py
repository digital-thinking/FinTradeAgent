"""Portfolio comparison page."""

from datetime import datetime, timedelta

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from fin_trade.models import AssetClass
from fin_trade.services import PortfolioService, StockDataService, ComparisonService


def render_comparison_page(portfolio_service: PortfolioService) -> None:
    """Render the portfolio comparison page."""
    st.title("Portfolio Comparison")

    # Get available portfolios
    portfolio_names = portfolio_service.list_portfolios()

    if len(portfolio_names) < 1:
        st.info("Create at least one portfolio to use the comparison feature.")
        return

    # Multi-select for portfolios (default: all portfolios)
    selected_portfolios = st.multiselect(
        "Select portfolios to compare",
        options=portfolio_names,
        default=portfolio_names,  # Default to all portfolios
        help="Choose 2 or more portfolios to compare their performance",
    )

    if len(selected_portfolios) < 1:
        st.warning("Select at least one portfolio to view comparison.")
        return

    # Initialize services
    stock_data_service = StockDataService()
    comparison_service = ComparisonService(
        portfolio_service=portfolio_service,
        stock_data_service=stock_data_service,
    )

    selected_asset_classes = set()
    for name in selected_portfolios:
        config, _ = portfolio_service.load_portfolio(name)
        selected_asset_classes.add(config.asset_class)

    if len(selected_asset_classes) > 1:
        st.error("Comparison supports one asset class at a time. Select either stock or crypto portfolios.")
        return

    selected_asset_class = next(iter(selected_asset_classes), AssetClass.STOCKS)
    default_benchmark = comparison_service.get_default_benchmark(selected_asset_class)

    if selected_asset_class == AssetClass.CRYPTO:
        benchmark_options = ["BTC-USD", "ETH-USD"]
    else:
        benchmark_options = ["SPY", "QQQ", "DIA", "IWM"]

    benchmark_index = (
        benchmark_options.index(default_benchmark)
        if default_benchmark in benchmark_options
        else 0
    )

    # Benchmark options
    col1, col2 = st.columns([2, 1])
    with col1:
        include_benchmark = st.checkbox("Include benchmark", value=True)
    with col2:
        benchmark_symbol = st.selectbox(
            "Benchmark",
            options=benchmark_options,
            index=benchmark_index,
            disabled=not include_benchmark,
        )

    # Tab layout for different views
    tab1, tab2 = st.tabs(["Performance Chart", "Metrics Table"])

    with tab1:
        _render_performance_comparison(
            comparison_service,
            selected_portfolios,
            include_benchmark,
            benchmark_symbol,
        )

    with tab2:
        _render_metrics_comparison(
            comparison_service,
            selected_portfolios,
            benchmark_symbol,
        )


def _render_performance_comparison(
    comparison_service: ComparisonService,
    portfolio_names: list[str],
    include_benchmark: bool,
    benchmark_symbol: str,
) -> None:
    """Render the normalized performance comparison chart."""
    st.subheader("Normalized Performance")
    st.caption("All portfolios rebased to 100 at the start for comparison")

    try:
        returns_df = comparison_service.get_normalized_returns(
            portfolio_names=portfolio_names,
            include_benchmark=include_benchmark,
            benchmark_symbol=benchmark_symbol,
        )

        if returns_df.empty:
            st.info("No trade history available for the selected portfolios.")
            return

        # Build the chart
        fig = go.Figure()

        # Color palette for portfolios
        colors = ["#2196F3", "#4CAF50", "#FF5722", "#9C27B0", "#00BCD4", "#FFC107"]

        # Add portfolio traces
        for i, col in enumerate(returns_df.columns):
            if col == "date":
                continue

            color = colors[i % len(colors)]
            is_benchmark = col.endswith("_benchmark")

            fig.add_trace(
                go.Scatter(
                    x=returns_df["date"],
                    y=returns_df[col],
                    mode="lines",
                    name=col.replace("_return", "").replace("_benchmark", " (Benchmark)"),
                    line=dict(
                        color="#FF9800" if is_benchmark else color,
                        width=2,
                        dash="dot" if is_benchmark else "solid",
                    ),
                    hovertemplate="%{y:.1f}<extra>%{fullData.name}</extra>",
                )
            )

        # Add baseline
        fig.add_hline(
            y=100,
            line_dash="dash",
            line_color="#666666",
            annotation_text="Start (100)",
            annotation_position="bottom right",
        )

        fig.update_layout(
            xaxis=dict(
                title="Date",
                gridcolor="rgba(128, 128, 128, 0.2)",
            ),
            yaxis=dict(
                title="Normalized Value (Start = 100)",
                gridcolor="rgba(128, 128, 128, 0.2)",
            ),
            height=500,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
            ),
            hovermode="x unified",
        )

        st.plotly_chart(fig, width='stretch')

    except Exception as e:
        st.error(f"Failed to generate comparison chart: {e}")


def _render_metrics_comparison(
    comparison_service: ComparisonService,
    portfolio_names: list[str],
    benchmark_symbol: str,
) -> None:
    """Render the metrics comparison table."""
    st.subheader("Performance Metrics")

    try:
        metrics_df = comparison_service.get_comparison_table(
            portfolio_names=portfolio_names,
            benchmark_symbol=benchmark_symbol,
        )

        if metrics_df.empty:
            st.info("No metrics available for the selected portfolios.")
            return

        # Transpose for better display (metrics as rows, portfolios as columns)
        display_df = metrics_df.T

        # Style the table
        st.dataframe(
            display_df,
            width='stretch',
            height=400,
        )

        # Additional insights
        st.divider()
        st.subheader("Quick Insights")

        col1, col2, col3 = st.columns(3)

        # Find best performer
        best_return = None
        best_portfolio = None
        for name in portfolio_names:
            try:
                metrics = comparison_service.calculate_metrics(name, benchmark_symbol)
                if best_return is None or metrics.total_return_pct > best_return:
                    best_return = metrics.total_return_pct
                    best_portfolio = name
            except Exception:
                pass

        with col1:
            if best_portfolio:
                st.metric(
                    "Best Performer",
                    best_portfolio,
                    f"{best_return:+.1f}%",
                )

        # Find lowest drawdown
        lowest_dd = None
        safest_portfolio = None
        for name in portfolio_names:
            try:
                metrics = comparison_service.calculate_metrics(name, benchmark_symbol)
                if lowest_dd is None or metrics.max_drawdown_pct < lowest_dd:
                    lowest_dd = metrics.max_drawdown_pct
                    safest_portfolio = name
            except Exception:
                pass

        with col2:
            if safest_portfolio:
                st.metric(
                    "Lowest Drawdown",
                    safest_portfolio,
                    f"-{lowest_dd:.1f}%",
                    delta_color="inverse",
                )

        # Find best Sharpe ratio
        best_sharpe = None
        best_risk_adj = None
        for name in portfolio_names:
            try:
                metrics = comparison_service.calculate_metrics(name, benchmark_symbol)
                if metrics.sharpe_ratio is not None:
                    if best_sharpe is None or metrics.sharpe_ratio > best_sharpe:
                        best_sharpe = metrics.sharpe_ratio
                        best_risk_adj = name
            except Exception:
                pass

        with col3:
            if best_risk_adj:
                st.metric(
                    "Best Risk-Adjusted",
                    best_risk_adj,
                    f"Sharpe: {best_sharpe:.2f}",
                )

    except Exception as e:
        st.error(f"Failed to calculate metrics: {e}")
