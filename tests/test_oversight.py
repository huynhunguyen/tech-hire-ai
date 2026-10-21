import json

import pytest

from techhire.domain.exceptions import DecisionValidationError
from techhire.domain.models import HrDecision, Recommendation


def test_valid_decision_is_logged(decision_gate, audit_logger, make_request):
    record = decision_gate.submit(make_request())
    assert audit_logger.read_records() == [record]
    assert record.is_override is False


def test_override_is_detected(decision_gate, make_request):
    record = decision_gate.submit(make_request(hr_decision=HrDecision.DO_NOT_PROCEED))
    assert record.is_override is True
    record = decision_gate.submit(
        make_request(
            ai_recommendation=Recommendation.NEEDS_FURTHER_REVIEW,
            hr_decision=HrDecision.INVITE_TO_INTERVIEW,
            justification="Dự án mã nguồn mở của ứng viên chứng minh kỹ năng thiết kế hệ thống vượt yêu cầu.",
        )
    )
    assert record.is_override is True


@pytest.mark.parametrize(
    "overrides, expected_fragment",
    [
        ({"hr_id": "HR-999"}, "giao quyền"),
        ({"explanation_reviewed": False}, "thẻ điểm"),
        ({"justification": "Đồng ý"}, "quá ngắn"),
        ({"justification": "ok ok ok ok ok ok ok ok ok ok ok ok"}, "lặp từ"),
        ({"justification": "Tôi đồng ý hoàn toàn với đề xuất mà hệ thống AI đưa ra."}, "căn cứ năng lực"),
        ({"justification": "Kinh nghiệm tốt nhưng ứng viên là phụ nữ nên không phù hợp lắm."}, "thuộc tính được bảo vệ"),
    ],
)
def test_rubber_stamping_and_invalid_decisions_are_blocked(decision_gate, audit_logger, make_request, overrides, expected_fragment):
    with pytest.raises(DecisionValidationError) as error:
        decision_gate.submit(make_request(**overrides))
    assert any(expected_fragment in violation for violation in error.value.violations)
    assert audit_logger.read_records() == []


def test_accentless_evidence_keywords_are_accepted(decision_gate, make_request):
    decision_gate.submit(make_request(justification="Ung vien co ky nang Python tot va kinh nghiem du an thuc te."))


def test_copy_pasted_justification_is_rejected(decision_gate, make_request):
    decision_gate.submit(make_request(candidate_id="C-1"))
    with pytest.raises(DecisionValidationError, match="trùng lặp"):
        decision_gate.submit(make_request(candidate_id="C-2"))


def test_hash_chain_links_records(decision_gate, audit_logger, make_request):
    first = decision_gate.submit(make_request(candidate_id="C-1"))
    second = decision_gate.submit(
        make_request(candidate_id="C-2", justification="Chứng chỉ AWS và kinh nghiệm vận hành hệ thống lớn rất phù hợp.")
    )
    assert second.previous_hash == first.record_hash
    assert audit_logger.verify_integrity().is_valid


def _rewrite_line(log_path, index, mutate):
    lines = log_path.read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[index])
    mutate(record)
    lines[index] = json.dumps(record, ensure_ascii=False)
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_edited_record_is_detected(decision_gate, audit_logger, make_request):
    decision_gate.submit(make_request())
    _rewrite_line(audit_logger.log_path, 0, lambda record: record.update(hr_decision="Không tiếp tục"))
    report = audit_logger.verify_integrity()
    assert not report.is_valid
    assert report.broken_at_line == 1


def test_deleted_record_is_detected(decision_gate, audit_logger, make_request):
    for index, text in enumerate(
        [
            "Kinh nghiệm backend sáu năm phù hợp yêu cầu vị trí kỹ sư cấp cao.",
            "Kỹ năng phân tích dữ liệu tốt, điểm phỏng vấn chuyên môn cao hơn mặt bằng.",
            "Chứng chỉ bảo mật và dự án thực tế cho thấy năng lực vượt yêu cầu tối thiểu.",
        ]
    ):
        decision_gate.submit(make_request(candidate_id=f"C-{index}", justification=text))
    lines = audit_logger.log_path.read_text(encoding="utf-8").splitlines()
    audit_logger.log_path.write_text("\n".join([lines[0], lines[2]]) + "\n", encoding="utf-8")
    assert not audit_logger.verify_integrity().is_valid


def test_log_contains_no_sensitive_attributes(decision_gate, audit_logger, make_request):
    decision_gate.submit(make_request())
    raw = audit_logger.log_path.read_text(encoding="utf-8")
    for field in ("Gender", "Age", "Ethnicity", "gender", "ethnicity"):
        assert field not in raw
