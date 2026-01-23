"""Skeleton loader components for loading states."""

import streamlit as st


def render_skeleton_text(width: str = "100%", height: str = "1em") -> None:
    """Render a skeleton text placeholder."""
    st.markdown(
        f'<div class="skeleton skeleton-text" style="width: {width}; height: {height};"></div>',
        unsafe_allow_html=True,
    )


def render_skeleton_metric() -> None:
    """Render a skeleton metric placeholder (label + value)."""
    st.markdown(
        """<div>
            <div class="skeleton" style="width: 40%; height: 0.8em; margin-bottom: 0.5em;"></div>
            <div class="skeleton skeleton-metric" style="width: 80%;"></div>
        </div>""",
        unsafe_allow_html=True,
    )


def render_skeleton_table(rows: int = 5, cols: int = 4) -> None:
    """Render a skeleton table placeholder."""
    # Header row
    header_cells = "".join(
        f'<div class="skeleton" style="height: 1em; flex: 1; margin: 0 4px;"></div>'
        for _ in range(cols)
    )

    # Data rows
    data_rows = ""
    for _ in range(rows):
        cells = "".join(
            f'<div class="skeleton" style="height: 1em; flex: 1; margin: 0 4px;"></div>'
            for _ in range(cols)
        )
        data_rows += f'<div style="display: flex; margin: 8px 0;">{cells}</div>'

    st.markdown(
        f"""<div style="padding: 1rem; border: 1px solid #003b00; border-radius: 0px; background-color: rgba(0, 20, 0, 0.3);">
            <div style="display: flex; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #003b00;">
                {header_cells}
            </div>
            {data_rows}
        </div>""",
        unsafe_allow_html=True,
    )


def render_skeleton_card() -> None:
    """Render a skeleton card placeholder (for portfolio tiles)."""
    st.markdown(
        """<div class="skeleton-card">
            <div class="skeleton skeleton-title"></div>
            <div style="display: flex; gap: 1rem; margin: 1rem 0;">
                <div style="flex: 1;">
                    <div class="skeleton" style="height: 0.7em; width: 50%; margin-bottom: 0.5em;"></div>
                    <div class="skeleton" style="height: 1.5em; width: 80%;"></div>
                </div>
                <div style="flex: 1;">
                    <div class="skeleton" style="height: 0.7em; width: 50%; margin-bottom: 0.5em;"></div>
                    <div class="skeleton" style="height: 1.5em; width: 80%;"></div>
                </div>
            </div>
            <div class="skeleton" style="height: 2.5em; width: 100%; margin-top: 1rem;"></div>
        </div>""",
        unsafe_allow_html=True,
    )


def render_skeleton_holdings() -> None:
    """Render skeleton placeholder for holdings table."""
    st.subheader("Current Holdings")
    render_skeleton_table(rows=4, cols=8)


def render_skeleton_metrics_row(count: int = 5) -> None:
    """Render a row of skeleton metrics."""
    cols = st.columns(count)
    for col in cols:
        with col:
            render_skeleton_metric()
