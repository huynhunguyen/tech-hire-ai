"""Composition root: wires data, governance, models, explainers and oversight together."""

from dataclasses import dataclass

import pandas as pd
from sklearn.model_selection import train_test_split

from techhire.config import AppSettings, load_settings
from techhire.data.dataset_loader import DatasetLoader, DatasetLoadReport
from techhire.domain import schema
from techhire.explainability.shap_explainer import LocalExplainer
from techhire.governance.bias_auditor import (
    AGE_PROTECTED_BAND,
    AGE_REFERENCE_BAND,
    BiasAuditor,
    FairnessReport,
    to_age_band,
)
from techhire.governance.reweighing import ReweighingResult, compute_reweighing_weights
from techhire.governance.sensitive_attribute_filter import drop_sensitive_attributes
from techhire.ml_engine.model_comparator import ModelComparator, ModelEvaluation
from techhire.ml_engine.model_trainer import ModelTrainer, ModelVariant, TrainedModel
from techhire.ml_engine.recommendation_engine import RecommendationEngine
from techhire.oversight.audit_logger import AuditLogger
from techhire.oversight.decision_gate import DecisionGate
from techhire.services.screening_service import ScreeningService


@dataclass(frozen=True)
class DataGovernanceSummary:
    load_report: DatasetLoadReport
    gender_fairness: FairnessReport
    ethnicity_fairness: FairnessReport
    age_fairness: FairnessReport
    removed_attributes: tuple[str, ...]
    model_input_columns: tuple[str, ...]
    reweighing: ReweighingResult
    reweighed_gender_fairness: FairnessReport


@dataclass(frozen=True)
class ComplianceSystem:
    settings: AppSettings
    dataset: pd.DataFrame
    candidate_pool: pd.DataFrame
    governance: DataGovernanceSummary
    models: dict[ModelVariant, TrainedModel]
    evaluations: dict[ModelVariant, ModelEvaluation]
    screening_service: ScreeningService
    decision_gate: DecisionGate
    audit_logger: AuditLogger

    @property
    def compliant_model(self) -> TrainedModel:
        return self.models[ModelVariant.COMPLIANT]


def _reweighing_groups(frame: pd.DataFrame, attributes: tuple[str, ...]) -> pd.DataFrame:
    groups = frame[list(attributes)].copy()
    if schema.AGE in groups.columns:
        groups[schema.AGE] = to_age_band(frame[schema.AGE])
    return groups


def _audit_historical_data(
    auditor: BiasAuditor, report: DatasetLoadReport, dataset: pd.DataFrame, train_frame: pd.DataFrame,
    reweighing_attributes: tuple[str, ...],
) -> DataGovernanceSummary:
    labels = dataset[schema.HIRING_DECISION]
    reweighing = compute_reweighing_weights(
        _reweighing_groups(train_frame, reweighing_attributes), train_frame[schema.HIRING_DECISION]
    )
    model_input_columns = tuple(
        column
        for column in drop_sensitive_attributes(dataset).columns
        if column not in (schema.CANDIDATE_ID, schema.HIRING_DECISION)
    )
    return DataGovernanceSummary(
        load_report=report,
        gender_fairness=auditor.audit(
            dataset[schema.GENDER], labels, schema.GENDER, schema.GENDER_FEMALE, schema.GENDER_MALE
        ),
        ethnicity_fairness=auditor.audit(dataset[schema.ETHNICITY], labels, schema.ETHNICITY),
        age_fairness=auditor.audit(
            to_age_band(dataset[schema.AGE]), labels, schema.AGE, AGE_PROTECTED_BAND, AGE_REFERENCE_BAND
        ),
        removed_attributes=schema.SENSITIVE_ATTRIBUTES,
        model_input_columns=model_input_columns,
        reweighing=reweighing,
        reweighed_gender_fairness=auditor.audit(
            train_frame[schema.GENDER],
            train_frame[schema.HIRING_DECISION],
            schema.GENDER,
            schema.GENDER_FEMALE,
            schema.GENDER_MALE,
            sample_weight=reweighing.sample_weights,
        ),
    )


def build_compliance_system(settings: AppSettings | None = None) -> ComplianceSystem:
    settings = settings or load_settings()
    loaded = DatasetLoader(
        settings.dataset_path, settings.synthetic_sample_size, settings.model.random_state
    ).load()
    dataset = loaded.frame

    train_frame, test_frame = train_test_split(
        dataset,
        test_size=settings.model.test_size,
        random_state=settings.model.random_state,
        stratify=dataset[schema.HIRING_DECISION],
    )

    auditor = BiasAuditor(settings.fairness.dir_threshold)
    governance = _audit_historical_data(
        auditor, loaded.report, dataset, train_frame, settings.fairness.reweighing_attributes
    )

    trainer = ModelTrainer(settings.model)
    models = {
        ModelVariant.NON_COMPLIANT: trainer.train(ModelVariant.NON_COMPLIANT, train_frame),
        ModelVariant.UNAWARE: trainer.train(ModelVariant.UNAWARE, train_frame),
        ModelVariant.COMPLIANT: trainer.train(
            ModelVariant.COMPLIANT, train_frame, sample_weight=governance.reweighing.sample_weights
        ),
    }

    threshold = settings.recommendation.interview_threshold
    comparator = ModelComparator(auditor, threshold)
    evaluations = {variant: comparator.evaluate(model, test_frame) for variant, model in models.items()}

    screening_service = ScreeningService(
        engine=RecommendationEngine(models[ModelVariant.COMPLIANT], threshold),
        explainer=LocalExplainer(models[ModelVariant.COMPLIANT]),
        reference_model=models[ModelVariant.NON_COMPLIANT],
        reference_explainer=LocalExplainer(models[ModelVariant.NON_COMPLIANT]),
    )
    audit_logger = AuditLogger(settings.audit_log_path)

    return ComplianceSystem(
        settings=settings,
        dataset=dataset,
        candidate_pool=test_frame.sort_values(schema.CANDIDATE_ID).reset_index(drop=True),
        governance=governance,
        models=models,
        evaluations=evaluations,
        screening_service=screening_service,
        decision_gate=DecisionGate(settings.oversight, audit_logger),
        audit_logger=audit_logger,
    )
