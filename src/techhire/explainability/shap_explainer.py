"""Per-candidate SHAP explanations expressed in probability points."""

from collections import defaultdict

import numpy as np
import pandas as pd
import shap

from techhire.domain import schema
from techhire.domain.models import FeatureContribution, Scorecard
from techhire.explainability.value_formatter import format_attribute_value
from techhire.ml_engine.feature_encoder import source_attribute_of
from techhire.ml_engine.model_trainer import TrainedModel


class LocalExplainer:
    """Explains a single prediction only.

    Global feature importances and model internals are deliberately not exposed, so HR can
    justify an individual outcome without disclosing the model as a trade secret.
    """

    def __init__(self, model: TrainedModel):
        self.model_ = model
        # For a RandomForestClassifier the raw TreeExplainer output is already in probability space,
        # so base value plus contributions adds up to the predicted matching score.
        self.explainer_ = shap.TreeExplainer(model.estimator)

    def explain(self, candidate_frame: pd.DataFrame) -> Scorecard:
        if len(candidate_frame) != 1:
            raise ValueError("LocalExplainer explains exactly one candidate at a time.")

        encoded = self.model_.encoder.transform(candidate_frame)
        contributions = self._positive_class_contributions(self.explainer_.shap_values(encoded))

        # One-hot columns (e.g. Gender=Male, Gender=Female) are folded back into their source
        # attribute; SHAP values are additive so the sum is still a valid attribution.
        per_attribute: dict[str, float] = defaultdict(float)
        for feature_name, value in zip(encoded.columns, contributions):
            per_attribute[source_attribute_of(feature_name)] += float(value)

        row = candidate_frame.iloc[0]
        items = sorted(
            (
                FeatureContribution(
                    attribute=attribute,
                    display_value=format_attribute_value(attribute, row[attribute]),
                    contribution=value,
                )
                for attribute, value in per_attribute.items()
            ),
            key=lambda item: abs(item.contribution),
            reverse=True,
        )
        return Scorecard(
            candidate_id=str(row.get(schema.CANDIDATE_ID, "")),
            base_score=self._positive_class_base_value(),
            matching_score=float(self.model_.predict_proba(candidate_frame)[0]),
            contributions=tuple(items),
        )

    def _positive_class_contributions(self, shap_values: object) -> np.ndarray:
        # Older SHAP versions return one array per class; newer ones return (rows, features, classes).
        if isinstance(shap_values, list):
            return np.asarray(shap_values[self.model_.positive_class_index])[0]
        values = np.asarray(shap_values)
        if values.ndim == 3:
            return values[0, :, self.model_.positive_class_index]
        return values[0]

    def _positive_class_base_value(self) -> float:
        expected = np.atleast_1d(self.explainer_.expected_value)
        if expected.size > 1:
            return float(expected[self.model_.positive_class_index])
        return float(expected[0])
