"""FastAPI app: submit free-text questions, receive structured workflow output."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from medicineai.orchestrator import run_case
from medicineai.schemas import Demographics, PatientCase, SymptomEntry
from medicineai.state import WorkflowContext

DISCLAIMER = (
    "MedicineAI is a research prototype for clinical decision support. "
    "It is not a substitute for professional medical advice, diagnosis, or treatment."
)


def _case_from_query(
    question: str,
    *,
    age: int | None,
    sex: str | None,
) -> PatientCase:
    text = question.strip()
    if not text:
        raise ValueError("question must not be empty")
    return PatientCase(
        demographics=Demographics(age=age, sex=sex),
        chief_complaint=text,
        symptoms=[SymptomEntry(description=text)],
    )


def _serialize_context(ctx: WorkflowContext) -> dict[str, Any]:
    return {
        "disclaimer": DISCLAIMER,
        "symptom": ctx.symptom.model_dump() if ctx.symptom else None,
        "diagnosis": ctx.diagnosis.model_dump() if ctx.diagnosis else None,
        "selected_diagnosis": ctx.selected_diagnosis.model_dump() if ctx.selected_diagnosis else None,
        "treatment": ctx.treatment.model_dump() if ctx.treatment else None,
        "verification": ctx.verification.model_dump() if ctx.verification else None,
        "icd_context": ctx.icd_context,
        "audit": ctx.audit,
    }


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question / symptom narrative.")
    age: int | None = Field(default=None, ge=0, le=130)
    sex: str | None = Field(default=None, description="Optional: e.g. male, female, other.")
    diagnosis_index: int = Field(
        default=0,
        ge=0,
        description="0-based index into ranked diagnosis candidates when running non-interactively.",
    )


class AskResponse(BaseModel):
    ok: bool = True
    result: dict[str, Any]


app = FastAPI(
    title="MedicineAI API",
    description="Submit questions and run the existing multi-agent workflow (non-interactive).",
    version="0.1.0",
)

_origins = os.getenv("MEDICINEAI_CORS_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/ask", response_model=AskResponse)
def ask(body: AskRequest) -> AskResponse:
    try:
        case = _case_from_query(body.question, age=body.age, sex=body.sex)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        ctx = run_case(
            case,
            interactive=False,
            auto_diagnosis_index=body.diagnosis_index,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    return AskResponse(result=_serialize_context(ctx))
