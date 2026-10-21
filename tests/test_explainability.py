import pandas as pd
import pytest

from techhire.domain import schema
from techhire.domain.models import CandidateProfile

LATENCY_BUDGET_MS = 2000


@pytest.fixture
def pool_candidate(compliance_system) -> pd.DataFrame:
    return compliance_system.candidate_pool.iloc[[0]]


def test_scorecard_is_additive(compliance_system, pool_candidate):
    profile = CandidateProfile.from_record(pool_candidate.iloc[0].to_dict())
    scorecard = compliance_system.screening_service.assess(profile).scorecard
    reconstructed = scorecard.base_score + sum(item.contribution for item in scorecard.contributions)
    assert reconstructed == pytest.approx(scorecard.matching_score, abs=1e-6)


def test_scorecard_only_contains_competence_attributes(compliance_system, pool_candidate):
    profile = CandidateProfile.from_record(pool_candidate.iloc[0].to_dict())
    scorecard = compliance_system.screening_service.assess(profile).scorecard
    assert {item.attribute for item in scorecard.contributions} == set(schema.COMPETENCE_FEATURES)


def test_assessment_meets_latency_budget(compliance_system, pool_candidate):
    profile = CandidateProfile.from_record(pool_candidate.iloc[0].to_dict())
    compliance_system.screening_service.assess(profile)
    assert compliance_system.screening_service.assess(profile).latency_ms < LATENCY_BUDGET_MS


def test_explanation_mentions_human_review_right(compliance_system, pool_candidate):
    profile = CandidateProfile.from_record(pool_candidate.iloc[0].to_dict())
    explanation = compliance_system.screening_service.assess(profile).explanation
    assert profile.candidate_id in explanation
    assert "con người xem xét lại" in explanation


def test_fairness_probe_shows_gender_effect_only_in_reference_model(compliance_system, pool_candidate):
    probe = compliance_system.screening_service.probe_fairness(pool_candidate)
    assert probe.compliant_counterfactual.score_delta == pytest.approx(0.0)
    assert schema.GENDER in {item.attribute for item in probe.reference_scorecard.contributions}
