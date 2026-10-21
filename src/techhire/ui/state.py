"""Typed accessors for Streamlit session state shared between dashboard areas."""

import pandas as pd
import streamlit as st

from techhire.services.screening_service import CandidateAssessment

CURRENT_ASSESSMENT_KEY = "current_assessment"
CURRENT_CANDIDATE_ROW_KEY = "current_candidate_row"
MANUAL_ASSESSMENT_KEY = "manual_assessment"
DECISION_FEEDBACK_KEY = "decision_feedback"
INTEGRITY_REPORT_KEY = "integrity_report"


def set_current_assessment(assessment: CandidateAssessment, candidate_row: pd.DataFrame | None) -> None:
    st.session_state[CURRENT_ASSESSMENT_KEY] = assessment
    st.session_state[CURRENT_CANDIDATE_ROW_KEY] = candidate_row


def get_current_assessment() -> CandidateAssessment | None:
    return st.session_state.get(CURRENT_ASSESSMENT_KEY)


def get_manual_assessment() -> CandidateAssessment | None:
    return st.session_state.get(MANUAL_ASSESSMENT_KEY)


def set_manual_assessment(assessment: CandidateAssessment) -> None:
    st.session_state[MANUAL_ASSESSMENT_KEY] = assessment
