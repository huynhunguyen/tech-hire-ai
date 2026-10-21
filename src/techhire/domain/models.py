"""Value objects shared across layers."""

from dataclasses import asdict, dataclass
from enum import Enum

from techhire.domain import schema
from techhire.domain.exceptions import InvalidCandidateProfileError


class Recommendation(str, Enum):
    """Advisory output only: the system never rejects or hires a candidate by itself."""

    RECOMMEND_INTERVIEW = "Khuyến nghị Phỏng vấn"
    NEEDS_FURTHER_REVIEW = "Cần xem xét thêm"


class HrDecision(str, Enum):
    INVITE_TO_INTERVIEW = "Mời phỏng vấn"
    DO_NOT_PROCEED = "Không tiếp tục"


def is_override(recommendation: Recommendation, decision: HrDecision) -> bool:
    ai_suggests_interview = recommendation is Recommendation.RECOMMEND_INTERVIEW
    hr_invites = decision is HrDecision.INVITE_TO_INTERVIEW
    return ai_suggests_interview != hr_invites


@dataclass(frozen=True)
class CandidateProfile:
    """Competence-only view of a candidate. Sensitive attributes are not part of it by design."""

    candidate_id: str
    experience_years: float
    education_level: str
    skill_score: float
    interview_score: float
    certification_count: int

    def __post_init__(self) -> None:
        violations = self._collect_violations()
        if violations:
            raise InvalidCandidateProfileError(violations)

    def _collect_violations(self) -> list[str]:
        violations = []
        if not str(self.candidate_id).strip():
            violations.append("Mã ứng viên không được để trống.")
        if self.education_level not in schema.EDUCATION_LEVELS:
            violations.append(f"Trình độ học vấn không hợp lệ: {self.education_level!r}.")
        numeric_values = {
            schema.EXPERIENCE_YEARS: self.experience_years,
            schema.SKILL_SCORE: self.skill_score,
            schema.INTERVIEW_SCORE: self.interview_score,
            schema.CERTIFICATION_COUNT: self.certification_count,
        }
        for attribute, value in numeric_values.items():
            valid_range = schema.NUMERIC_RANGES[attribute]
            if not valid_range.contains(value):
                violations.append(
                    f"{schema.label_of(attribute)} = {value} nằm ngoài miền hợp lệ "
                    f"[{valid_range.min_value}, {valid_range.max_value}]."
                )
        return violations

    def to_record(self) -> dict[str, object]:
        return {
            schema.CANDIDATE_ID: self.candidate_id,
            schema.EXPERIENCE_YEARS: self.experience_years,
            schema.EDUCATION_LEVEL: self.education_level,
            schema.SKILL_SCORE: self.skill_score,
            schema.INTERVIEW_SCORE: self.interview_score,
            schema.CERTIFICATION_COUNT: self.certification_count,
        }

    @classmethod
    def from_record(cls, record: dict) -> "CandidateProfile":
        return cls(
            candidate_id=str(record[schema.CANDIDATE_ID]),
            experience_years=float(record[schema.EXPERIENCE_YEARS]),
            education_level=str(record[schema.EDUCATION_LEVEL]),
            skill_score=float(record[schema.SKILL_SCORE]),
            interview_score=float(record[schema.INTERVIEW_SCORE]),
            certification_count=int(record[schema.CERTIFICATION_COUNT]),
        )


@dataclass(frozen=True)
class ScreeningResult:
    candidate_id: str
    matching_score: float
    recommendation: Recommendation
    model_version: str

    @property
    def matching_score_percent(self) -> float:
        return round(self.matching_score * 100, 1)


@dataclass(frozen=True)
class FeatureContribution:
    attribute: str
    display_value: str
    contribution: float

    @property
    def label(self) -> str:
        return schema.label_of(self.attribute)

    @property
    def contribution_points(self) -> float:
        return round(self.contribution * 100, 1)


@dataclass(frozen=True)
class Scorecard:
    """Local explanation of one prediction. It never exposes global weights (trade secret)."""

    candidate_id: str
    base_score: float
    matching_score: float
    contributions: tuple[FeatureContribution, ...]

    @property
    def positive_factors(self) -> tuple[FeatureContribution, ...]:
        return tuple(item for item in self.contributions if item.contribution > 0)

    @property
    def negative_factors(self) -> tuple[FeatureContribution, ...]:
        return tuple(item for item in self.contributions if item.contribution < 0)

    def contribution_of(self, attribute: str) -> float:
        return sum(item.contribution for item in self.contributions if item.attribute == attribute)


@dataclass(frozen=True)
class DecisionRequest:
    hr_id: str
    candidate_id: str
    ai_score: float
    ai_recommendation: Recommendation
    hr_decision: HrDecision
    justification: str
    explanation_reviewed: bool
    model_version: str

    @property
    def is_override(self) -> bool:
        return is_override(self.ai_recommendation, self.hr_decision)


@dataclass(frozen=True)
class AuditRecord:
    event_id: str
    timestamp: str
    hr_id: str
    candidate_id: str
    ai_score: float
    ai_recommendation: str
    hr_decision: str
    is_override: bool
    justification: str
    model_version: str
    previous_hash: str
    record_hash: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
