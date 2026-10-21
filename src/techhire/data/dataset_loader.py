"""Loads the recruitment dataset and enforces the canonical schema (Art. 10 and Art. 15)."""

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from techhire.data.synthetic_generator import generate_synthetic_dataset
from techhire.domain import schema
from techhire.domain.exceptions import SchemaValidationError

# Keys are column names lowercased with every non-alphanumeric character removed.
COLUMN_ALIASES: dict[str, str] = {
    "candidateid": schema.CANDIDATE_ID,
    "applicantid": schema.CANDIDATE_ID,
    "id": schema.CANDIDATE_ID,
    "gender": schema.GENDER,
    "sex": schema.GENDER,
    "age": schema.AGE,
    "ethnicity": schema.ETHNICITY,
    "race": schema.ETHNICITY,
    "experienceyears": schema.EXPERIENCE_YEARS,
    "yearsofexperience": schema.EXPERIENCE_YEARS,
    "experience": schema.EXPERIENCE_YEARS,
    "educationlevel": schema.EDUCATION_LEVEL,
    "education": schema.EDUCATION_LEVEL,
    "skillscore": schema.SKILL_SCORE,
    "skillsscore": schema.SKILL_SCORE,
    "interviewscore": schema.INTERVIEW_SCORE,
    "certificationcount": schema.CERTIFICATION_COUNT,
    "certifications": schema.CERTIFICATION_COUNT,
    "numcertifications": schema.CERTIFICATION_COUNT,
    "hiringdecision": schema.HIRING_DECISION,
    "hired": schema.HIRING_DECISION,
    "decision": schema.HIRING_DECISION,
}

GENDER_ALIASES: dict[str, str] = {
    "m": schema.GENDER_MALE,
    "male": schema.GENDER_MALE,
    "man": schema.GENDER_MALE,
    "f": schema.GENDER_FEMALE,
    "female": schema.GENDER_FEMALE,
    "woman": schema.GENDER_FEMALE,
}

EDUCATION_KEYWORDS = (("phd", "PhD"), ("doct", "PhD"), ("mast", "Master"), ("bach", "Bachelor"), ("high", "High School"))

SYNTHETIC_SOURCE = "Dữ liệu mô phỏng, tham khảo bộ Recruitment Bias & Fairness AI Dataset (Kaggle)"

POSITIVE_DECISION_TOKENS ={"1", "1.0", "true", "yes", "hired", "selected", "accept", "accepted"}
NEGATIVE_DECISION_TOKENS = {"0", "0.0", "false", "no", "nothired", "rejected", "reject", "notselected"}


@dataclass(frozen=True)
class DatasetLoadReport:
    source: str
    total_rows: int
    valid_rows: int
    quarantined_rows: int
    duplicate_rows_removed: int
    dropped_columns: tuple[str, ...]


@dataclass(frozen=True)
class LoadedDataset:
    frame: pd.DataFrame
    report: DatasetLoadReport


def _column_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def _normalize_columns(raw: pd.DataFrame) -> tuple[pd.DataFrame, tuple[str, ...]]:
    renamed: dict[str, str] = {}
    dropped: list[str] = []
    for column in raw.columns:
        canonical = COLUMN_ALIASES.get(_column_key(column))
        if canonical is None or canonical in renamed.values():
            dropped.append(str(column))
        else:
            renamed[column] = canonical
    frame = raw[list(renamed)].rename(columns=renamed)

    missing = [column for column in schema.REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise SchemaValidationError(f"Dataset is missing required columns: {', '.join(missing)}")
    return frame, tuple(dropped)


def _normalize_gender(value: object) -> object:
    if pd.isna(value) or not str(value).strip():
        return np.nan
    return GENDER_ALIASES.get(str(value).strip().lower(), schema.GENDER_OTHER)


def _education_from_index(index: int) -> object:
    return schema.EDUCATION_LEVELS[index] if 0 <= index < len(schema.EDUCATION_LEVELS) else np.nan


def _education_from_text(value: object) -> object:
    if pd.isna(value):
        return np.nan
    text = str(value).strip().lower()
    for keyword, level in EDUCATION_KEYWORDS:
        if keyword in text:
            return level
    return np.nan


def _normalize_education(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().all():
        # Ordinal codes may be 0-based or 1-based; decide once for the whole column.
        offset = 1 if numeric.min() >= 1 else 0
        return numeric.map(lambda code: _education_from_index(int(code) - offset))
    return series.map(_education_from_text)


def _normalize_decision(value: object) -> object:
    if pd.isna(value):
        return np.nan
    token = re.sub(r"[^a-z0-9.]", "", str(value).lower())
    if token in POSITIVE_DECISION_TOKENS:
        return 1
    if token in NEGATIVE_DECISION_TOKENS:
        return 0
    return np.nan


def _normalize_values(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    if schema.CANDIDATE_ID not in frame.columns:
        frame[schema.CANDIDATE_ID] = [f"C-{index:05d}" for index in range(1, len(frame) + 1)]
    frame[schema.CANDIDATE_ID] = frame[schema.CANDIDATE_ID].astype(str).str.strip()
    frame[schema.GENDER] = frame[schema.GENDER].map(_normalize_gender)
    frame[schema.ETHNICITY] = frame[schema.ETHNICITY].astype("string").str.strip().replace("", pd.NA)
    frame[schema.EDUCATION_LEVEL] = _normalize_education(frame[schema.EDUCATION_LEVEL])
    frame[schema.HIRING_DECISION] = frame[schema.HIRING_DECISION].map(_normalize_decision)
    for column in schema.NUMERIC_RANGES:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def _valid_row_mask(frame: pd.DataFrame) -> pd.Series:
    mask = frame[list(schema.REQUIRED_COLUMNS)].notna().all(axis=1)
    for column, valid_range in schema.NUMERIC_RANGES.items():
        mask &= frame[column].between(valid_range.min_value, valid_range.max_value)
    return mask


class DatasetLoader:
    def __init__(self, dataset_path: Path | None, synthetic_sample_size: int = 2000, random_state: int = 42):
        self.dataset_path_ = Path(dataset_path) if dataset_path else None
        self.synthetic_sample_size_ = synthetic_sample_size
        self.random_state_ = random_state

    def load(self) -> LoadedDataset:
        if self.dataset_path_ is not None and self.dataset_path_.exists():
            raw = pd.read_csv(self.dataset_path_)
            source = f"CSV: {self.dataset_path_.name}"
        else:
            raw = generate_synthetic_dataset(self.synthetic_sample_size_, self.random_state_)
            source = SYNTHETIC_SOURCE
        return prepare_dataset(raw, source)


def prepare_dataset(raw: pd.DataFrame, source: str) -> LoadedDataset:
    frame, dropped_columns = _normalize_columns(raw)
    frame = _normalize_values(frame)

    valid_mask = _valid_row_mask(frame)
    valid = frame[valid_mask]
    deduplicated = valid.drop_duplicates(subset=schema.CANDIDATE_ID, keep="first")

    clean = deduplicated[list(schema.ALLOWED_COLUMNS)].reset_index(drop=True)
    clean[schema.HIRING_DECISION] = clean[schema.HIRING_DECISION].astype(int)
    clean[schema.CERTIFICATION_COUNT] = clean[schema.CERTIFICATION_COUNT].astype(int)
    clean[schema.AGE] = clean[schema.AGE].astype(int)
    clean[schema.ETHNICITY] = clean[schema.ETHNICITY].astype(str)

    if clean.empty:
        raise SchemaValidationError("No valid rows remain after schema validation.")

    report = DatasetLoadReport(
        source=source,
        total_rows=len(raw),
        valid_rows=len(clean),
        quarantined_rows=int((~valid_mask).sum()),
        duplicate_rows_removed=len(valid) - len(deduplicated),
        dropped_columns=dropped_columns,
    )
    return LoadedDataset(frame=clean, report=report)
