"""Summary Dashboard page."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from fin_trade.cache import get_portfolio_metrics
from fin_trade.services import (
    PortfolioService,
    AttributionService,
    SecurityService,
    SchedulerService,
)
from fin_trade.services.attribution import SectorAttribution, HoldingAttribution


def render_dashboard_page(
    portfolio_service: PortfolioService,
    scheduler_service: SchedulerService,
) -> None:
    """Render the summary dashboard page."""
    st.title("Summary Dashboard")

    portfolios = portfolio_service.list_portfolios()

    if not portfolios:
        st.warning("No portfolios found.")
        return

    # Aggregate data
    total_value = 0
    total_gain = 0
    portfolio_metrics = []

    for filename in portfolios:
        try:
            config, state = portfolio_service.load_portfolio(filename)
            metrics = get_portfolio_metrics(portfolio_service, filename)
            
            total_value += metrics["value"]
            total_gain += metrics["absolute_gain"]
            
            portfolio_metrics.append({
                "Name": config.name,
                "Value": metrics["value"],
                "Gain ($)": metrics["absolute_gain"],
                "Gain (%)": metrics["percentage_gain"],
                "Holdings": len(state.holdings),
                "Last Run": state.last_execution,
                "Frequency": config.run_frequency
            })
        except Exception as e:
            st.error(f"Error loading {filename}: {e}")

    # Top Level Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total AUM", f"${total_value:,.2f}")
    with col2:
        gain_pct = (total_gain / (total_value - total_gain) * 100) if (total_value - total_gain) > 0 else 0
        st.metric("Total Gain/Loss", f"${total_gain:,.2f}", delta=f"{gain_pct:+.1f}%")
    with col3:
        st.metric("Active Strategies", len(portfolios))

    st.divider()

    # Performance Comparison
    st.subheader("Performance Comparison")
    
    if portfolio_metrics:
        df = pd.DataFrame(portfolio_metrics)
        
        # Sort by Gain %
        df_sorted = df.sort_values("Gain (%)", ascending=False)
        
        # Best & Worst Performers
        best = df_sorted.iloc[0]
        worst = df_sorted.iloc[-1]
        
        col_best, col_worst = st.columns(2)
        
        with col_best:
            st.success(f"🏆 Best Performer: **{best['Name']}**")
            st.metric("Return", f"{best['Gain (%)']:+.1f}%", f"${best['Gain ($)']:,.2f}")
            
        with col_worst:
            st.error(f"📉 Worst Performer: **{worst['Name']}**")
            st.metric("Return", f"{worst['Gain (%)']:+.1f}%", f"${worst['Gain ($)']:,.2f}")

        # Bar Chart Comparison
        # Convert to native Python floats to avoid numpy display issues
        gain_values = [float(x) for x in df_sorted['Gain (%)']]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_sorted['Name'].tolist(),
            y=gain_values,
            marker_color=['#008F11' if x >= 0 else '#ff0000' for x in gain_values],
            hovertemplate="<b>%{x}</b><br>Return: %{y:.2f}%<extra></extra>"
        ))

        fig.update_layout(
            title="Return by Strategy (%)",
            xaxis_title="Strategy",
            yaxis_title="Return (%)",
            yaxis_tickformat=".1f",
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Segoe UI, Roboto, Helvetica Neue, sans-serif", color="#000000"),
            title_font_color="#000000",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Scheduler Status
    st.subheader("Scheduler Status")
    status = scheduler_service.get_status()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Scheduler", "Running" if status["running"] else "Stopped")
    with col2:
        st.metric("Enabled Schedules", status["enabled"])
    with col3:
        st.metric("Active Jobs", status["jobs"])

    st.divider()

    # Upcoming Runs Schedule
    st.subheader("Upcoming Scheduled Runs")

    scheduled = scheduler_service.get_scheduled_portfolios()
    if not scheduled:
        st.info("No portfolios are enabled for scheduled execution.")
    else:
        schedule_data = []
        now = datetime.now()

        for item in scheduled:
            if item.next_run is None:
                status_label = "Pending"
            elif item.next_run <= now:
                status_label = "Due"
            else:
                status_label = "Scheduled"

            schedule_data.append({
                "Strategy": item.display_name,
                "Frequency": item.frequency,
                "Last Run": item.last_run,
                "Next Run": item.next_run,
                "Status": status_label,
            })

        df_schedule = pd.DataFrame(schedule_data).sort_values("Next Run")

        st.dataframe(
            df_schedule,
            column_config={
                "Last Run": st.column_config.DatetimeColumn("Last Run", format="YYYY-MM-DD HH:mm"),
                "Next Run": st.column_config.DatetimeColumn("Next Run", format="YYYY-MM-DD HH:mm"),
                "Status": st.column_config.TextColumn("Status"),
            },
            hide_index=True,
            use_container_width=True
        )

    # Performance Attribution Section
    st.divider()
    _render_performance_attribution(portfolio_service, portfolios)


def _render_performance_attribution(
    portfolio_service: PortfolioService,
    portfolios: list[str],
) -> None:
    """Render the performance attribution section showing sector and ticker contributions."""
    st.subheader("Performance Attribution")

    security_service = SecurityService()
    attribution_service = AttributionService(security_service)

    # Aggregate attribution across all portfolios
    all_sector_data: dict[str, dict] = {}
    all_holding_data: list[HoldingAttribution] = []
    total_gain = 0.0

    for filename in portfolios:
        try:
            config, state = portfolio_service.load_portfolio(filename)
            if not state.holdings:
                continue

            result = attribution_service.calculate_attribution(config, state)
            total_gain += result.total_gain

            # Aggregate sector data
            for sector_attr in result.by_sector:
                if sector_attr.sector not in all_sector_data:
                    all_sector_data[sector_attr.sector] = {
                        "total_gain": 0.0,
                        "total_cost_basis": 0.0,
                        "total_current_value": 0.0,
                        "holdings_count": 0,
                    }
                all_sector_data[sector_attr.sector]["total_gain"] += sector_attr.total_gain
                all_sector_data[sector_attr.sector]["total_cost_basis"] += sector_attr.total_cost_basis
                all_sector_data[sector_attr.sector]["total_current_value"] += sector_attr.total_current_value
                all_sector_data[sector_attr.sector]["holdings_count"] += sector_attr.holdings_count

            # Collect all holding attributions
            all_holding_data.extend(result.by_holding)

        except Exception:
            continue

    if not all_sector_data and not all_holding_data:
        st.info("No holdings data available for attribution analysis.")
        return

    # Display sector attribution
    col1, col2 = st.columns(2)

    with col1:
        _render_sector_attribution_chart(all_sector_data, total_gain)

    with col2:
        _render_top_performers(all_holding_data)


def _render_sector_attribution_chart(
    sector_data: dict[str, dict],
    total_gain: float,
) -> None:
    """Render the sector attribution bar chart."""
    st.markdown("**By Sector**")

    if not sector_data:
        st.info("No sector data available.")
        return

    # Build sector attribution list
    sectors = []
    gains = []
    gain_pcts = []

    for sector, data in sector_data.items():
        sectors.append(sector)
        gains.append(data["total_gain"])
        pct = (data["total_gain"] / data["total_cost_basis"]) * 100 if data["total_cost_basis"] > 0 else 0
        gain_pcts.append(pct)

    # Sort by gain
    sorted_data = sorted(zip(sectors, gains, gain_pcts), key=lambda x: x[1], reverse=True)
    sectors = [x[0] for x in sorted_data]
    gains = [x[1] for x in sorted_data]
    gain_pcts = [x[2] for x in sorted_data]

    # Create bar chart
    colors = ["#008F11" if g >= 0 else "#ff0000" for g in gains]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=sectors,
        x=gains,
        orientation="h",
        marker_color=colors,
        text=[f"{p:+.1f}%" for p in gain_pcts],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Gain: $%{x:,.2f}<br>Return: %{text}<extra></extra>",
    ))

    fig.update_layout(
        title="Sector Contribution to Return",
        xaxis_title="Gain/Loss ($)",
        yaxis_title="",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Segoe UI, Roboto, Helvetica Neue, sans-serif", color="#000000"),
        title_font_color="#000000",
        height=300,
        margin=dict(l=10, r=50, t=40, b=40),
        yaxis=dict(autorange="reversed"),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Show sector breakdown table
    with st.expander("Sector Details"):
        sector_df = pd.DataFrame([
            {
                "Sector": sector,
                "Holdings": sector_data[sector]["holdings_count"],
                "Cost Basis": sector_data[sector]["total_cost_basis"],
                "Current Value": sector_data[sector]["total_current_value"],
                "Gain/Loss": sector_data[sector]["total_gain"],
                "Return %": (sector_data[sector]["total_gain"] / sector_data[sector]["total_cost_basis"]) * 100
                    if sector_data[sector]["total_cost_basis"] > 0 else 0,
            }
            for sector in sectors
        ])

        st.dataframe(
            sector_df,
            column_config={
                "Sector": st.column_config.TextColumn("Sector", width="medium"),
                "Holdings": st.column_config.NumberColumn("Holdings", format="d"),
                "Cost Basis": st.column_config.NumberColumn("Cost Basis", format="$,.2f"),
                "Current Value": st.column_config.NumberColumn("Current", format="$,.2f"),
                "Gain/Loss": st.column_config.NumberColumn("Gain/Loss", format="$,.2f"),
                "Return %": st.column_config.NumberColumn("Return %", format=".1f"),
            },
            hide_index=True,
            use_container_width=True,
        )


def _render_top_performers(holding_data: list[HoldingAttribution]) -> None:
    """Render the top/bottom performers section."""
    st.markdown("**Top Contributors & Detractors**")

    if not holding_data:
        st.info("No holding data available.")
        return

    # Sort by unrealized gain
    sorted_holdings = sorted(holding_data, key=lambda x: x.unrealized_gain, reverse=True)

    # Top 3 contributors
    top_contributors = sorted_holdings[:3]
    # Bottom 3 detractors (only if negative)
    bottom_detractors = [h for h in sorted_holdings[-3:] if h.unrealized_gain < 0]
    bottom_detractors.reverse()

    # Display top contributors
    st.markdown("*Top Contributors*")
    for i, h in enumerate(top_contributors):
        gain_color = "green" if h.unrealized_gain >= 0 else "red"
        st.markdown(
            f"**{i+1}. {h.ticker}** ({h.sector or 'Unknown'}): "
            f":{gain_color}[${h.unrealized_gain:+,.2f}] ({h.gain_pct:+.1f}%)"
        )

    if bottom_detractors:
        st.markdown("*Top Detractors*")
        for i, h in enumerate(bottom_detractors):
            st.markdown(
                f"**{i+1}. {h.ticker}** ({h.sector or 'Unknown'}): "
                f":red[${h.unrealized_gain:+,.2f}] ({h.gain_pct:+.1f}%)"
            )

    # Full holdings table in expander
    with st.expander("All Holdings Attribution"):
        holdings_df = pd.DataFrame([
            {
                "Ticker": h.ticker,
                "Name": h.name,
                "Sector": h.sector or "Unknown",
                "Qty": h.quantity,
                "Avg Price": h.avg_price,
                "Current": h.current_price,
                "Gain/Loss": h.unrealized_gain,
                "Return %": h.gain_pct,
            }
            for h in sorted_holdings
        ])

        st.dataframe(
            holdings_df,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                "Name": st.column_config.TextColumn("Name", width="medium"),
                "Sector": st.column_config.TextColumn("Sector", width="medium"),
                "Qty": st.column_config.NumberColumn("Qty", format="d"),
                "Avg Price": st.column_config.NumberColumn("Avg Price", format="$,.2f"),
                "Current": st.column_config.NumberColumn("Current", format="$,.2f"),
                "Gain/Loss": st.column_config.NumberColumn("Gain/Loss", format="$,.2f"),
                "Return %": st.column_config.NumberColumn("Return %", format=".1f"),
            },
            hide_index=True,
            use_container_width=True,
        )
