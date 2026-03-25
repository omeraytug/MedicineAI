"""Workflow state for the CLI orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from medicineai.schemas import (
    DiagnosisCandidate,
    DiagnosisOutput,
    PatientCase,
    SymptomAnalysisOutput,
    TreatmentOutput,
    VerificationOutput,
)


class WorkflowPhase(str, Enum):
    SYMPTOM = "symptom"
    DIAGNOSIS = "diagnosis"
    REVIEW_DIAGNOSIS = "review_diagnosis"
    TREATMENT = "treatment"
    REVIEW_TREATMENT = "review_treatment"
    VERIFICATION = "verification"
    DONE = "done"
    TERMINATED = "terminated"


@dataclass
class WorkflowContext:
    case: PatientCase
    symptom: SymptomAnalysisOutput | None = None
    icd_context: str = ""
    diagnosis: DiagnosisOutput | None = None
    selected_diagnosis: DiagnosisCandidate | None = None
    treatment: TreatmentOutput | None = None
    verification: VerificationOutput | None = None
    audit: list[dict[str, Any]] = field(default_factory=list)

    def log(self, event: str, payload: dict[str, Any] | None = None) -> None:
        entry: dict[str, Any] = {"event": event}
        if payload:
            entry.update(payload)
        self.audit.append(entry)
