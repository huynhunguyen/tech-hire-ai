"""Group fairness auditing based on the Disparate Impact Ratio (four-fifths rule)."""

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

# Two bands around 40, the age from which hiring discrimination against older workers is typically studied.
AGE_REFERENCE_BAND = "Dưới 40"
AGE_PROTECTED_BAND = "40 trở lên"
AGE_BANDS: tuple[tuple[str, int, int], ...] = ((AGE_REFERENCE_BAND, 0, 39), (AGE_PROTECTED_BAND, 40, 200))


@dataclass(frozen=True)
class GroupSelectionRate:
    group: str
    count: int
    selection_rate: float


@dataclass(frozen=True)
class FairnessReport:
    attribute: str
    protected_group: str
    reference_group: str
    group_rates: tuple[GroupSelectionRate, ...]
    disparate_impact_ratio: float
    statistical_parity_difference: float
    threshold: float

    @property
    def passes(self) -> bool:
        return self.disparate_impact_ratio >= self.threshold

    def rate_of(self, group: str) -> float:
        return next(item.selection_rate for item in self.group_rates if item.group == group)


def to_age_band(ages: pd.Series) -> pd.Series:
    labels = pd.Series("Không xác định", index=ages.index)
    for label, lower, upper in AGE_BANDS:
        labels[ages.between(lower, upper)] = label
    return labels


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 1.0 if numerator == 0 else math.inf
    return numerator / denominator


class BiasAuditor:
    def __init__(self, threshold: float = 0.80):
        self.threshold_ = threshold

    def audit(
        self,
        groups: pd.Series,
        outcomes: pd.Series,
        attribute: str,
        protected_group: str | None = None,
        reference_group: str | None = None,
        sample_weight: pd.Series | None = None,
    ) -> FairnessReport:
        """Compares positive-outcome rates across groups.

        With explicit groups the ratio is protected / reference. Otherwise the worst-off group
        is compared against the best-off group, which is the strictest multi-group reading.
        """
        weights = pd.Series(1.0, index=outcomes.index) if sample_weight is None else sample_weight
        frame = pd.DataFrame({"group": groups.astype(str), "outcome": outcomes.astype(float), "weight": weights})

        group_rates = []
        for group, members in frame.groupby("group", sort=True):
            rate = float(np.average(members["outcome"], weights=members["weight"]))
            group_rates.append(GroupSelectionRate(group=str(group), count=len(members), selection_rate=rate))
        rates = {item.group: item.selection_rate for item in group_rates}

        if protected_group is None or reference_group is None:
            protected_group = min(rates, key=rates.get)
            reference_group = max(rates, key=rates.get)

        protected_rate = rates.get(protected_group, 0.0)
        reference_rate = rates.get(reference_group, 0.0)
        return FairnessReport(
            attribute=attribute,
            protected_group=protected_group,
            reference_group=reference_group,
            group_rates=tuple(group_rates),
            disparate_impact_ratio=_safe_ratio(protected_rate, reference_rate),
            statistical_parity_difference=protected_rate - reference_rate,
            threshold=self.threshold_,
        )
