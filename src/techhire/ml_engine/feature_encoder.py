"""Maps canonical candidate frames to the numeric matrix consumed by the models."""

import pandas as pd

from techhire.domain import schema

ONE_HOT_SEPARATOR = "="
EDUCATION_INDEX = {level: index for index, level in enumerate(schema.EDUCATION_LEVELS)}


def source_attribute_of(feature_name: str) -> str:
    return feature_name.split(ONE_HOT_SEPARATOR, 1)[0]


class FeatureEncoder:
    def __init__(self, include_sensitive: bool):
        self.include_sensitive_ = include_sensitive
        self.gender_categories_: tuple[str, ...] = ()
        self.ethnicity_categories_: tuple[str, ...] = ()

    @property
    def include_sensitive(self) -> bool:
        return self.include_sensitive_

    def fit(self, frame: pd.DataFrame) -> "FeatureEncoder":
        if self.include_sensitive_:
            self.gender_categories_ = tuple(sorted(frame[schema.GENDER].astype(str).unique()))
            self.ethnicity_categories_ = tuple(sorted(frame[schema.ETHNICITY].astype(str).unique()))
        return self

    @property
    def feature_names(self) -> tuple[str, ...]:
        names = list(schema.COMPETENCE_FEATURES)
        if self.include_sensitive_:
            names.append(schema.AGE)
            names += [f"{schema.GENDER}{ONE_HOT_SEPARATOR}{value}" for value in self.gender_categories_]
            names += [f"{schema.ETHNICITY}{ONE_HOT_SEPARATOR}{value}" for value in self.ethnicity_categories_]
        return tuple(names)

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        encoded = pd.DataFrame(index=frame.index)
        encoded[schema.EXPERIENCE_YEARS] = frame[schema.EXPERIENCE_YEARS].astype(float)
        encoded[schema.EDUCATION_LEVEL] = frame[schema.EDUCATION_LEVEL].map(EDUCATION_INDEX).astype(float)
        encoded[schema.SKILL_SCORE] = frame[schema.SKILL_SCORE].astype(float)
        encoded[schema.INTERVIEW_SCORE] = frame[schema.INTERVIEW_SCORE].astype(float)
        encoded[schema.CERTIFICATION_COUNT] = frame[schema.CERTIFICATION_COUNT].astype(float)

        if self.include_sensitive_:
            encoded[schema.AGE] = frame[schema.AGE].astype(float)
            gender = frame[schema.GENDER].astype(str)
            for value in self.gender_categories_:
                encoded[f"{schema.GENDER}{ONE_HOT_SEPARATOR}{value}"] = (gender == value).astype(float)
            ethnicity = frame[schema.ETHNICITY].astype(str)
            for value in self.ethnicity_categories_:
                encoded[f"{schema.ETHNICITY}{ONE_HOT_SEPARATOR}{value}"] = (ethnicity == value).astype(float)

        return encoded[list(self.feature_names)]
