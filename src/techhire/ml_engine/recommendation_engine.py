"""Produces advisory recommendations. It never issues an accept or reject decision (Art. 14)."""

import pandas as pd

from techhire.domain.exceptions import SensitiveAttributeLeakError
from techhire.domain.models import CandidateProfile, Recommendation, ScreeningResult
from techhire.ml_engine.model_trainer import TrainedModel


class RecommendationEngine:
    def __init__(self, model: TrainedModel, interview_threshold: float):
        if model.variant.uses_sensitive_attributes:
            raise SensitiveAttributeLeakError("Only a model blind to sensitive attributes may serve recommendations.")
        self.model_ = model
        self.interview_threshold_ = interview_threshold

    @property
    def model(self) -> TrainedModel:
        return self.model_

    def recommend(self, matching_score: float) -> Recommendation:
        if matching_score >= self.interview_threshold_:
            return Recommendation.RECOMMEND_INTERVIEW
        return Recommendation.NEEDS_FURTHER_REVIEW

    def screen(self, profile: CandidateProfile) -> ScreeningResult:
        candidate_frame = pd.DataFrame([profile.to_record()])
        matching_score = float(self.model_.predict_proba(candidate_frame)[0])
        return ScreeningResult(
            candidate_id=profile.candidate_id,
            matching_score=matching_score,
            recommendation=self.recommend(matching_score),
            model_version=self.model_.model_version,
        )
