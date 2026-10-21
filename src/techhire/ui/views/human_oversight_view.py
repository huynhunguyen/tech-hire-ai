"""Area 3 - HR approval gate and audit trail (Art. 14 and Art. 12)."""

import pandas as pd
import streamlit as st

from techhire.domain.exceptions import AuditLogCorruptedError, DecisionValidationError
from techhire.domain.models import AuditRecord, DecisionRequest, HrDecision, is_override
from techhire.services.compliance_pipeline import ComplianceSystem
from techhire.services.screening_service import CandidateAssessment
from techhire.ui import state
from techhire.ui.components import badge, legal_note, recommendation_badge, render_badges, section_header

HR_ID_KEY = "oversight_hr_id"
DECISION_KEY = "oversight_decision"
JUSTIFICATION_KEY = "oversight_justification"
ATTESTATION_KEY = "oversight_attestation"
BOUND_CANDIDATE_KEY = "oversight_bound_candidate"
# Below this override rate, with enough decisions, reviewers may be deferring to the AI by habit.
AUTOMATION_BIAS_OVERRIDE_RATE = 0.05
AUTOMATION_BIAS_MIN_DECISIONS = 10


def _reset_form_for_new_candidate(candidate_id: str) -> None:
    # A decision drafted for one candidate must never carry over to the next one.
    if st.session_state.get(BOUND_CANDIDATE_KEY) != candidate_id:
        st.session_state[BOUND_CANDIDATE_KEY] = candidate_id
        st.session_state[DECISION_KEY] = None
        st.session_state[JUSTIFICATION_KEY] = ""
        st.session_state[ATTESTATION_KEY] = False
        st.session_state.pop(state.DECISION_FEEDBACK_KEY, None)


def _submit_decision(system: ComplianceSystem, assessment: CandidateAssessment) -> None:
    decision_value = st.session_state.get(DECISION_KEY)
    if decision_value is None:
        st.session_state[state.DECISION_FEEDBACK_KEY] = ("error", ["Cần chọn quyết định cuối cùng."])
        return

    request = DecisionRequest(
        hr_id=str(st.session_state.get(HR_ID_KEY, "")).strip(),
        candidate_id=assessment.profile.candidate_id,
        ai_score=assessment.screening.matching_score,
        ai_recommendation=assessment.screening.recommendation,
        hr_decision=HrDecision(decision_value),
        justification=str(st.session_state.get(JUSTIFICATION_KEY, "")),
        explanation_reviewed=bool(st.session_state.get(ATTESTATION_KEY)),
        model_version=assessment.screening.model_version,
    )
    try:
        record = system.decision_gate.submit(request)
    except DecisionValidationError as error:
        st.session_state[state.DECISION_FEEDBACK_KEY] = ("error", error.violations)
        return
    except AuditLogCorruptedError as error:
        st.session_state[state.DECISION_FEEDBACK_KEY] = ("error", [f"Nhật ký kiểm toán bị lỗi, từ chối ghi: {error}"])
        return

    st.session_state[state.DECISION_FEEDBACK_KEY] = ("success", record)
    st.session_state[DECISION_KEY] = None
    st.session_state[JUSTIFICATION_KEY] = ""
    st.session_state[ATTESTATION_KEY] = False


def _render_feedback() -> None:
    feedback = st.session_state.get(state.DECISION_FEEDBACK_KEY)
    if not feedback:
        return
    kind, payload = feedback
    if kind == "error":
        st.error("Quyết định chưa được ghi nhận:\n\n" + "\n".join(f"- {violation}" for violation in payload))
    else:
        record: AuditRecord = payload
        st.success(
            f"Đã ghi nhận quyết định '{record.hr_decision}' cho {record.candidate_id} vào nhật ký kiểm toán. "
            f"Mã băm bản ghi: {record.record_hash[:16]}..."
        )


def _render_decision_gate(system: ComplianceSystem, assessment: CandidateAssessment) -> None:
    section_header("3.1", "Chốt chặn quyết định (Human-in-the-loop Gate)")
    screening = assessment.screening
    _reset_form_for_new_candidate(screening.candidate_id)

    with st.container(border=True):
        left, middle, right = st.columns([2, 2, 3])
        left.metric("Ứng viên", screening.candidate_id)
        middle.metric("Điểm AI", f"{screening.matching_score_percent:.1f}%")
        with right:
            st.caption("Đề xuất tham mưu của AI")
            render_badges(recommendation_badge(screening.recommendation))
        st.caption(
            "Lưu ý thiên kiến tự động hóa (Điều 14(4)(b)): đề xuất của AI có thể sai. Hãy tự đánh giá dựa trên "
            "thẻ điểm giải trình và hồ sơ, không mặc nhiên chấp thuận."
        )

    previous = [record for record in _safe_read_records(system) if record.candidate_id == screening.candidate_id]
    if previous:
        st.info(
            f"Ứng viên này đã có {len(previous)} quyết định trước đó. Quyết định mới sẽ được ghi thêm như một bản "
            "sửa đổi; bản ghi cũ không bị xóa (nhật ký chỉ cho phép ghi nối)."
        )

    hr_column, decision_column = st.columns([1, 2])
    hr_column.text_input(
        "Mã HR người duyệt",
        key=HR_ID_KEY,
        placeholder="VD: HR-001",
        help=f"Danh sách được ủy quyền: {', '.join(system.decision_gate.authorized_hr_ids)}",
    )
    decision_column.radio(
        "Quyết định cuối cùng của HR",
        [decision.value for decision in HrDecision],
        key=DECISION_KEY,
        index=None,
        horizontal=True,
    )
    selected = st.session_state.get(DECISION_KEY)
    if selected is not None and is_override(screening.recommendation, HrDecision(selected)):
        st.warning(
            "Quyết định này PHỦ QUYẾT đề xuất của AI. Đây là quyền hợp pháp của người giám sát (Điều 14(4)(d)); "
            "hệ thống sẽ đánh dấu Override trong nhật ký."
        )

    st.text_area(
        "Lý do / ghi chú đánh giá (bắt buộc)",
        key=JUSTIFICATION_KEY,
        height=110,
        placeholder="Nêu căn cứ năng lực cụ thể: kinh nghiệm, kỹ năng, kết quả phỏng vấn, chứng chỉ, yêu cầu vị trí...",
        help=(
            f"Tối thiểu {system.settings.oversight.min_justification_chars} ký tự, "
            f"{system.settings.oversight.min_justification_words} từ; phải nêu căn cứ năng lực; không viện dẫn "
            "thuộc tính được bảo vệ; không sao chép lý do của các quyết định gần đây."
        ),
    )
    st.checkbox(
        "Tôi xác nhận đã xem xét thẻ điểm giải trình và tự chịu trách nhiệm về quyết định này.",
        key=ATTESTATION_KEY,
    )
    st.button(
        "Xác nhận quyết định",
        type="primary",
        on_click=_submit_decision,
        args=(system, assessment),
    )
    _render_feedback()


def _safe_read_records(system: ComplianceSystem) -> list[AuditRecord]:
    try:
        return system.audit_logger.read_records()
    except AuditLogCorruptedError:
        return []


def _records_frame(records: list[AuditRecord]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Thời gian (UTC)": record.timestamp,
                "Mã HR": record.hr_id,
                "Mã ứng viên": record.candidate_id,
                "Điểm AI (%)": round(record.ai_score * 100, 1),
                "Đề xuất AI": record.ai_recommendation,
                "Quyết định HR": record.hr_decision,
                "Phủ quyết (Override)": "Có" if record.is_override else "Không",
                "Lý do chi tiết": record.justification,
                "Phiên bản mô hình": record.model_version,
                "Mã băm": record.record_hash[:12],
            }
            for record in records
        ]
    )


def _render_audit_trail(system: ComplianceSystem) -> None:
    section_header("3.2", "Bảng truy xuất nhật ký hệ thống (Audit Trail)")
    integrity = system.audit_logger.verify_integrity()
    if integrity.is_valid:
        render_badges(badge(integrity.message, "positive"))
    else:
        st.error(f"PHÁT HIỆN CAN THIỆP NHẬT KÝ: {integrity.message}")

    try:
        records = system.audit_logger.read_records()
    except AuditLogCorruptedError as error:
        st.error(f"Không thể đọc nhật ký: {error}")
        return
    if not records:
        st.info("Chưa có quyết định nào được ghi nhận.")
        return

    override_count = sum(record.is_override for record in records)
    override_rate = override_count / len(records)
    columns = st.columns(4)
    columns[0].metric("Tổng quyết định", len(records))
    columns[1].metric("Số lần phủ quyết", override_count)
    columns[2].metric("Tỷ lệ phủ quyết", f"{override_rate:.0%}")
    columns[3].metric("Số người duyệt", len({record.hr_id for record in records}))
    if len(records) >= AUTOMATION_BIAS_MIN_DECISIONS and override_rate < AUTOMATION_BIAS_OVERRIDE_RATE:
        st.warning(
            "Tỷ lệ phủ quyết rất thấp: có thể là dấu hiệu duyệt hình thức (rubber-stamping). "
            "Đề nghị rà soát quy trình giám sát và đào tạo lại người duyệt (Điều 14(4), Điều 26(2))."
        )

    filter_hr, filter_override, filter_candidate = st.columns([2, 1, 2])
    selected_hr = filter_hr.multiselect("Lọc theo mã HR", sorted({record.hr_id for record in records}))
    overrides_only = filter_override.checkbox("Chỉ hiện phủ quyết")
    candidate_query = filter_candidate.text_input("Tìm mã ứng viên")

    filtered = [
        record
        for record in records
        if (not selected_hr or record.hr_id in selected_hr)
        and (not overrides_only or record.is_override)
        and candidate_query.strip().lower() in record.candidate_id.lower()
    ]
    frame = _records_frame(list(reversed(filtered)))
    st.dataframe(frame, hide_index=True, width="stretch")

    download_csv, download_jsonl = st.columns(2)
    download_csv.download_button(
        "Xuất CSV (bản lọc)",
        data=frame.to_csv(index=False).encode("utf-8-sig"),
        file_name="techhire_audit_trail.csv",
        mime="text/csv",
    )
    download_jsonl.download_button(
        "Xuất JSONL gốc (có chuỗi băm)",
        data=system.audit_logger.log_path.read_bytes(),
        file_name=system.audit_logger.log_path.name,
        mime="application/jsonl",
    )
    st.caption(
        "Nhật ký chỉ lưu mã ứng viên (bút danh hóa) và không lưu giới tính, độ tuổi, sắc tộc - "
        "tuân thủ nguyên tắc tối thiểu hóa dữ liệu (GDPR Điều 5(1)(c))."
    )


def render(system: ComplianceSystem) -> None:
    legal_note(
        "<b>Điều 14 EU AI Act - Giám sát của con người.</b> Người giám sát phải có khả năng không sử dụng, bỏ qua "
        "hoặc đảo ngược đầu ra của hệ thống. <b>Điều 12 - Lưu giữ hồ sơ.</b> Hệ thống phải tự động ghi nhật ký "
        "sự kiện để bảo đảm truy vết trong suốt vòng đời."
    )
    assessment = state.get_current_assessment()
    if assessment is None:
        st.info("Hãy chọn và đánh giá một hồ sơ ở khu vực 2 trước khi ra quyết định.")
    else:
        _render_decision_gate(system, assessment)
    st.divider()
    _render_audit_trail(system)
