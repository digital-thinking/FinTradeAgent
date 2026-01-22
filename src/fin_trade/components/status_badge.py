"""Reusable status badge component."""

import streamlit as st


def render_status_badge(is_overdue: bool) -> None:
    """Render a status badge indicating if the portfolio is overdue or current."""
    if is_overdue:
        st.markdown(
            """<div style="background: #ff6b6b; color: white; padding: 4px 8px;
            border-radius: 12px; font-size: 0.75em; text-align: center; font-weight: 500;">
            ⚠️ OVERDUE</div>""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """<div style="background: #51cf66; color: white; padding: 4px 8px;
            border-radius: 12px; font-size: 0.75em; text-align: center; font-weight: 500;">
            ✓ Current</div>""",
            unsafe_allow_html=True,
        )


def render_large_status_badge(is_overdue: bool, overdue_count: int = 0) -> None:
    """Render a large status badge for overview/detail pages."""
    if is_overdue:
        label = f"{overdue_count} Overdue" if overdue_count > 0 else "OVERDUE"
        st.markdown(
            f"""<div style="background: linear-gradient(135deg, #ff6b6b, #ee5a5a);
            padding: 12px; border-radius: 8px; text-align: center;">
            <span style="font-size: 0.8em; color: rgba(255,255,255,0.8);">Status</span><br>
            <span style="font-size: 1.2em; font-weight: bold; color: white;">⚠️ {label}</span>
            </div>""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """<div style="background: linear-gradient(135deg, #51cf66, #40c057);
            padding: 12px; border-radius: 8px; text-align: center;">
            <span style="font-size: 0.8em; color: rgba(255,255,255,0.8);">Status</span><br>
            <span style="font-size: 1.2em; font-weight: bold; color: white;">✓ Current</span>
            </div>""",
            unsafe_allow_html=True,
        )
