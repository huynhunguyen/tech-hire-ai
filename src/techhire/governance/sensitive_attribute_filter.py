"""Shift-left removal of protected attributes before data reaches the model."""

from collections.abc import Iterable

import pandas as pd

from techhire.domain.schema import SENSITIVE_ATTRIBUTES
from techhire.domain.exceptions import SensitiveAttributeLeakError


def drop_sensitive_attributes(
    frame: pd.DataFrame, sensitive_attributes: Iterable[str] = SENSITIVE_ATTRIBUTES
) -> pd.DataFrame:
    present = [column for column in sensitive_attributes if column in frame.columns]
    return frame.drop(columns=present)


def assert_blind_to_sensitive_attributes(
    feature_names: Iterable[str], sensitive_attributes: Iterable[str] = SENSITIVE_ATTRIBUTES
) -> None:
    """Fails fast if an encoded feature is derived from a protected attribute (e.g. Gender_Male)."""
    leaked = [
        feature
        for feature in feature_names
        if any(feature == attribute or feature.startswith(f"{attribute}=") for attribute in sensitive_attributes)
    ]
    if leaked:
        raise SensitiveAttributeLeakError(f"Sensitive features reached a blind model: {', '.join(leaked)}")
