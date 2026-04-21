"""System Health page for viewing execution logs and analytics."""

import json

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from fin_trade.services.execution_log import ExecutionLogService
from fin_trade.services import PortfolioService
from fin_trade.services.llm_provider import check_ollama_status
from fin_trade.services.security import SecurityService


def _display_persistent_messages() -> None:
    """Display and clear persistent messages from session state."""
    messages = st.session_state.pop("system_health_messages", None)
    if not messages:
        return

    for msg in messages:
        if msg["type"] == "success":
            st.success(msg["text"])
        elif msg["type"] == "error":
            st.error(msg["text"])
        elif msg["type"] == "warning":
            st.warning(msg["text"])
        elif msg["type"] == "info":
            st.info(msg["text"])


def render_system_health_page() -> None:
    """Render the system health and analytics page."""
    st.title("System Health & Analytics")

    # Display persistent messages from previous actions
    _display_persistent_messages()

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

    _render_ollama_status()

    st.divider()

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📜 Execution History", "📈 Analytics", "📊 By Portfolio"])

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
        width='stretch',
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
                    st.dataframe(step_df, hide_index=True, width='stretch')
            except json.JSONDecodeError:
                st.caption("No step details available")

        # Recommendations section
        _render_recommendations_section(log, log_service)


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
    st.plotly_chart(fig_executions, width='stretch')

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
        st.plotly_chart(fig_tokens, width='stretch')

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
        st.plotly_chart(fig_duration, width='stretch')

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
            st.plotly_chart(fig_mode, width='stretch')

        with col2:
            fig_tokens_mode = px.bar(
                mode_df,
                x="mode",
                y="tokens",
                title="Token Usage by Agent Mode",
                labels={"mode": "Agent Mode", "tokens": "Total Tokens"},
            )
            fig_tokens_mode.update_layout(template="plotly_dark", height=300)
            st.plotly_chart(fig_tokens_mode, width='stretch')


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
        width='stretch',
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
        st.plotly_chart(fig_exec, width='stretch')

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
        st.plotly_chart(fig_tokens, width='stretch')


def _render_recommendations_section(
    log,
    log_service: ExecutionLogService,
) -> None:
    """Render recommendations from an execution log with execution status."""
    if not log.recommendations_json:
        st.caption("No recommendations stored for this execution.")
        return

    try:
        recommendations = json.loads(log.recommendations_json)
    except json.JSONDecodeError:
        st.caption("Could not parse recommendations.")
        return

    if not recommendations:
        st.caption("No trade recommendations in this execution.")
        return

    # Parse executed trades
    executed_indices = set()
    if log.executed_trades_json:
        try:
            executed_indices = set(json.loads(log.executed_trades_json))
        except json.JSONDecodeError:
            pass

    st.markdown("**Trade Recommendations**")

    # Build DataFrame for display
    rec_data = []
    for i, rec in enumerate(recommendations):
        was_executed = i in executed_indices
        rec_data.append({
            "": "✓" if was_executed else "○",
            "Action": rec.get("action", ""),
            "Ticker": rec.get("ticker", ""),
            "Name": rec.get("name", ""),
            "Qty": rec.get("quantity", 0),
            "Reasoning": rec.get("reasoning", "")[:100] + "..." if len(rec.get("reasoning", "")) > 100 else rec.get("reasoning", ""),
            "Status": "Executed" if was_executed else "Pending",
        })

    df = pd.DataFrame(rec_data)
    st.dataframe(
        df,
        column_config={
            "": st.column_config.TextColumn("", width="small"),
            "Action": st.column_config.TextColumn("Action", width="small"),
            "Ticker": st.column_config.TextColumn("Ticker", width="small"),
            "Name": st.column_config.TextColumn("Name", width="medium"),
            "Qty": st.column_config.NumberColumn("Qty", format="%d", width="small"),
            "Reasoning": st.column_config.TextColumn("Reasoning", width="large"),
            "Status": st.column_config.TextColumn("Status", width="small"),
        },
        hide_index=True,
        width='stretch',
    )

    # Check if there are pending trades to apply
    pending_indices = [i for i in range(len(recommendations)) if i not in executed_indices]

    if pending_indices:
        st.markdown("---")
        st.markdown("**Apply Pending Recommendations**")

        # Let user select which pending trades to apply
        selected_indices = []
        for i in pending_indices:
            rec = recommendations[i]
            col1, col2 = st.columns([1, 5])
            with col1:
                if st.checkbox(
                    "Select",
                    key=f"apply_trade_{log.id}_{i}",
                    label_visibility="collapsed",
                ):
                    selected_indices.append(i)
            with col2:
                action_color = "#00ff41" if rec.get("action") == "BUY" else "#ff0000"
                st.markdown(
                    f"<span style='color:{action_color}'>{rec.get('action')}</span> "
                    f"**{rec.get('quantity')}** {rec.get('ticker')} - {rec.get('name')}",
                    unsafe_allow_html=True,
                )

        if selected_indices:
            if st.button("Apply Selected Trades", type="primary", key=f"apply_trades_{log.id}"):
                _apply_pending_trades(log, recommendations, selected_indices, log_service)
    else:
        st.success("All recommendations from this execution have been applied.")


def _render_ollama_status() -> None:
    """Render Ollama local model status."""
    st.subheader("Ollama Status")

    status = check_ollama_status()
    if status["status"] == "ok":
        st.success("Ollama is running.")
        if status["models"]:
            st.write("Available local models:")
            for model in status["models"]:
                st.write(f"- `{model}`")
        else:
            st.warning("Ollama is running but no local models are installed.")
    else:
        st.error(f"Ollama unavailable: {status['error']}")
        st.markdown("[Install Ollama](https://ollama.com/download)")


def _apply_pending_trades(
    log,
    recommendations: list[dict],
    selected_indices: list[int],
    log_service: ExecutionLogService,
) -> None:
    """Apply selected pending trades to the portfolio."""
    security_service = SecurityService()
    portfolio_service = PortfolioService(security_service=security_service)

    # Find the portfolio config file
    portfolios = portfolio_service.list_portfolios()
    portfolio_filename = None
    for filename in portfolios:
        config, _ = portfolio_service.load_portfolio(filename)
        if config.name == log.portfolio_name:
            portfolio_filename = filename
            break

    if not portfolio_filename:
        st.error(f"Could not find portfolio '{log.portfolio_name}'")
        return

    config, state = portfolio_service.load_portfolio(portfolio_filename)

    errors = []
    applied_indices = []
    quoted_prices: dict[str, float] = {}

    try:
        for i in selected_indices:
            rec = recommendations[i]
            ticker = rec.get("ticker", "")
            quantity = rec.get("quantity", 0)
            if quantity <= 0 or not ticker:
                continue
            if ticker not in quoted_prices:
                quoted_prices[ticker] = security_service.get_price(ticker)
    except Exception as e:
        st.error(f"Failed to capture quoted prices: {e}")
        return

    for i in selected_indices:
        rec = recommendations[i]
        ticker = rec.get("ticker", "")
        action = rec.get("action", "")
        quantity = rec.get("quantity", 0)
        reasoning = rec.get("reasoning", "")
        stop_loss_price = rec.get("stop_loss_price")
        take_profit_price = rec.get("take_profit_price")

        try:
            state = portfolio_service.execute_trade(
                state,
                ticker,
                action,
                quantity,
                reasoning,
                price=quoted_prices[ticker],
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                asset_class=config.asset_class,
            )
            applied_indices.append(i)
        except Exception as e:
            errors.append(f"{action} {quantity} {ticker}: {str(e)}")

    # Save state
    portfolio_service.save_state(portfolio_filename, state)

    # Update executed trades in log
    existing_executed = set()
    if log.executed_trades_json:
        try:
            existing_executed = set(json.loads(log.executed_trades_json))
        except json.JSONDecodeError:
            pass

    all_executed = list(existing_executed | set(applied_indices))
    log_service.mark_trades_executed(log.id, all_executed)

    # Store messages in session state for persistence across rerun
    messages = []
    if applied_indices:
        messages.append({
            "type": "success",
            "text": f"Successfully applied {len(applied_indices)} trade(s)!",
        })

    if errors:
        for error in errors:
            messages.append({
                "type": "error",
                "text": error,
            })

    if messages:
        st.session_state["system_health_messages"] = messages

    st.rerun()
