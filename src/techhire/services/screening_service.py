"""Candidate assessment use case: score, explain and probe a single candidate."""

import time
from dataclasses import dataclass

import pandas as pd

from techhire.domain.models import CandidateProfile, Scorecard, ScreeningResult
from techhire.explainability.explanation_narrator import build_candidate_explanation
from techhire.explainability.shap_explainer import LocalExplainer
from techhire.ml_engine.counterfactual import CounterfactualResult, gender_counterfactual
from techhire.ml_engine.model_trainer import TrainedModel
from techhire.ml_engine.recommendation_engine import RecommendationEngine


@dataclass(frozen=True)
class CandidateAssessment:
    profile: CandidateProfile
    screening: ScreeningResult
    scorecard: Scorecard
    explanation: str
    latency_ms: float


@dataclass(frozen=True)
class FairnessProbe:
    """Contrasts the compliant model with the non-compliant reference for one real candidate."""

    compliant_counterfactual: CounterfactualResult | None
    reference_counterfactual: CounterfactualResult | None
    reference_scorecard: Scorecard


class ScreeningService:
    def __init__(
        self,
        engine: RecommendationEngine,
        explainer: LocalExplainer,
        reference_model: TrainedModel,
        reference_explainer: LocalExplainer,
    ):
        self.engine_ = engine
        self.explainer_ = explainer
        self.reference_model_ = reference_model
        self.reference_explainer_ = reference_explainer

    def assess(self, profile: CandidateProfile) -> CandidateAssessment:
        started = time.perf_counter()
        screening = self.engine_.screen(profile)
        scorecard = self.explainer_.explain(pd.DataFrame([profile.to_record()]))
        explanation = build_candidate_explanation(screening, scorecard)
        latency_ms = (time.perf_counter() - started) * 1000
        return CandidateAssessment(profile, screening, scorecard, explanation, latency_ms)

    def probe_fairness(self, candidate_row: pd.DataFrame) -> FairnessProbe:
        return FairnessProbe(
            compliant_counterfactual=gender_counterfactual(self.engine_.model, candidate_row),
            reference_counterfactual=gender_counterfactual(self.reference_model_, candidate_row),
            reference_scorecard=self.reference_explainer_.explain(candidate_row),
        )
