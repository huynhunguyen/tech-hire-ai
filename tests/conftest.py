import dataclasses
from pathlib import Path

import pandas as pd
import pytest

from techhire.config import OversightSettings, load_settings
from techhire.data.synthetic_generator import generate_synthetic_dataset
from techhire.domain.models import DecisionRequest, HrDecision, Recommendation
from techhire.oversight.audit_logger import AuditLogger
from techhire.oversight.decision_gate import DecisionGate
from techhire.services.compliance_pipeline import ComplianceSystem, build_compliance_system

VALID_JUSTIFICATION = "Ứng viên có kinh nghiệm backend 6 năm và kết quả phỏng vấn chuyên môn tốt, phù hợp vị trí."


@pytest.fixture(scope="session")
def synthetic_frame() -> pd.DataFrame:
    return generate_synthetic_dataset(sample_size=1500, random_state=42)


@pytest.fixture(scope="session")
def compliance_system(tmp_path_factory: pytest.TempPathFactory) -> ComplianceSystem:
    settings = dataclasses.replace(
        load_settings(),
        dataset_path=None,
        audit_log_path=tmp_path_factory.mktemp("audit") / "audit_log.jsonl",
        synthetic_sample_size=3000,
    )
    return build_compliance_system(settings)


@pytest.fixture
def audit_logger(tmp_path: Path) -> AuditLogger:
    return AuditLogger(tmp_path / "audit_log.jsonl")


@pytest.fixture
def decision_gate(audit_logger: AuditLogger) -> DecisionGate:
    return DecisionGate(OversightSettings(), audit_logger)


@pytest.fixture
def make_request():
    def factory(**overrides) -> DecisionRequest:
        values = dict(
            hr_id="HR-001",
            candidate_id="C-00001",
            ai_score=0.72,
            ai_recommendation=Recommendation.RECOMMEND_INTERVIEW,
            hr_decision=HrDecision.INVITE_TO_INTERVIEW,
            justification=VALID_JUSTIFICATION,
            explanation_reviewed=True,
            model_version="compliant-rf-test",
        )
        values.update(overrides)
        return DecisionRequest(**values)

    return factory
