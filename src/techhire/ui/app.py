"""Streamlit entry point for the TechHire AI compliance dashboard."""

import streamlit as st

from techhire.domain.exceptions import SchemaValidationError
from techhire.services.compliance_pipeline import ComplianceSystem, build_compliance_system
from techhire.ui.components import badge, render_badges
from techhire.ui.theme import apply_theme
from techhire.ui.views import candidate_evaluation_view, data_governance_view, human_oversight_view

TAB_TITLES = (
    "1. Kiểm toán dữ liệu & Đối chứng mô hình (Điều 10)",
    "2. Đánh giá ứng viên & Thẻ điểm XAI (Điều 13, GDPR Điều 22)",
    "3. Phê duyệt HR & Nhật ký hệ thống (Điều 14, Điều 12)",
)


@st.cache_resource(show_spinner="Đang kiểm toán dữ liệu và huấn luyện mô hình...")
def _load_system() -> ComplianceSystem:
    return build_compliance_system()


def _render_sidebar(system: ComplianceSystem) -> None:
    with st.sidebar:
        st.markdown("### Hồ sơ tuân thủ")
        st.markdown("**Phân loại pháp lý**")
        render_badges(badge("AI rủi ro cao", "negative"), badge("Phụ lục III, Mục 4(a)", "neutral"))
        st.markdown("**Vai trò hệ thống**")
        st.caption("Hỗ trợ ra quyết định. Không tự động loại hoặc nhận ứng viên.")
        st.markdown("**Loại bỏ từ khâu thiết kế**")
        st.caption(
            "Mô-đun nhận diện cảm xúc / phân tích video phỏng vấn thuộc thực hành bị cấm "
            "(Điều 5(1)(f)) nên không tồn tại trong hệ thống."
        )
        st.markdown("**Bốn trụ cột tuân thủ**")
        render_badges(
            badge("Điều 10 - Quản trị dữ liệu", "positive"),
            badge("Điều 13 & GDPR 22 - Giải thích", "positive"),
            badge("Điều 14 - Giám sát con người", "positive"),
            badge("Điều 12 - Lưu vết", "positive"),
        )
        st.divider()
        st.markdown("**Thông tin vận hành**")
        settings = system.settings
        st.caption(f"Dữ liệu: {system.governance.load_report.source}")
        st.caption(f"Mô hình phục vụ: `{system.compliant_model.model_version}`")
        st.caption(f"Ngưỡng khuyến nghị phỏng vấn: {settings.recommendation.interview_threshold:.0%}")
        st.caption(f"Ngưỡng DIR: {settings.fairness.dir_threshold:.2f}")
        st.caption(f"Nhật ký: `{system.audit_logger.log_path}`")
        if st.button("Nạp lại dữ liệu và huấn luyện lại"):
            _load_system.clear()
            st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="TechHire AI - Sàng lọc hồ sơ tuân thủ EU AI Act",
        page_icon=":material/balance:",
        layout="wide",
    )
    apply_theme()

    try:
        system = _load_system()
    except SchemaValidationError as error:
        st.error(f"Dữ liệu đầu vào không hợp lệ: {error}")
        st.stop()

    st.title("TechHire AI - Sàng lọc và Đánh giá Hồ sơ Ứng viên")
    st.markdown(
        '<p class="th-subtitle">Proof-of-Concept quy trình tuân thủ EU AI Act và GDPR cho hệ thống AI '
        "rủi ro cao trong tuyển dụng</p>",
        unsafe_allow_html=True,
    )
    _render_sidebar(system)

    data_tab, evaluation_tab, oversight_tab = st.tabs(TAB_TITLES)
    # Tabs are rendered in order within one script run, so the assessment selected in tab 2
    # is already in session state when tab 3 renders.
    with data_tab:
        data_governance_view.render(system)
    with evaluation_tab:
        candidate_evaluation_view.render(system)
    with oversight_tab:
        human_oversight_view.render(system)
