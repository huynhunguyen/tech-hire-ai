"""Synthetic recruitment data following the candidate schema of the project specification.

Competence is generated independently of gender, but the historical hiring label adds a
bonus for male candidates (Amazon 2018 style) and smaller penalties for older candidates
and some ethnic groups. A mild career-gap proxy lowers experience for female candidates,
so removing the Gender column alone does not erase all bias.
"""

import numpy as np
import pandas as pd

from techhire.domain import schema

ETHNIC_GROUPS = ("White", "Asian", "Black", "Hispanic")
ETHNIC_GROUP_SHARES = (0.46, 0.22, 0.17, 0.15)
DISADVANTAGED_ETHNIC_GROUPS = ("Black", "Hispanic")

MALE_HISTORICAL_BONUS = 0.50
OLDER_CANDIDATE_AGE = 40
OLDER_CANDIDATE_PENALTY = 0.70
ETHNIC_PENALTY = 0.25
FEMALE_EXPERIENCE_GAP_YEARS = 2.0
HISTORICAL_HIRE_RATE = 0.40


def _standardize(values: np.ndarray) -> np.ndarray:
    return (values - values.mean()) / values.std()


def generate_synthetic_dataset(sample_size: int = 2000, random_state: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(random_state)

    gender = rng.choice([schema.GENDER_MALE, schema.GENDER_FEMALE], size=sample_size, p=[0.58, 0.42])
    is_female = gender == schema.GENDER_FEMALE
    age = rng.integers(21, 61, size=sample_size)
    ethnicity = rng.choice(ETHNIC_GROUPS, size=sample_size, p=ETHNIC_GROUP_SHARES)

    working_years = np.maximum(age - 22, 0)
    experience = working_years * rng.uniform(0.35, 0.85, size=sample_size)
    experience = experience - is_female * FEMALE_EXPERIENCE_GAP_YEARS + rng.normal(0, 1.0, size=sample_size)
    experience = np.clip(np.round(experience, 1), 0, 40)

    education_index = rng.choice(len(schema.EDUCATION_LEVELS), size=sample_size, p=[0.15, 0.50, 0.28, 0.07])
    skill_score = np.clip(np.round(rng.normal(65, 14, size=sample_size)), 0, 100)
    interview_score = np.clip(np.round(0.4 * skill_score + rng.normal(38, 12, size=sample_size)), 0, 100)
    certification_count = rng.poisson(1.2 + 0.6 * education_index)
    certification_count = np.clip(certification_count, 0, 15)

    merit = (
        0.30 * _standardize(experience)
        + 0.15 * _standardize(education_index.astype(float))
        + 0.30 * _standardize(skill_score)
        + 0.30 * _standardize(interview_score)
        + 0.15 * _standardize(certification_count.astype(float))
    )
    historical_bias = (
        MALE_HISTORICAL_BONUS * (~is_female)
        - OLDER_CANDIDATE_PENALTY * (age >= OLDER_CANDIDATE_AGE)
        - ETHNIC_PENALTY * np.isin(ethnicity, DISADVANTAGED_ETHNIC_GROUPS)
    )
    hiring_signal = merit + historical_bias + rng.normal(0, 0.45, size=sample_size)
    cutoff = np.quantile(hiring_signal, 1 - HISTORICAL_HIRE_RATE)

    return pd.DataFrame(
        {
            schema.CANDIDATE_ID: [f"C-{index:05d}" for index in range(1, sample_size + 1)],
            schema.GENDER: gender,
            schema.AGE: age,
            schema.ETHNICITY: ethnicity,
            schema.EXPERIENCE_YEARS: experience,
            schema.EDUCATION_LEVEL: [schema.EDUCATION_LEVELS[index] for index in education_index],
            schema.SKILL_SCORE: skill_score,
            schema.INTERVIEW_SCORE: interview_score,
            schema.CERTIFICATION_COUNT: certification_count,
            schema.HIRING_DECISION: (hiring_signal >= cutoff).astype(int),
        }
    )


def inject_invalid_rows(frame: pd.DataFrame, row_count: int, random_state: int = 7) -> pd.DataFrame:
    """Simulates a crude data-poisoning attempt with out-of-range, positively labelled rows."""
    rng = np.random.default_rng(random_state)
    poisoned = frame.sample(n=row_count, random_state=random_state, replace=True).copy()
    poisoned[schema.CANDIDATE_ID] = [f"X-{index:05d}" for index in range(1, row_count + 1)]
    poisoned[schema.SKILL_SCORE] = rng.integers(150, 999, size=row_count)
    poisoned[schema.EXPERIENCE_YEARS] = -rng.integers(1, 10, size=row_count)
    poisoned[schema.HIRING_DECISION] = 1
    return pd.concat([frame, poisoned], ignore_index=True)
