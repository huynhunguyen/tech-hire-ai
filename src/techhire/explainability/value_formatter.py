"""Human-readable rendering of attribute values for scorecards and explanations."""

from techhire.domain import schema


def format_attribute_value(attribute: str, value: object) -> str:
    if attribute == schema.EXPERIENCE_YEARS:
        return f"{float(value):g} năm"
    if attribute in (schema.SKILL_SCORE, schema.INTERVIEW_SCORE):
        return f"{float(value):g}/100"
    if attribute == schema.CERTIFICATION_COUNT:
        return f"{int(value)} chứng chỉ"
    if attribute == schema.AGE:
        return f"{int(value)} tuổi"
    return str(value)
