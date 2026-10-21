"""Plotly figures used by the dashboard."""

import plotly.graph_objects as go

from techhire.domain.models import Scorecard
from techhire.governance.bias_auditor import FairnessReport
from techhire.ml_engine.model_comparator import ModelEvaluation
from techhire.ml_engine.model_trainer import ModelVariant
from techhire.ui import theme

VARIANT_COLORS = {
    ModelVariant.NON_COMPLIANT: theme.NON_COMPLIANT_COLOR,
    ModelVariant.UNAWARE: theme.UNAWARE_COLOR,
    ModelVariant.COMPLIANT: theme.COMPLIANT_COLOR,
}


def _base_layout(figure: go.Figure, height: int) -> go.Figure:
    figure.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        font=dict(family="Georgia, 'Times New Roman', serif"),
    )
    return figure


def selection_rate_chart(report: FairnessReport) -> go.Figure:
    groups = [item.group for item in report.group_rates]
    rates = [item.selection_rate for item in report.group_rates]
    colors = [
        theme.NEGATIVE_COLOR if group == report.protected_group and not report.passes else theme.PRIMARY_COLOR
        for group in groups
    ]
    figure = go.Figure(
        go.Bar(
            x=groups,
            y=rates,
            marker_color=colors,
            text=[f"{rate:.1%}" for rate in rates],
            textposition="outside",
            customdata=[item.count for item in report.group_rates],
            hovertemplate="%{x}<br>Tỷ lệ chọn: %{y:.1%}<br>Số mẫu: %{customdata}<extra></extra>",
        )
    )
    four_fifths_line = report.rate_of(report.reference_group) * report.threshold
    figure.add_hline(
        y=four_fifths_line,
        line_dash="dash",
        line_color=theme.WARNING_COLOR,
        annotation_text=f"Ngưỡng 4/5 so với {report.reference_group}",
        annotation_position="top left",
    )
    figure.update_yaxes(tickformat=".0%", range=[0, max(rates) * 1.3], title="Tỷ lệ được chọn")
    return _base_layout(figure, 320)


def gender_selection_comparison_chart(evaluations: list[ModelEvaluation]) -> go.Figure:
    figure = go.Figure()
    for evaluation in evaluations:
        report = evaluation.gender_fairness
        figure.add_trace(
            go.Bar(
                name=evaluation.variant.label,
                x=[item.group for item in report.group_rates],
                y=[item.selection_rate for item in report.group_rates],
                marker_color=VARIANT_COLORS[evaluation.variant],
                text=[f"{item.selection_rate:.1%}" for item in report.group_rates],
                textposition="outside",
            )
        )
    figure.update_layout(barmode="group")
    figure.update_yaxes(tickformat=".0%", title="Tỷ lệ được khuyến nghị phỏng vấn")
    return _base_layout(figure, 340)


def scorecard_chart(scorecard: Scorecard) -> go.Figure:
    """Horizontal waterfall from the shared starting point to the candidate's matching score."""
    contributions = list(scorecard.contributions)
    labels = ["Điểm xuất phát chung"] + [f"{item.label}: {item.display_value}" for item in contributions]
    labels.append("Mức độ phù hợp")
    values = [scorecard.base_score * 100] + [item.contribution * 100 for item in contributions]
    values.append(scorecard.matching_score * 100)
    measures = ["absolute"] + ["relative"] * len(contributions) + ["total"]
    texts = [f"{values[0]:.1f}"] + [f"{value:+.1f}" for value in values[1:-1]] + [f"{values[-1]:.1f}%"]

    figure = go.Figure(
        go.Waterfall(
            orientation="h",
            y=labels,
            x=values,
            measure=measures,
            text=texts,
            textposition="outside",
            increasing=dict(marker=dict(color=theme.POSITIVE_COLOR)),
            decreasing=dict(marker=dict(color=theme.NEGATIVE_COLOR)),
            totals=dict(marker=dict(color=theme.PRIMARY_COLOR)),
            connector=dict(line=dict(color=theme.NEUTRAL_COLOR, width=1, dash="dot")),
            hovertemplate="%{y}<br>%{text} điểm<extra></extra>",
        )
    )
    figure.update_xaxes(title="Điểm phần trăm (0 - 100)", range=[0, 105])
    figure.update_yaxes(autorange="reversed")
    return _base_layout(figure, 90 + 42 * len(labels))
