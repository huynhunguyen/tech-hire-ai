"""Canonical dataset schema and attribute grouping (EU AI Act Art. 10)."""

from dataclasses import dataclass

CANDIDATE_ID = "Candidate_ID"

GENDER = "Gender"
AGE = "Age"
ETHNICITY = "Ethnicity"

EXPERIENCE_YEARS = "Experience_Years"
EDUCATION_LEVEL = "Education_Level"
SKILL_SCORE = "Skill_Score"
INTERVIEW_SCORE = "Interview_Score"
CERTIFICATION_COUNT = "Certification_Count"

HIRING_DECISION = "Hiring_Decision"

SENSITIVE_ATTRIBUTES: tuple[str, ...] = (GENDER, AGE, ETHNICITY)
COMPETENCE_FEATURES: tuple[str, ...] = (
    EXPERIENCE_YEARS,
    EDUCATION_LEVEL,
    SKILL_SCORE,
    INTERVIEW_SCORE,
    CERTIFICATION_COUNT,
)
# Allow-list: any other column (e.g. biometric or video-derived data) is discarded on load.
ALLOWED_COLUMNS: tuple[str, ...] = (CANDIDATE_ID, *SENSITIVE_ATTRIBUTES, *COMPETENCE_FEATURES, HIRING_DECISION)
REQUIRED_COLUMNS: tuple[str, ...] = (*SENSITIVE_ATTRIBUTES, *COMPETENCE_FEATURES, HIRING_DECISION)

GENDER_MALE = "Male"
GENDER_FEMALE = "Female"
GENDER_OTHER = "Other"

# Order matters: the index is used as the ordinal encoding.
EDUCATION_LEVELS: tuple[str, ...] = ("High School", "Bachelor", "Master", "PhD")


@dataclass(frozen=True)
class NumericRange:
    min_value: float
    max_value: float

    def contains(self, value: float) -> bool:
        return self.min_value <= value <= self.max_value


NUMERIC_RANGES: dict[str, NumericRange] = {
    AGE: NumericRange(18, 75),
    EXPERIENCE_YEARS: NumericRange(0, 45),
    SKILL_SCORE: NumericRange(0, 100),
    INTERVIEW_SCORE: NumericRange(0, 100),
    CERTIFICATION_COUNT: NumericRange(0, 30),
}

ATTRIBUTE_LABELS: dict[str, str] = {
    CANDIDATE_ID: "Mã ứng viên",
    GENDER: "Giới tính",
    AGE: "Độ tuổi",
    ETHNICITY: "Sắc tộc",
    EXPERIENCE_YEARS: "Số năm kinh nghiệm",
    EDUCATION_LEVEL: "Trình độ học vấn",
    SKILL_SCORE: "Điểm kỹ năng",
    INTERVIEW_SCORE: "Điểm phỏng vấn chuyên môn",
    CERTIFICATION_COUNT: "Số lượng chứng chỉ",
    HIRING_DECISION: "Quyết định tuyển dụng (lịch sử)",
}


def label_of(attribute: str) -> str:
    return ATTRIBUTE_LABELS.get(attribute, attribute)
