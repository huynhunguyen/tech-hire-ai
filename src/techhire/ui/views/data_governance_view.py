"""Area 1 - Data audit and model comparison (Art. 10)."""

import pandas as pd
import streamlit as st

from techhire.domain import schema
from techhire.governance.bias_auditor import FairnessReport
from techhire.ml_engine.model_comparator import ModelEvaluation
from techhire.ml_engine.model_trainer import ModelVariant
from techhire.services.compliance_pipeline import ComplianceSystem, DataGovernanceSummary
from techhire.ui import charts
from techhire.ui.components import badge, format_percent, format_ratio, legal_note, render_badges, section_header


def _fairness_row(report: FairnessReport) -> dict[str, object]:
    return {
        "Thuộc tính": schema.label_of(report.attribute),
        "Nhóm bất lợi nhất": report.protected_group,
        "Nhóm tham chiếu": report.reference_group,
        "DIR": format_ratio(report.disparate_impact_ratio),
        "Chênh lệch tỷ lệ": f"{report.statistical_parity_difference * 100:+.1f} điểm",
        "Đánh giá": "Đạt" if report.passes else "Không đạt (< 0.80)",
    }


def _render_data_quality(governance: DataGovernanceSummary) -> None:
    report = governance.load_report
    columns = st.columns(4)
    columns[0].metric("Nguồn dữ liệu", "CSV" if report.source.startswith("CSV") else "Mô phỏng", help=report.source)
    columns[1].metric("Bản ghi hợp lệ", f"{report.valid_rows:,}", help=f"Tổng số dòng đọc vào: {report.total_rows:,}")
    columns[2].metric(
        "Bản ghi bị cách ly",
        f"{report.quarantined_rows + report.duplicate_rows_removed:,}",
        help="Thiếu giá trị, ngoài miền hợp lệ hoặc trùng mã ứng viên (Điều 10(3), Điều 15).",
    )
    columns[3].metric(
        "Cột bị loại (allow-list)",
        len(report.dropped_columns),
        help=", ".join(report.dropped_columns) or "Không có",
    )
    if report.quarantined_rows:
        st.warning(
            f"Đã cách ly {report.quarantined_rows} bản ghi không vượt qua kiểm tra lược đồ/miền giá trị. "
            "Đây là lớp phòng thủ đầu tiên trước dữ liệu bị đầu độc (data poisoning, Điều 15(5))."
        )


def _render_historical_audit(governance: DataGovernanceSummary, threshold: float) -> None:
    section_header("1.1", "Kiểm toán thiên kiến trong dữ liệu lịch sử (Bias Auditing)")
    gender = governance.gender_fairness
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.plotly_chart(charts.selection_rate_chart(gender), width="stretch")
    with right:
        st.metric(
            "Disparate Impact Ratio (Nữ / Nam)",
            format_ratio(gender.disparate_impact_ratio),
            delta=f"{gender.disparate_impact_ratio - threshold:+.2f} so với ngưỡng {threshold:.2f}",
            delta_color="normal" if gender.passes else "inverse",
        )
        if gender.passes:
            st.success("Dữ liệu lịch sử đạt quy tắc 4/5 đối với giới tính.")
        else:
            st.error(
                f"CẢNH BÁO THIÊN KIẾN: tỷ lệ tuyển chọn ứng viên nữ chỉ bằng "
                f"{gender.disparate_impact_ratio:.0%} so với ứng viên nam (ngưỡng {threshold:.0%}). "
                "Không được huấn luyện trực tiếp trên dữ liệu này."
            )
        st.caption("Các thuộc tính được bảo vệ khác")
        rows = [_fairness_row(governance.ethnicity_fairness), _fairness_row(governance.age_fairness)]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


def _render_debiasing(governance: DataGovernanceSummary) -> None:
    section_header("1.2", "Tiền xử lý khử thiên kiến (Shift-left Debiasing)")
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("**Bước 1 - Ẩn thuộc tính nhạy cảm khỏi đầu vào mô hình**")
        render_badges(*(badge(f"Đã loại: {schema.label_of(column)}", "negative") for column in governance.removed_attributes))
        render_badges(*(badge(schema.label_of(column), "positive") for column in governance.model_input_columns))
        st.caption(
            "Mô hình đã tuân thủ chỉ nhận các thuộc tính năng lực. Một chốt kiểm tra tự động "
            "(assert_blind_to_sensitive_attributes) chặn việc huấn luyện nếu thuộc tính nhạy cảm lọt vào."
        )
    with right:
        st.markdown("**Bước 2 - Cân bằng lại trọng số mẫu (Sample Reweighing)**")
        cells = pd.DataFrame(
            [
                {
                    "Nhóm": cell.group,
                    "Nhãn lịch sử": "Được tuyển" if cell.label == 1 else "Không tuyển",
                    "Số mẫu": cell.count,
                    "P quan sát": f"{cell.observed_probability:.3f}",
                    "P kỳ vọng": f"{cell.expected_probability:.3f}",
                    "Trọng số": f"{cell.weight:.3f}",
                }
                for cell in governance.reweighing.cells
            ]
        )
        st.dataframe(cells, hide_index=True, width="stretch")
        before = governance.gender_fairness.disparate_impact_ratio
        after = governance.reweighed_gender_fairness.disparate_impact_ratio
        st.caption(
            f"DIR theo giới tính trên tập huấn luyện: {format_ratio(before)} (gốc) → {format_ratio(after)} "
            "(sau tái cân bằng). Trọng số w = P(nhóm)·P(nhãn) / P(nhóm, nhãn)."
        )


def _evaluation_card(evaluation: ModelEvaluation, threshold: float) -> None:
    with st.container(border=True):
        st.markdown(f"**{evaluation.variant.label}**")
        first, second = st.columns(2)
        first.metric("Accuracy (so với nhãn lịch sử)", format_percent(evaluation.accuracy))
        second.metric("ROC-AUC", f"{evaluation.roc_auc:.3f}")
        first.metric("DIR giới tính (dự đoán)", format_ratio(evaluation.gender_fairness.disparate_impact_ratio))
        second.metric("Tỷ lệ đảo kết quả khi đổi giới tính", format_percent(evaluation.counterfactual_flip_rate))
        uses_sensitive = evaluation.variant.uses_sensitive_attributes
        render_badges(
            badge("Dùng thuộc tính nhạy cảm" if uses_sensitive else "Không dùng thuộc tính nhạy cảm",
                  "negative" if uses_sensitive else "positive"),
            badge("Đạt quy tắc 4/5" if evaluation.gender_fairness.disparate_impact_ratio >= threshold
                  else "Không đạt quy tắc 4/5",
                  "positive" if evaluation.gender_fairness.disparate_impact_ratio >= threshold else "negative"),
        )
        st.caption(f"Phiên bản: `{evaluation.model_version}`")


def _render_model_comparison(system: ComplianceSystem) -> None:
    section_header("1.3", "Đối chứng mô hình: trước và sau khi áp dụng luật")
    threshold = system.settings.fairness.dir_threshold
    non_compliant = system.evaluations[ModelVariant.NON_COMPLIANT]
    compliant = system.evaluations[ModelVariant.COMPLIANT]

    left, right = st.columns(2, gap="large")
    with left:
        _evaluation_card(non_compliant, threshold)
    with right:
        _evaluation_card(compliant, threshold)

    st.plotly_chart(
        charts.gender_selection_comparison_chart(list(system.evaluations.values())), width="stretch"
    )
    accuracy_change = (compliant.accuracy - non_compliant.accuracy) * 100
    st.info(
        f"Đánh đổi độ chính xác - công bằng: accuracy thay đổi {accuracy_change:+.1f} điểm, trong khi DIR giới tính "
        f"tăng từ {format_ratio(non_compliant.gender_fairness.disparate_impact_ratio)} lên "
        f"{format_ratio(compliant.gender_fairness.disparate_impact_ratio)}. Accuracy được đo trên nhãn lịch sử "
        "vốn đã thiên lệch, nên phần sụt giảm phản ánh việc mô hình từ chối tái tạo thiên kiến quá khứ."
    )

    with st.expander("Bảng phân tích chi tiết (ablation) cho cả ba biến thể"):
        rows = [
            {
                "Biến thể": evaluation.variant.label,
                "Accuracy": format_percent(evaluation.accuracy),
                "ROC-AUC": f"{evaluation.roc_auc:.3f}",
                "Tỷ lệ khuyến nghị": format_percent(evaluation.selection_rate),
                "DIR giới tính": format_ratio(evaluation.gender_fairness.disparate_impact_ratio),
                "DIR sắc tộc": format_ratio(evaluation.ethnicity_fairness.disparate_impact_ratio),
                "DIR nhóm tuổi": format_ratio(evaluation.age_fairness.disparate_impact_ratio),
                "Đảo kết quả (phản thực tế)": format_percent(evaluation.counterfactual_flip_rate),
            }
            for evaluation in system.evaluations.values()
        ]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        unaware = system.evaluations[ModelVariant.UNAWARE]
        unaware_failures = [
            schema.label_of(report.attribute).lower()
            for report in (unaware.gender_fairness, unaware.ethnicity_fairness, unaware.age_fairness)
            if not report.passes
        ]
        if unaware_failures:
            st.caption(
                f"Chỉ ẩn thuộc tính nhạy cảm (fairness through unawareness) vẫn không đạt quy tắc 4/5 với: "
                f"{', '.join(unaware_failures)}. Nguyên nhân là biến đại diện (proxy), ví dụ số năm kinh nghiệm bị "
                "ảnh hưởng bởi khoảng nghỉ sự nghiệp, và nhãn lịch sử thiên lệch. Bước tái cân bằng trọng số là cần thiết."
            )
        else:
            st.caption("Trên tập dữ liệu hiện tại, chỉ ẩn thuộc tính nhạy cảm đã đủ đạt quy tắc 4/5.")


def render(system: ComplianceSystem) -> None:
    legal_note(
        "<b>Điều 10 EU AI Act - Dữ liệu và quản trị dữ liệu.</b> Dữ liệu huấn luyện của hệ thống rủi ro cao phải "
        "được kiểm tra thiên kiến có khả năng dẫn đến phân biệt đối xử và áp dụng biện pháp phát hiện, ngăn ngừa, "
        "giảm thiểu. Thuộc tính nhạy cảm chỉ được xử lý cho mục đích khử thiên kiến (Điều 10(5))."
    )
    _render_data_quality(system.governance)
    st.divider()
    _render_historical_audit(system.governance, system.settings.fairness.dir_threshold)
    st.divider()
    _render_debiasing(system.governance)
    st.divider()
    _render_model_comparison(system)
