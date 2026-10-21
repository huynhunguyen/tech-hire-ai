"""Human-in-the-loop gate: no decision is final until an authorized reviewer justifies it (Art. 14)."""

import re
import unicodedata

from techhire.config import OversightSettings
from techhire.domain.exceptions import DecisionValidationError
from techhire.domain.models import AuditRecord, DecisionRequest
from techhire.oversight.audit_logger import AuditLogger

# Matched against accent-stripped text so reviewers typing without diacritics are handled too.
EVIDENCE_KEYWORDS = (
    "kinh nghiem", "hoc van", "bang cap", "ky nang", "phong van", "chung chi", "du an", "nang luc",
    "chuyen mon", "vi tri", "cong viec", "yeu cau", "tham chieu", "thanh tich", "portfolio",
    "experience", "skill", "interview", "certif", "education", "degree", "project", "role",
)
# Matched against the original lowercase text: stripping accents would turn "năm" into "nam".
PROTECTED_ATTRIBUTE_PATTERNS = (
    r"giới tính", r"độ tuổi", r"tuổi tác", r"sắc tộc", r"dân tộc", r"chủng tộc", r"tôn giáo",
    r"mang thai", r"có thai", r"kết hôn", r"nam giới", r"nữ giới", r"phụ nữ", r"đàn ông",
    r"quá già", r"\bgender\b", r"\bage\b", r"\brace\b", r"\bethnicity\b", r"\bpregnan", r"\breligion\b",
)
MIN_UNIQUE_WORD_RATIO = 0.5


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower().replace("đ", "d"))
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _normalize_for_comparison(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", " ".join(_strip_accents(text).split()))


class DecisionGate:
    def __init__(self, settings: OversightSettings, audit_logger: AuditLogger):
        self.settings_ = settings
        self.audit_logger_ = audit_logger

    @property
    def authorized_hr_ids(self) -> tuple[str, ...]:
        return self.settings_.authorized_hr_ids

    def validate(self, request: DecisionRequest) -> list[str]:
        violations = []
        if request.hr_id not in self.settings_.authorized_hr_ids:
            violations.append(
                f"Mã HR '{request.hr_id}' không thuộc danh sách nhân sự được giao quyền giám sát (Điều 14, Điều 26(2))."
            )
        if not request.explanation_reviewed:
            violations.append("Cần xác nhận đã xem xét thẻ điểm giải trình trước khi ra quyết định.")
        violations += self._justification_violations(request)
        return violations

    def submit(self, request: DecisionRequest) -> AuditRecord:
        violations = self.validate(request)
        if violations:
            raise DecisionValidationError(violations)
        return self.audit_logger_.append(request)

    def _justification_violations(self, request: DecisionRequest) -> list[str]:
        text = request.justification.strip()
        words = text.split()
        violations = []

        if len(text) < self.settings_.min_justification_chars or len(words) < self.settings_.min_justification_words:
            violations.append(
                f"Lý do quá ngắn: cần tối thiểu {self.settings_.min_justification_chars} ký tự và "
                f"{self.settings_.min_justification_words} từ."
            )
            return violations

        normalized_words = _normalize_for_comparison(text).split()
        if len(set(normalized_words)) / max(len(normalized_words), 1) < MIN_UNIQUE_WORD_RATIO:
            violations.append("Lý do lặp từ, không mang nội dung đánh giá thực chất.")

        accentless = _strip_accents(text)
        if not any(keyword in accentless for keyword in EVIDENCE_KEYWORDS):
            violations.append(
                "Lý do cần nêu căn cứ năng lực cụ thể (ví dụ: kinh nghiệm, kỹ năng, kết quả phỏng vấn, "
                "chứng chỉ, yêu cầu vị trí)."
            )

        lowered = text.lower()
        if any(re.search(pattern, lowered) for pattern in PROTECTED_ATTRIBUTE_PATTERNS):
            violations.append("Lý do không được viện dẫn thuộc tính được bảo vệ (giới tính, tuổi, sắc tộc...).")

        recent = self.audit_logger_.recent_justifications(request.hr_id, self.settings_.duplicate_lookback)
        normalized_text = _normalize_for_comparison(text)
        if any(_normalize_for_comparison(previous) == normalized_text for previous in recent):
            violations.append("Lý do trùng lặp với quyết định gần đây (dấu hiệu duyệt hàng loạt hình thức).")
        return violations
