"""Visual tokens and the small amount of CSS the dashboard needs on top of the Streamlit theme."""

import streamlit as st

PRIMARY_COLOR = "#1F4E79"
POSITIVE_COLOR = "#2E7D5B"
NEGATIVE_COLOR = "#B23A48"
WARNING_COLOR = "#B7791F"
NEUTRAL_COLOR = "#7A8699"
COMPLIANT_COLOR = "#2E7D5B"
NON_COMPLIANT_COLOR = "#B23A48"
UNAWARE_COLOR = "#B7791F"

DASHBOARD_CSS = """
<style>
h1, h2, h3 { letter-spacing: 0.2px; }
.block-container { padding-top: 2.2rem; max-width: 1320px; }
.th-subtitle { color: #5B6675; font-size: 1.02rem; margin-top: -0.6rem; }
.th-legal {
    border-left: 4px solid #1F4E79;
    background: rgba(31, 78, 121, 0.07);
    padding: 0.6rem 0.9rem;
    border-radius: 4px;
    font-size: 0.93rem;
    margin: 0.2rem 0 1rem 0;
}
.th-badge {
    display: inline-block;
    padding: 0.18rem 0.6rem;
    border-radius: 999px;
    font-size: 0.82rem;
    font-weight: 600;
    margin: 0 0.3rem 0.3rem 0;
    border: 1px solid currentColor;
}
.th-badge-positive { color: #2E7D5B; background: rgba(46, 125, 91, 0.10); }
.th-badge-negative { color: #B23A48; background: rgba(178, 58, 72, 0.10); }
.th-badge-warning { color: #B7791F; background: rgba(183, 121, 31, 0.12); }
.th-badge-neutral { color: #4A5A70; background: rgba(122, 134, 153, 0.12); }
.th-section-index { color: #1F4E79; font-weight: 700; }
</style>
"""


def apply_theme() -> None:
    st.markdown(DASHBOARD_CSS, unsafe_allow_html=True)
