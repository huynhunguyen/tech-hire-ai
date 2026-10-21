"""Central runtime configuration. Every tunable threshold of the system lives here."""

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("TECHHIRE_HOME", Path(__file__).resolve().parents[2]))


@dataclass(frozen=True)
class FairnessSettings:
    # Four-fifths rule used by EEOC and widely adopted as the Art. 10 audit benchmark.
    dir_threshold: float = 0.80
    # Intersectional reweighing over all protected attributes.
    reweighing_attributes: tuple[str, ...] = ("Gender", "Age", "Ethnicity")


@dataclass(frozen=True)
class ModelSettings:
    n_estimators: int = 200
    max_depth: int = 8
    min_samples_leaf: int = 5
    test_size: float = 0.30
    random_state: int = 42


@dataclass(frozen=True)
class RecommendationSettings:
    interview_threshold: float = 0.60


@dataclass(frozen=True)
class OversightSettings:
    authorized_hr_ids: tuple[str, ...] = ("HR-001", "HR-002", "HR-003")
    min_justification_chars: int = 30
    min_justification_words: int = 6
    duplicate_lookback: int = 5


@dataclass(frozen=True)
class AppSettings:
    # None means the built-in synthetic dataset; a CSV is used only when explicitly configured.
    dataset_path: Path | None
    audit_log_path: Path
    synthetic_sample_size: int = 6000
    fairness: FairnessSettings = field(default_factory=FairnessSettings)
    model: ModelSettings = field(default_factory=ModelSettings)
    recommendation: RecommendationSettings = field(default_factory=RecommendationSettings)
    oversight: OversightSettings = field(default_factory=OversightSettings)


def load_settings() -> AppSettings:
    configured_dataset = os.environ.get("TECHHIRE_DATASET_PATH")
    audit_log_path = Path(
        os.environ.get("TECHHIRE_AUDIT_LOG_PATH", PROJECT_ROOT / "data" / "audit" / "audit_log.jsonl")
    )
    return AppSettings(
        dataset_path=Path(configured_dataset) if configured_dataset else None,
        audit_log_path=audit_log_path,
    )
