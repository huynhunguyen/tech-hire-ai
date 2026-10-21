"""Area 2 - Candidate evaluation and XAI scorecard (Art. 13 and GDPR Art. 22)."""

import pandas as pd
import streamlit as st

from techhire.domain import schema
from techhire.domain.exceptions import InvalidCandidateProfileError
from techhire.domain.models import CandidateProfile, Scorecard
from techhire.explainability.value_formatter import format_attribute_value
from techhire.services.compliance_pipeline import ComplianceSystem
from techhire.services.screening_service import CandidateAssessment
from techhire.ui import charts, state
from techhire.ui.components import legal_note, recommendation_badge, render_badges, section_header

SOURCE_POOL = "Hồ sơ trong tập đánh giá"
SOURCE_MANUAL = "Nhập hồ sơ mới"
LATENCY_BUDGET_MS = 2000


def _scorecard_table(scorecard: Scorecard) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Thuộc tính năng lực": item.label,
                "Giá trị": item.display_value,
                "Đóng góp (điểm)": f"{item.contribution_points:+.1f}",
                "Chiều tác động": "Nâng điểm" if item.contribution > 0 else "Giảm điểm",
            }
            for item in scorecard.contributions
        ]
    )


def _select_pool_candidate(system: ComplianceSystem) -> tuple[CandidateAssessment, pd.DataFrame]:
    candidate_ids = system.candidate_pool[schema.CANDIDATE_ID].tolist()
    candidate_id = st.selectbox(
        "Mã ứng viên",
        candidate_ids,
        help="Tập đánh giá gồm các hồ sơ mô hình chưa từng thấy khi huấn luyện.",
    )
    candidate_row = system.candidate_pool[system.candidate_pool[schema.CANDIDATE_ID] == candidate_id]
    profile = CandidateProfile.from_record(candidate_row.iloc[0].to_dict())
    return system.screening_service.assess(profile), candidate_row


def _manual_candidate_form(system: ComplianceSystem) -> CandidateAssessment | None:
    with st.form("manual_candidate_form"):
        first, second, third = st.columns(3)
        candidate_id = first.text_input("Mã ứng viên", value="NEW-0001")
        experience = second.number_input("Số năm kinh nghiệm", min_value=-10.0, max_value=80.0, value=5.0, step=0.5)
        education = third.selectbox("Trình độ học vấn", schema.EDUCATION_LEVELS, index=1)
        skill = first.number_input("Điểm kỹ năng (0-100)", min_value=-100.0, max_value=1000.0, value=70.0, step=1.0)
        interview = second.number_input(
            "Điểm phỏng vấn chuyên môn (0-100)", min_value=-100.0, max_value=1000.0, value=65.0, step=1.0
        )
        certifications = third.number_input("Số lượng chứng chỉ", min_value=-10, max_value=100, value=2, step=1)
        st.caption(
            "Biểu mẫu cố ý cho phép nhập giá trị ngoài miền để minh họa lớp kiểm tra đầu vào (Điều 15). "
            "Không có trường giới tính, độ tuổi hay sắc tộc."
        )
        submitted = st.form_submit_button("Đánh giá hồ sơ", type="primary")

    if submitted:
        try:
            profile = CandidateProfile(
                candidate_id=candidate_id.strip(),
                experience_years=float(experience),
                education_level=education,
                skill_score=float(skill),
                interview_score=float(interview),
                certification_count=int(certifications),
            )
        except InvalidCandidateProfileError as error:
            st.error("Hồ sơ bị từ chối bởi lớp kiểm tra đầu vào:\n\n" + "\n".join(f"- {v}" for v in error.violations))
            return None
        state.set_manual_assessment(system.screening_service.assess(profile))
    return state.get_manual_assessment()


def _render_profile(assessment: CandidateAssessment) -> None:
    record = assessment.profile.to_record()
    rows = [
        {"Thuộc tính": schema.label_of(attribute), "Giá trị": format_attribute_value(attribute, record[attribute])}
        for attribute in schema.COMPETENCE_FEATURES
    ]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.caption("Giới tính, độ tuổi và sắc tộc được ẩn khỏi giao diện đánh giá để giảm thiên kiến của người duyệt.")


def _render_result(assessment: CandidateAssessment) -> None:
    screening = assessment.screening
    st.metric("Mức độ phù hợp (Matching Score)", f"{screening.matching_score_percent:.1f}%")
    render_badges(recommendation_badge(screening.recommendation))
    within_budget = assessment.latency_ms < LATENCY_BUDGET_MS
    st.caption(
        f"Thời gian chấm điểm + giải thích: {assessment.latency_ms:.0f} ms "
        f"({'đạt' if within_budget else 'vượt'} yêu cầu < {LATENCY_BUDGET_MS} ms, CPU localhost)."
    )
    st.caption(f"Phiên bản mô hình: `{screening.model_version}`")
    st.caption("Kết quả chỉ mang tính tham mưu. Hệ thống không tự động loại hay nhận ứng viên.")


def _render_scorecard(assessment: CandidateAssessment) -> None:
    section_header("2.2", "Thẻ điểm giải trình (Local XAI - SHAP)")
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.plotly_chart(charts.scorecard_chart(assessment.scorecard), width="stretch")
    with right:
        st.dataframe(_scorecard_table(assessment.scorecard), hide_index=True, width="stretch")
        st.caption(
            "Bảo vệ bí mật kinh doanh: chỉ hiển thị đóng góp cục bộ của hồ sơ này, đã làm tròn; "
            "không công bố cấu trúc cây, trọng số hay mức độ quan trọng toàn cục của mô hình."
        )

    section_header("2.3", "Lời giải thích dành cho ứng viên (GDPR Điều 22(3))")
    st.text_area(
        "Nội dung HR có thể gửi cho ứng viên",
        value=assessment.explanation,
        height=140,
        key=f"explanation_{assessment.profile.candidate_id}",
    )


def _render_fairness_probe(system: ComplianceSystem, candidate_row: pd.DataFrame) -> None:
    with st.expander("Chế độ kiểm toán viên: kiểm tra phản thực tế theo giới tính"):
        st.caption(
            "Chỉ dành cho kiểm toán tuân thủ. Giữ nguyên năng lực, chỉ đổi giới tính của hồ sơ và so sánh "
            "điểm giữa mô hình chưa tuân thủ và mô hình đã tuân thủ."
        )
        probe = system.screening_service.probe_fairness(candidate_row)
        if probe.reference_counterfactual is None:
            st.info("Hồ sơ không thuộc nhóm giới tính nhị phân nên không áp dụng phép thử này.")
            return
        reference = probe.reference_counterfactual
        compliant = probe.compliant_counterfactual
        left, right = st.columns(2)
        with left:
            st.markdown("**Mô hình chưa tuân thủ**")
            st.metric(f"Giới tính gốc: {reference.original_gender}", f"{reference.original_score:.1%}")
            st.metric(
                f"Nếu là: {reference.counterfactual_gender}",
                f"{reference.counterfactual_score:.1%}",
                delta=f"{reference.score_delta * 100:+.1f} điểm",
            )
        with right:
            st.markdown("**Mô hình đã tuân thủ**")
            st.metric(f"Giới tính gốc: {compliant.original_gender}", f"{compliant.original_score:.1%}")
            st.metric(
                f"Nếu là: {compliant.counterfactual_gender}",
                f"{compliant.counterfactual_score:.1%}",
                delta=f"{compliant.score_delta * 100:+.1f} điểm",
            )
        gender_points = probe.reference_scorecard.contribution_of(schema.GENDER) * 100
        st.markdown(
            f"Trong mô hình chưa tuân thủ, riêng thuộc tính **Giới tính** đóng góp **{gender_points:+.1f} điểm** "
            "vào kết quả của hồ sơ này - bằng chứng định lượng về thiên kiến lịch sử mà Điều 10 yêu cầu loại bỏ."
        )
        st.plotly_chart(charts.scorecard_chart(probe.reference_scorecard), width="stretch")


def render(system: ComplianceSystem) -> None:
    legal_note(
        "<b>Điều 13 EU AI Act - Minh bạch.</b> Người triển khai phải hiểu và diễn giải được đầu ra của hệ thống. "
        "<b>GDPR Điều 22 và Điều 15(1)(h)</b> - ứng viên có quyền nhận thông tin có ý nghĩa về logic xử lý và "
        "quyền yêu cầu sự can thiệp của con người."
    )
    section_header("2.1", "Chọn và đánh giá hồ sơ")
    source = st.radio("Nguồn hồ sơ", [SOURCE_POOL, SOURCE_MANUAL], horizontal=True, label_visibility="collapsed")

    candidate_row = None
    if source == SOURCE_POOL:
        assessment, candidate_row = _select_pool_candidate(system)
    else:
        assessment = _manual_candidate_form(system)
        if assessment is None:
            st.info("Nhập thông tin năng lực và bấm 'Đánh giá hồ sơ'.")
            return

    state.set_current_assessment(assessment, candidate_row)
    left, right = st.columns([3, 2], gap="large")
    with left:
        _render_profile(assessment)
    with right:
        _render_result(assessment)

    _render_scorecard(assessment)
    if candidate_row is not None:
        _render_fairness_probe(system, candidate_row)
