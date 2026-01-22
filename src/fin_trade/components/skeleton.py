"""Skeleton loader components for loading states."""

import streamlit as st

# CSS for skeleton animation - injected once per page
_SKELETON_CSS = """
<style>
@keyframes skeleton-pulse {
    0% { opacity: 0.6; }
    50% { opacity: 0.3; }
    100% { opacity: 0.6; }
}
.skeleton {
    background: linear-gradient(90deg, #2d2d2d 25%, #3d3d3d 50%, #2d2d2d 75%);
    background-size: 200% 100%;
    animation: skeleton-pulse 1.5s ease-in-out infinite;
    border-radius: 4px;
}
.skeleton-text {
    height: 1em;
    margin: 0.5em 0;
}
.skeleton-title {
    height: 1.5em;
    width: 60%;
    margin: 0.5em 0;
}
.skeleton-metric {
    height: 2.5em;
    margin: 0.25em 0;
}
.skeleton-card {
    padding: 1rem;
    border: 1px solid #3d3d3d;
    border-radius: 8px;
    margin-bottom: 1rem;
}
</style>
"""

_css_injected = False


def _inject_css() -> None:
    """Inject skeleton CSS once per session."""
    global _css_injected
    if not _css_injected:
        st.markdown(_SKELETON_CSS, unsafe_allow_html=True)
        _css_injected = True


def render_skeleton_text(width: str = "100%", height: str = "1em") -> None:
    """Render a skeleton text placeholder."""
    _inject_css()
    st.markdown(
        f'<div class="skeleton skeleton-text" style="width: {width}; height: {height};"></div>',
        unsafe_allow_html=True,
    )


def render_skeleton_metric() -> None:
    """Render a skeleton metric placeholder (label + value)."""
    _inject_css()
    st.markdown(
        """<div>
            <div class="skeleton" style="width: 40%; height: 0.8em; margin-bottom: 0.5em;"></div>
            <div class="skeleton skeleton-metric" style="width: 80%;"></div>
        </div>""",
        unsafe_allow_html=True,
    )


def render_skeleton_table(rows: int = 5, cols: int = 4) -> None:
    """Render a skeleton table placeholder."""
    _inject_css()

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
        f"""<div style="padding: 1rem; border: 1px solid #3d3d3d; border-radius: 8px;">
            <div style="display: flex; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #3d3d3d;">
                {header_cells}
            </div>
            {data_rows}
        </div>""",
        unsafe_allow_html=True,
    )


def render_skeleton_card() -> None:
    """Render a skeleton card placeholder (for portfolio tiles)."""
    _inject_css()
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
    _inject_css()
    st.subheader("Current Holdings")
    render_skeleton_table(rows=4, cols=8)


def render_skeleton_metrics_row(count: int = 5) -> None:
    """Render a row of skeleton metrics."""
    _inject_css()
    cols = st.columns(count)
    for col in cols:
        with col:
            render_skeleton_metric()
