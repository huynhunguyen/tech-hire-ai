"""Sample reweighing (Kamiran and Calders, 2012).

Each (group, label) cell receives weight P(group) * P(label) / P(group, label), which makes the
weighted label distribution statistically independent of the protected group. Protected data is
only used here, inside the governance layer, as permitted by Art. 10(5) for bias correction.
"""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ReweighingCell:
    group: str
    label: int
    count: int
    observed_probability: float
    expected_probability: float
    weight: float


@dataclass(frozen=True)
class ReweighingResult:
    attributes: tuple[str, ...]
    group_keys: pd.Series
    sample_weights: pd.Series
    cells: tuple[ReweighingCell, ...]


def _combine_group_columns(groups: pd.DataFrame) -> pd.Series:
    return groups.astype(str).agg(" | ".join, axis=1)


def compute_reweighing_weights(groups: pd.DataFrame, labels: pd.Series) -> ReweighingResult:
    group_keys = _combine_group_columns(groups)
    total = len(labels)
    group_probability = group_keys.value_counts(normalize=True)
    label_probability = labels.value_counts(normalize=True)

    weights = pd.Series(1.0, index=labels.index)
    cells = []
    joint = pd.DataFrame({"group": group_keys, "label": labels})
    for (group, label), members in joint.groupby(["group", "label"], sort=True):
        observed = len(members) / total
        expected = group_probability[group] * label_probability[label]
        weight = expected / observed
        weights.loc[members.index] = weight
        cells.append(
            ReweighingCell(
                group=str(group),
                label=int(label),
                count=len(members),
                observed_probability=observed,
                expected_probability=expected,
                weight=weight,
            )
        )
    return ReweighingResult(
        attributes=tuple(groups.columns),
        group_keys=group_keys,
        sample_weights=weights,
        cells=tuple(cells),
    )
