"""Side-by-side evaluation of model variants on accuracy and fairness."""

from dataclasses import dataclass

import pandas as pd
from sklearn.metrics import accuracy_score, roc_auc_score

from techhire.domain import schema
from techhire.governance.bias_auditor import (
    AGE_PROTECTED_BAND,
    AGE_REFERENCE_BAND,
    BiasAuditor,
    FairnessReport,
    to_age_band,
)
from techhire.ml_engine.counterfactual import counterfactual_flip_rate
from techhire.ml_engine.model_trainer import ModelVariant, TrainedModel


@dataclass(frozen=True)
class ModelEvaluation:
    variant: ModelVariant
    model_version: str
    accuracy: float
    roc_auc: float
    selection_rate: float
    gender_fairness: FairnessReport
    ethnicity_fairness: FairnessReport
    age_fairness: FairnessReport
    counterfactual_flip_rate: float


class ModelComparator:
    def __init__(self, auditor: BiasAuditor, interview_threshold: float):
        self.auditor_ = auditor
        self.interview_threshold_ = interview_threshold

    def evaluate(self, model: TrainedModel, test_frame: pd.DataFrame) -> ModelEvaluation:
        """Accuracy is measured against historical labels, which themselves carry bias.

        A drop in accuracy for the compliant model is therefore expected: it partly reflects the
        model refusing to reproduce the biased past rather than a loss of predictive quality.
        """
        scores = pd.Series(model.predict_proba(test_frame), index=test_frame.index)
        predicted = (scores >= self.interview_threshold_).astype(int)
        labels = test_frame[schema.HIRING_DECISION].astype(int)

        return ModelEvaluation(
            variant=model.variant,
            model_version=model.model_version,
            accuracy=float(accuracy_score(labels, predicted)),
            roc_auc=float(roc_auc_score(labels, scores)),
            selection_rate=float(predicted.mean()),
            gender_fairness=self.auditor_.audit(
                test_frame[schema.GENDER], predicted, schema.GENDER, schema.GENDER_FEMALE, schema.GENDER_MALE
            ),
            ethnicity_fairness=self.auditor_.audit(test_frame[schema.ETHNICITY], predicted, schema.ETHNICITY),
            age_fairness=self.auditor_.audit(
                to_age_band(test_frame[schema.AGE]), predicted, schema.AGE, AGE_PROTECTED_BAND, AGE_REFERENCE_BAND
            ),
            counterfactual_flip_rate=counterfactual_flip_rate(model, test_frame, self.interview_threshold_),
        )
