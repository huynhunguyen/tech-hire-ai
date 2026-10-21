import pandas as pd
import pytest

from techhire.data.dataset_loader import SYNTHETIC_SOURCE, DatasetLoader, prepare_dataset
from techhire.data.synthetic_generator import inject_invalid_rows
from techhire.domain import schema
from techhire.domain.exceptions import SchemaValidationError


def test_unknown_columns_are_dropped_by_allow_list(synthetic_frame):
    raw = synthetic_frame.assign(Facial_Expression_Score=0.5, Voice_Tone="calm")
    loaded = prepare_dataset(raw, "test")
    assert "Facial_Expression_Score" not in loaded.frame.columns
    assert set(loaded.report.dropped_columns) == {"Facial_Expression_Score", "Voice_Tone"}
    assert tuple(loaded.frame.columns) == schema.ALLOWED_COLUMNS


def test_column_aliases_and_value_encodings_are_normalized():
    raw = pd.DataFrame(
        {
            "applicant id": ["A1", "A2"],
            "sex": ["M", "female"],
            "age": [30, 41],
            "race": ["Asian", "White"],
            "years of experience": [3, 10],
            "education": ["Bachelor's degree", "PhD"],
            "skill score": [70, 80],
            "interview_score": [60, 90],
            "certifications": [1, 4],
            "Hired": ["Yes", "No"],
        }
    )
    frame = prepare_dataset(raw, "test").frame
    assert frame[schema.GENDER].tolist() == [schema.GENDER_MALE, schema.GENDER_FEMALE]
    assert frame[schema.EDUCATION_LEVEL].tolist() == ["Bachelor", "PhD"]
    assert frame[schema.HIRING_DECISION].tolist() == [1, 0]


def test_one_based_education_codes_are_mapped():
    raw = pd.DataFrame(
        {
            "Gender": ["Male", "Female"], "Age": [30, 31], "Ethnicity": ["A", "B"],
            "Experience_Years": [1, 2], "Education_Level": [1, 4], "Skill_Score": [50, 60],
            "Interview_Score": [50, 60], "Certification_Count": [0, 1], "Hiring_Decision": [0, 1],
        }
    )
    assert prepare_dataset(raw, "test").frame[schema.EDUCATION_LEVEL].tolist() == ["High School", "PhD"]


def test_out_of_range_rows_are_quarantined(synthetic_frame):
    poisoned = inject_invalid_rows(synthetic_frame, row_count=40)
    loaded = prepare_dataset(poisoned, "test")
    assert loaded.report.quarantined_rows == 40
    assert loaded.report.valid_rows == len(synthetic_frame)
    assert not loaded.frame[schema.CANDIDATE_ID].str.startswith("X-").any()


def test_missing_required_column_raises(synthetic_frame):
    with pytest.raises(SchemaValidationError, match=schema.SKILL_SCORE):
        prepare_dataset(synthetic_frame.drop(columns=[schema.SKILL_SCORE]), "test")


def test_synthetic_data_is_used_unless_a_csv_is_configured(tmp_path):
    assert DatasetLoader(None, synthetic_sample_size=300).load().report.source == SYNTHETIC_SOURCE
    assert DatasetLoader(tmp_path / "missing.csv", synthetic_sample_size=300).load().report.source == SYNTHETIC_SOURCE
