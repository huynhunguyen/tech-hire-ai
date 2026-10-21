"""Reusable presentational widgets."""

import html

import streamlit as st

from techhire.domain.models import Recommendation


def legal_note(text: str) -> None:
    st.markdown(f'<div class="th-legal">{text}</div>', unsafe_allow_html=True)


def badge(text: str, tone: str = "neutral") -> str:
    return f'<span class="th-badge th-badge-{tone}">{html.escape(text)}</span>'


def render_badges(*badges: str) -> None:
    st.markdown("".join(badges), unsafe_allow_html=True)


def recommendation_badge(recommendation: Recommendation) -> str:
    tone = "positive" if recommendation is Recommendation.RECOMMEND_INTERVIEW else "warning"
    return badge(recommendation.value, tone)


def section_header(index: str, title: str) -> None:
    st.markdown(f'#### <span class="th-section-index">{index}</span> {html.escape(title)}', unsafe_allow_html=True)


def format_ratio(value: float) -> str:
    return "∞" if value == float("inf") else f"{value:.2f}"


def format_percent(value: float) -> str:
    return f"{value * 100:.1f}%"
