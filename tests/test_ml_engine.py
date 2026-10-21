import pytest

from techhire.domain import schema
from techhire.domain.exceptions import InvalidCandidateProfileError, SensitiveAttributeLeakError
from techhire.domain.models import CandidateProfile, Recommendation
from techhire.ml_engine.model_trainer import ModelVariant
from techhire.ml_engine.recommendation_engine import RecommendationEngine


def test_compliant_model_never_sees_sensitive_features(compliance_system):
    feature_names = compliance_system.compliant_model.encoder.feature_names
    assert feature_names == schema.COMPETENCE_FEATURES


def test_compliant_model_is_fairer_than_non_compliant(compliance_system):
    evaluations = compliance_system.evaluations
    non_compliant = evaluations[ModelVariant.NON_COMPLIANT].gender_fairness.disparate_impact_ratio
    compliant = evaluations[ModelVariant.COMPLIANT].gender_fairness.disparate_impact_ratio
    assert non_compliant < 0.8
    assert compliant > non_compliant


def test_compliant_model_is_counterfactually_fair(compliance_system):
    evaluation = compliance_system.evaluations[ModelVariant.COMPLIANT]
    assert evaluation.counterfactual_flip_rate == 0.0
    assert compliance_system.evaluations[ModelVariant.NON_COMPLIANT].counterfactual_flip_rate > 0.0


def test_engine_refuses_model_using_sensitive_attributes(compliance_system):
    with pytest.raises(SensitiveAttributeLeakError):
        RecommendationEngine(compliance_system.models[ModelVariant.NON_COMPLIANT], 0.6)


def test_recommendation_is_advisory_only(compliance_system):
    engine = RecommendationEngine(compliance_system.compliant_model, 0.6)
    assert engine.recommend(0.6) is Recommendation.RECOMMEND_INTERVIEW
    assert engine.recommend(0.1) is Recommendation.NEEDS_FURTHER_REVIEW
    assert {item.name for item in Recommendation} == {"RECOMMEND_INTERVIEW", "NEEDS_FURTHER_REVIEW"}


def test_model_version_is_deterministic(compliance_system):
    first = compliance_system.compliant_model.model_version
    assert first.startswith("compliant-rf-")
    assert first == compliance_system.evaluations[ModelVariant.COMPLIANT].model_version


@pytest.mark.parametrize(
    "overrides",
    [{"skill_score": 150}, {"experience_years": -1}, {"education_level": "Kindergarten"}, {"candidate_id": " "}],
)
def test_invalid_profiles_are_rejected(overrides):
    values = dict(
        candidate_id="NEW-1", experience_years=3, education_level="Master",
        skill_score=70, interview_score=70, certification_count=1,
    )
    values.update(overrides)
    with pytest.raises(InvalidCandidateProfileError):
        CandidateProfile(**values)
