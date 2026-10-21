"""Plain-language explanation HR can hand to a candidate (GDPR Art. 13-15 and Art. 22(3))."""

from techhire.domain.models import FeatureContribution, Scorecard, ScreeningResult

MAX_FACTORS_PER_DIRECTION = 2
# Contributions below half a percentage point are noise for a candidate-facing text.
MIN_REPORTABLE_CONTRIBUTION = 0.005


def _describe(factors: tuple[FeatureContribution, ...]) -> str:
    selected = [item for item in factors if abs(item.contribution) >= MIN_REPORTABLE_CONTRIBUTION]
    selected = selected[:MAX_FACTORS_PER_DIRECTION]
    return ", ".join(f"{item.label.lower()} ({item.display_value})" for item in selected)


def build_candidate_explanation(screening: ScreeningResult, scorecard: Scorecard) -> str:
    sentences = [
        f"Hồ sơ {screening.candidate_id} được hệ thống hỗ trợ đánh giá ở mức phù hợp "
        f"{screening.matching_score_percent}% với kết quả tham mưu \"{screening.recommendation.value}\"."
    ]
    strengths = _describe(scorecard.positive_factors)
    if strengths:
        sentences.append(f"Các yếu tố nâng mức phù hợp nhiều nhất: {strengths}.")
    weaknesses = _describe(scorecard.negative_factors)
    if weaknesses:
        sentences.append(f"Các yếu tố làm giảm mức phù hợp: {weaknesses}.")
    sentences.append(
        "Đánh giá chỉ dựa trên năng lực chuyên môn; giới tính, độ tuổi và sắc tộc không được sử dụng. "
        "Kết quả này chỉ mang tính tham mưu, quyết định cuối cùng do chuyên viên nhân sự đưa ra. "
        "Ứng viên có quyền yêu cầu con người xem xét lại, trình bày quan điểm và phản đối quyết định."
    )
    return " ".join(sentences)
