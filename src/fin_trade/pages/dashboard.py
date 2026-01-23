"""Summary Dashboard page."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

from fin_trade.cache import get_portfolio_metrics
from fin_trade.services import PortfolioService


def render_dashboard_page(portfolio_service: PortfolioService) -> None:
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
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_sorted['Name'],
            y=df_sorted['Gain (%)'],
            marker_color=['#008F11' if x >= 0 else '#ff0000' for x in df_sorted['Gain (%)']]
        ))
        
        fig.update_layout(
            title="Return by Strategy (%)",
            xaxis_title="Strategy",
            yaxis_title="Return (%)",
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Segoe UI, Roboto, Helvetica Neue, sans-serif", color="#000000"),
            title_font_color="#000000",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Upcoming Runs Schedule
    st.subheader("Upcoming Scheduled Runs")
    
    schedule_data = []
    for p in portfolio_metrics:
        last_run = p["Last Run"]
        freq = p["Frequency"]
        
        if not last_run:
            next_run = datetime.now() # Run immediately if never run
            status = "Pending (New)"
        else:
            if freq == "daily":
                next_run = last_run + timedelta(days=1)
            elif freq == "weekly":
                next_run = last_run + timedelta(weeks=1)
            elif freq == "monthly":
                next_run = last_run + timedelta(days=30)
            else:
                next_run = last_run + timedelta(days=1) # Default
            
            if datetime.now() > next_run:
                status = "Overdue"
            else:
                status = "Scheduled"
                
        schedule_data.append({
            "Strategy": p["Name"],
            "Last Run": last_run,
            "Next Run": next_run,
            "Status": status
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
