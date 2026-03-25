"""Pydantic models: patient case input and structured agent outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Demographics(BaseModel):
    age: int | None = None
    sex: str | None = None
    pregnancy: bool | None = None
    weight_kg: float | None = None


class SymptomEntry(BaseModel):
    description: str
    onset: str | None = None
    severity: str | None = None
    duration: str | None = None


class PatientCase(BaseModel):
    schema_version: str = "patient_case_v1"
    demographics: Demographics = Field(default_factory=Demographics)
    chief_complaint: str = ""
    symptoms: list[SymptomEntry] = Field(default_factory=list)
    history: str | None = None
    medications: list[str] | None = None
    allergies: list[str] | None = None
    vitals: dict[str, Any] | None = None
    labs: Any = None

    def as_prompt_context(self) -> str:
        parts = [
            f"Demographics: {self.demographics.model_dump_json(exclude_none=True)}",
            f"Chief complaint: {self.chief_complaint}",
            "Symptoms:",
        ]
        for s in self.symptoms:
            parts.append(f"  - {s.model_dump_json(exclude_none=True)}")
        if self.history:
            parts.append(f"History: {self.history}")
        if self.medications:
            parts.append(f"Medications: {', '.join(self.medications)}")
        if self.allergies:
            parts.append(f"Allergies: {', '.join(self.allergies)}")
        if self.vitals:
            parts.append(f"Vitals: {self.vitals}")
        if self.labs is not None:
            parts.append(f"Labs: {self.labs}")
        return "\n".join(parts)


class SymptomAnalysisOutput(BaseModel):
    clinical_summary: str = Field(description="Concise clinical-style summary of the presentation.")
    key_points: list[str] = Field(description="Bullet-level key points for downstream reasoning.")
    icd_search_queries: list[str] = Field(
        description="2-6 short English search phrases for ICD-11 lookup (symptoms/syndromes)."
    )


class DiagnosisCandidate(BaseModel):
    title: str
    rationale: str
    icd11_uri: str | None = Field(default=None, description="WHO ICD-11 entity URI if grounded in API results.")
    icd11_code: str | None = Field(default=None, description="Human-readable code/label from API if available.")
    is_high_risk: bool = Field(
        default=False,
        description="True if this condition typically requires urgent specialist care (e.g. suspected malignancy, sepsis).",
    )


class DiagnosisOutput(BaseModel):
    candidates: list[DiagnosisCandidate] = Field(
        min_length=1,
        max_length=8,
        description="Ranked plausible diagnoses for physician review.",
    )


class TreatmentOutput(BaseModel):
    overview: str = Field(description="High-level, non-prescriptive management overview.")
    general_measures: list[str] = Field(description="Supportive or general measures to discuss with a clinician.")
    follow_up: str = Field(description="When to seek urgent care or routine follow-up.")
    educational_note: str = Field(
        description="Reminder that this is not personalized medical advice.",
    )


class VerificationOutput(BaseModel):
    patient_title: str = Field(description="Short plain-language title for the patient document.")
    patient_summary: str = Field(description="Plain-language explanation suitable for a lay reader.")
    what_to_do_next: list[str] = Field(description="Simple next steps in everyday language.")
    when_to_seek_care: str = Field(description="Clear guidance on warning signs / urgent care.")
