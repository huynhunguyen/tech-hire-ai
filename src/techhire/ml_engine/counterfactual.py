"""Counterfactual fairness probe: does the score change if only the gender changes?"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from techhire.domain import schema
from techhire.ml_engine.model_trainer import TrainedModel

GENDER_SWAP = {schema.GENDER_MALE: schema.GENDER_FEMALE, schema.GENDER_FEMALE: schema.GENDER_MALE}


@dataclass(frozen=True)
class CounterfactualResult:
    original_gender: str
    original_score: float
    counterfactual_gender: str
    counterfactual_score: float

    @property
    def score_delta(self) -> float:
        return self.counterfactual_score - self.original_score


def swap_binary_gender(frame: pd.DataFrame) -> pd.DataFrame:
    swapped = frame.copy()
    swapped[schema.GENDER] = frame[schema.GENDER].map(lambda value: GENDER_SWAP.get(value, value))
    return swapped


def gender_counterfactual(model: TrainedModel, candidate_row: pd.DataFrame) -> CounterfactualResult | None:
    original_gender = str(candidate_row[schema.GENDER].iloc[0])
    if original_gender not in GENDER_SWAP:
        return None
    original_score = float(model.predict_proba(candidate_row)[0])
    counterfactual_score = float(model.predict_proba(swap_binary_gender(candidate_row))[0])
    return CounterfactualResult(
        original_gender=original_gender,
        original_score=original_score,
        counterfactual_gender=GENDER_SWAP[original_gender],
        counterfactual_score=counterfactual_score,
    )


def counterfactual_flip_rate(model: TrainedModel, frame: pd.DataFrame, threshold: float) -> float:
    """Share of binary-gender candidates whose recommendation flips when only gender is swapped."""
    binary = frame[frame[schema.GENDER].isin(GENDER_SWAP)]
    if binary.empty:
        return 0.0
    original = model.predict_proba(binary) >= threshold
    swapped = model.predict_proba(swap_binary_gender(binary)) >= threshold
    return float(np.mean(original != swapped))
