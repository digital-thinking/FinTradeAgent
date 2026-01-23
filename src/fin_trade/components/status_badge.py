"""Reusable status badge component."""

import streamlit as st


def render_status_badge(is_overdue: bool) -> None:
    """Render a status badge indicating if the portfolio is overdue or current."""
    if is_overdue:
        st.markdown(
            """<div style="background: rgba(255, 0, 0, 0.1); color: #000000 !important; padding: 4px 8px;
            border: 1px solid #ff0000; font-size: 0.75em; text-align: center; font-weight: 500;
            font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif; text-transform: uppercase; letter-spacing: 0.5px;">
            ⚠️ OVERDUE</div>""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """<div style="background: rgba(0, 143, 17, 0.1); color: #000000 !important; padding: 4px 8px;
            border: 1px solid #008F11; font-size: 0.75em; text-align: center; font-weight: 500;
            font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif; text-transform: uppercase; letter-spacing: 0.5px;">
            ✓ Current</div>""",
            unsafe_allow_html=True,
        )


def render_large_status_badge(is_overdue: bool, overdue_count: int = 0) -> None:
    """Render a large status badge for overview/detail pages."""
    if is_overdue:
        label = f"{overdue_count} Overdue" if overdue_count > 0 else "OVERDUE"
        st.markdown(
            f"""<div style="background: rgba(255, 0, 0, 0.05); border: 1px solid #ff0000;
            padding: 12px; text-align: center;">
            <span style="font-size: 0.8em; color: #000000 !important; font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif; text-transform: uppercase; letter-spacing: 0.5px;">STATUS</span><br>
            <span style="font-size: 1.2em; font-weight: bold; color: #000000 !important; font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif; text-transform: uppercase; letter-spacing: 0.5px;">⚠️ {label}</span>
            </div>""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """<div style="background: rgba(0, 143, 17, 0.05); border: 1px solid #008F11;
            padding: 12px; text-align: center;">
            <span style="font-size: 0.8em; color: #000000 !important; font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif; text-transform: uppercase; letter-spacing: 0.5px;">STATUS</span><br>
            <span style="font-size: 1.2em; font-weight: bold; color: #000000 !important; font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif; text-transform: uppercase; letter-spacing: 0.5px;">✓ CURRENT</span>
            </div>""",
            unsafe_allow_html=True,
        )
