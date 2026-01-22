"""System Health page for viewing execution logs and analytics."""

import json

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from fin_trade.services.execution_log import ExecutionLogService


def render_system_health_page() -> None:
    """Render the system health and analytics page."""
    st.title("System Health & Analytics")

    log_service = ExecutionLogService()

    # Summary metrics
    st.subheader("Summary (Last 30 Days)")

    stats = log_service.get_summary_stats(days=30)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Executions", stats["total_executions"])

    with col2:
        st.metric(
            "Success Rate",
            f"{stats['success_rate']:.1f}%",
            delta=f"{stats['successful_executions']}/{stats['total_executions']}",
        )

    with col3:
        st.metric("Total Tokens", f"{stats['total_tokens']:,}")

    with col4:
        avg_duration_sec = stats["avg_duration_ms"] / 1000
        st.metric("Avg Duration", f"{avg_duration_sec:.1f}s")

    st.divider()

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["Execution History", "Analytics", "By Portfolio"])

    with tab1:
        _render_execution_history(log_service)

    with tab2:
        _render_analytics(log_service)

    with tab3:
        _render_by_portfolio(log_service)


def _render_execution_history(log_service: ExecutionLogService) -> None:
    """Render the execution history table."""
    st.subheader("Recent Executions")

    logs = log_service.get_logs(limit=50)

    if not logs:
        st.info("No execution logs yet. Run an agent to generate logs.")
        return

    # Build DataFrame
    log_data = []
    for log in logs:
        log_data.append({
            "Time": log.timestamp.strftime("%Y-%m-%d %H:%M"),
            "Portfolio": log.portfolio_name,
            "Mode": log.agent_mode,
            "Model": log.model,
            "Duration": f"{log.duration_ms / 1000:.1f}s",
            "Tokens": f"{log.total_tokens:,}",
            "Trades": log.num_trades,
            "Status": "Success" if log.success else "Failed",
        })

    df = pd.DataFrame(log_data)

    st.dataframe(
        df,
        column_config={
            "Time": st.column_config.TextColumn("Time", width="medium"),
            "Portfolio": st.column_config.TextColumn("Portfolio", width="medium"),
            "Mode": st.column_config.TextColumn("Mode", width="small"),
            "Model": st.column_config.TextColumn("Model", width="small"),
            "Duration": st.column_config.TextColumn("Duration", width="small"),
            "Tokens": st.column_config.TextColumn("Tokens", width="small"),
            "Trades": st.column_config.NumberColumn("Trades", format="%d"),
            "Status": st.column_config.TextColumn("Status", width="small"),
        },
        hide_index=True,
        use_container_width=True,
    )

    # Expandable detail view for each execution
    st.subheader("Execution Details")

    selected_idx = st.selectbox(
        "Select execution to view details",
        range(len(logs)),
        format_func=lambda i: f"{logs[i].timestamp.strftime('%Y-%m-%d %H:%M')} - {logs[i].portfolio_name} ({logs[i].agent_mode})",
    )

    if selected_idx is not None:
        log = logs[selected_idx]

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Execution Info**")
            st.write(f"- Portfolio: {log.portfolio_name}")
            st.write(f"- Agent Mode: {log.agent_mode}")
            st.write(f"- Model: {log.model}")
            st.write(f"- Duration: {log.duration_ms}ms")
            st.write(f"- Status: {'Success' if log.success else 'Failed'}")
            if log.error_message:
                st.error(f"Error: {log.error_message}")

        with col2:
            st.markdown("**Token Usage**")
            st.write(f"- Input Tokens: {log.input_tokens:,}")
            st.write(f"- Output Tokens: {log.output_tokens:,}")
            st.write(f"- Total Tokens: {log.total_tokens:,}")
            st.write(f"- Trades Generated: {log.num_trades}")

        # Step breakdown
        if log.step_details:
            st.markdown("**Step Breakdown**")
            try:
                steps = json.loads(log.step_details)
                if steps:
                    step_data = []
                    for step_name, step_metrics in steps.items():
                        step_data.append({
                            "Step": step_name,
                            "Duration (ms)": step_metrics.get("duration_ms", 0),
                            "Input Tokens": step_metrics.get("input_tokens", 0),
                            "Output Tokens": step_metrics.get("output_tokens", 0),
                        })

                    step_df = pd.DataFrame(step_data)
                    st.dataframe(step_df, hide_index=True, use_container_width=True)
            except json.JSONDecodeError:
                st.caption("No step details available")


def _render_analytics(log_service: ExecutionLogService) -> None:
    """Render analytics charts."""
    st.subheader("Usage Trends (Last 14 Days)")

    daily_stats = log_service.get_daily_stats(days=14)

    if not daily_stats:
        st.info("Not enough data for analytics. Run more agent executions.")
        return

    df = pd.DataFrame(daily_stats)

    # Executions over time
    fig_executions = px.bar(
        df,
        x="date",
        y="executions",
        title="Daily Executions",
        labels={"date": "Date", "executions": "Executions"},
    )
    fig_executions.update_layout(template="plotly_dark", height=300)
    st.plotly_chart(fig_executions, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        # Token usage over time
        fig_tokens = px.area(
            df,
            x="date",
            y="tokens",
            title="Daily Token Usage",
            labels={"date": "Date", "tokens": "Tokens"},
        )
        fig_tokens.update_layout(template="plotly_dark", height=300)
        st.plotly_chart(fig_tokens, use_container_width=True)

    with col2:
        # Average duration over time
        fig_duration = px.line(
            df,
            x="date",
            y="avg_duration_ms",
            title="Average Duration (ms)",
            labels={"date": "Date", "avg_duration_ms": "Duration (ms)"},
            markers=True,
        )
        fig_duration.update_layout(template="plotly_dark", height=300)
        st.plotly_chart(fig_duration, use_container_width=True)

    # Agent mode breakdown
    stats = log_service.get_summary_stats(days=30)

    if stats["by_agent_mode"]:
        st.subheader("By Agent Mode")

        col1, col2 = st.columns(2)

        with col1:
            mode_df = pd.DataFrame(stats["by_agent_mode"])
            fig_mode = px.pie(
                mode_df,
                values="executions",
                names="mode",
                title="Executions by Agent Mode",
            )
            fig_mode.update_layout(template="plotly_dark", height=300)
            st.plotly_chart(fig_mode, use_container_width=True)

        with col2:
            fig_tokens_mode = px.bar(
                mode_df,
                x="mode",
                y="tokens",
                title="Token Usage by Agent Mode",
                labels={"mode": "Agent Mode", "tokens": "Total Tokens"},
            )
            fig_tokens_mode.update_layout(template="plotly_dark", height=300)
            st.plotly_chart(fig_tokens_mode, use_container_width=True)


def _render_by_portfolio(log_service: ExecutionLogService) -> None:
    """Render per-portfolio breakdown."""
    st.subheader("Portfolio Breakdown")

    stats = log_service.get_summary_stats(days=30)

    if not stats["by_portfolio"]:
        st.info("No execution data by portfolio yet.")
        return

    portfolio_df = pd.DataFrame(stats["by_portfolio"])

    # Table view
    st.dataframe(
        portfolio_df,
        column_config={
            "portfolio": st.column_config.TextColumn("Portfolio", width="medium"),
            "executions": st.column_config.NumberColumn("Executions", format="%d"),
            "tokens": st.column_config.NumberColumn("Total Tokens", format="%d"),
            "avg_duration_ms": st.column_config.NumberColumn("Avg Duration (ms)", format="%.0f"),
        },
        hide_index=True,
        use_container_width=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        # Executions by portfolio
        fig_exec = px.bar(
            portfolio_df,
            x="portfolio",
            y="executions",
            title="Executions by Portfolio",
            labels={"portfolio": "Portfolio", "executions": "Executions"},
        )
        fig_exec.update_layout(template="plotly_dark", height=300)
        st.plotly_chart(fig_exec, use_container_width=True)

    with col2:
        # Tokens by portfolio
        fig_tokens = px.bar(
            portfolio_df,
            x="portfolio",
            y="tokens",
            title="Token Usage by Portfolio",
            labels={"portfolio": "Portfolio", "tokens": "Total Tokens"},
        )
        fig_tokens.update_layout(template="plotly_dark", height=300)
        st.plotly_chart(fig_tokens, use_container_width=True)
