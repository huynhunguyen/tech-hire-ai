import pandas as pd
import pytest

from techhire.domain import schema
from techhire.domain.exceptions import SensitiveAttributeLeakError
from techhire.governance.bias_auditor import BiasAuditor
from techhire.governance.reweighing import compute_reweighing_weights
from techhire.governance.sensitive_attribute_filter import (
    assert_blind_to_sensitive_attributes,
    drop_sensitive_attributes,
)


def test_disparate_impact_ratio_matches_hand_computation():
    groups = pd.Series(["Male"] * 10 + ["Female"] * 10)
    outcomes = pd.Series([1] * 6 + [0] * 4 + [1] * 3 + [0] * 7)
    report = BiasAuditor(0.8).audit(groups, outcomes, "Gender", "Female", "Male")
    assert report.disparate_impact_ratio == pytest.approx(0.3 / 0.6)
    assert report.statistical_parity_difference == pytest.approx(-0.3)
    assert not report.passes


def test_multi_group_audit_compares_worst_against_best_group():
    groups = pd.Series(["A"] * 4 + ["B"] * 4 + ["C"] * 4)
    outcomes = pd.Series([1, 1, 1, 1, 1, 1, 0, 0, 1, 0, 0, 0])
    report = BiasAuditor(0.8).audit(groups, outcomes, "Ethnicity")
    assert (report.protected_group, report.reference_group) == ("C", "A")
    assert report.disparate_impact_ratio == pytest.approx(0.25)


def test_synthetic_history_is_biased_against_women(synthetic_frame):
    report = BiasAuditor(0.8).audit(
        synthetic_frame[schema.GENDER], synthetic_frame[schema.HIRING_DECISION], schema.GENDER, "Female", "Male"
    )
    assert report.disparate_impact_ratio < 0.8


def test_reweighing_makes_labels_independent_of_group(synthetic_frame):
    groups = synthetic_frame[[schema.GENDER, schema.ETHNICITY]]
    labels = synthetic_frame[schema.HIRING_DECISION]
    result = compute_reweighing_weights(groups, labels)

    weighted = BiasAuditor(0.8).audit(
        synthetic_frame[schema.GENDER], labels, schema.GENDER, "Female", "Male", sample_weight=result.sample_weights
    )
    assert weighted.disparate_impact_ratio == pytest.approx(1.0)
    assert result.sample_weights.sum() == pytest.approx(len(labels))


def test_sensitive_attributes_are_removed(synthetic_frame):
    blind = drop_sensitive_attributes(synthetic_frame)
    assert not set(schema.SENSITIVE_ATTRIBUTES) & set(blind.columns)


@pytest.mark.parametrize("feature", ["Gender=Male", "Age", "Ethnicity=Asian"])
def test_blind_guard_rejects_leaked_features(feature):
    with pytest.raises(SensitiveAttributeLeakError):
        assert_blind_to_sensitive_attributes(["Skill_Score", feature])


def test_blind_guard_accepts_competence_features():
    assert_blind_to_sensitive_attributes(schema.COMPETENCE_FEATURES)
