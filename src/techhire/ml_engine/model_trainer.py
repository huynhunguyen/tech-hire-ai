"""Trains the Random Forest variants used for the before/after compliance comparison."""

import hashlib
from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from techhire.config import ModelSettings
from techhire.domain import schema
from techhire.governance.sensitive_attribute_filter import assert_blind_to_sensitive_attributes
from techhire.ml_engine.feature_encoder import FeatureEncoder


class ModelVariant(str, Enum):
    NON_COMPLIANT = "non_compliant"
    UNAWARE = "unaware"
    COMPLIANT = "compliant"

    @property
    def label(self) -> str:
        return VARIANT_LABELS[self]

    @property
    def uses_sensitive_attributes(self) -> bool:
        return self is ModelVariant.NON_COMPLIANT


VARIANT_LABELS = {
    ModelVariant.NON_COMPLIANT: "Mô hình chưa tuân thủ (dữ liệu thô)",
    ModelVariant.UNAWARE: "Chỉ ẩn thuộc tính nhạy cảm",
    ModelVariant.COMPLIANT: "Mô hình đã tuân thủ (ẩn + tái cân bằng)",
}


@dataclass(frozen=True)
class TrainedModel:
    variant: ModelVariant
    estimator: RandomForestClassifier
    encoder: FeatureEncoder
    model_version: str

    @property
    def positive_class_index(self) -> int:
        return list(self.estimator.classes_).index(1)

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        features = self.encoder.transform(frame)
        return self.estimator.predict_proba(features)[:, self.positive_class_index]


class ModelTrainer:
    def __init__(self, settings: ModelSettings):
        self.settings_ = settings

    def train(
        self, variant: ModelVariant, train_frame: pd.DataFrame, sample_weight: pd.Series | None = None
    ) -> TrainedModel:
        encoder = FeatureEncoder(include_sensitive=variant.uses_sensitive_attributes).fit(train_frame)
        if not variant.uses_sensitive_attributes:
            assert_blind_to_sensitive_attributes(encoder.feature_names)

        features = encoder.transform(train_frame)
        labels = train_frame[schema.HIRING_DECISION].astype(int)
        weights = None if sample_weight is None else sample_weight.loc[train_frame.index].to_numpy()

        estimator = RandomForestClassifier(
            n_estimators=self.settings_.n_estimators,
            max_depth=self.settings_.max_depth,
            min_samples_leaf=self.settings_.min_samples_leaf,
            random_state=self.settings_.random_state,
            # Thread start-up costs more than it saves on a few thousand rows and single-row scoring.
            n_jobs=1,
        )
        estimator.fit(features, labels, sample_weight=weights)
        return TrainedModel(
            variant=variant,
            estimator=estimator,
            encoder=encoder,
            model_version=self._build_version(variant, features, labels, weights),
        )

    def _build_version(
        self, variant: ModelVariant, features: pd.DataFrame, labels: pd.Series, weights: np.ndarray | None
    ) -> str:
        # Content-addressed version: identical data and hyper-parameters give the same id,
        # which lets every audit record be traced back to the exact training run (Art. 12).
        digest = hashlib.sha256()
        digest.update(pd.util.hash_pandas_object(features, index=False).to_numpy().tobytes())
        digest.update(labels.to_numpy().tobytes())
        if weights is not None:
            digest.update(np.round(weights, 8).tobytes())
        digest.update(repr(self.settings_).encode())
        return f"{variant.value}-rf-{digest.hexdigest()[:10]}"
