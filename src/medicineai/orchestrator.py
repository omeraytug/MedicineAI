"""State machine: agents + human review gates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from medicineai.agents import (
    build_diagnosis_chain,
    build_symptom_chain,
    build_treatment_chain,
    build_verification_chain,
)
from medicineai.icd11_client import build_icd_context_for_queries
from medicineai.schemas import DiagnosisOutput, PatientCase, SymptomAnalysisOutput
from medicineai.state import WorkflowContext, WorkflowPhase


def _print_banner() -> None:
    print(
        "\n=== MedicineAI (educational prototype) ===\n"
        "Not for clinical use. Outputs are not medical advice.\n"
    )


def _review_diagnosis(diagnosis: DiagnosisOutput) -> tuple[str, int | None]:
    """
    Returns (action, index) where action is 'accept'|'restart'|'handoff',
    and index is 0-based candidate index if accept.
    """
    print("\n--- Doctor review: diagnoses ---")
    for i, c in enumerate(diagnosis.candidates):
        risk = " [FLAG: high-risk]" if c.is_high_risk else ""
        print(f"  {i + 1}) {c.title}{risk}")
        print(f"      {c.rationale}")
        if c.icd11_uri or c.icd11_code:
            print(f"      ICD-11: {c.icd11_code or ''} {c.icd11_uri or ''}".strip())
    print("\n  [1-N] Accept listed diagnosis  |  R  Incorrect analysis — restart from symptom agent")
    print("  H  High risk / doctor takes over — end process\n")
    while True:
        raw = input("Choice: ").strip().upper()
        if raw == "R":
            return "restart", None
        if raw == "H":
            return "handoff", None
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(diagnosis.candidates):
                return "accept", idx
        print("Invalid input. Enter a number, R, or H.")


def _review_treatment() -> str:
    print("\n--- Doctor review: treatment ---")
    print("  A  Accept treatment draft  |  R  Incorrect — send back to treatment agent")
    print("  H  Doctor takes over — end process\n")
    while True:
        raw = input("Choice: ").strip().upper()
        if raw in {"A", "R", "H"}:
            return raw
        print("Invalid input. Enter A, R, or H.")


def _dump_audit(ctx: WorkflowContext) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for e in ctx.audit:
        out.append(dict(e))
    return out


def run_case(case: PatientCase, *, log_path: Path | None = None) -> WorkflowContext:
    _print_banner()
    ctx = WorkflowContext(case=case)
    symptom_chain = build_symptom_chain()
    diagnosis_chain = build_diagnosis_chain()
    treatment_chain = build_treatment_chain()
    verification_chain = build_verification_chain()

    # Phase: symptom + diagnosis loop (restart from symptom)
    while True:
        ctx.log("phase", {"phase": WorkflowPhase.SYMPTOM.value})
        print("\n[Agent 1 — Symptom analysis]")
        symptom: SymptomAnalysisOutput = symptom_chain.invoke({"case_text": case.as_prompt_context()})
        ctx.symptom = symptom
        ctx.log("symptom_output", {"data": symptom.model_dump()})
        print(symptom.clinical_summary)
        print("\nKey points:")
        for p in symptom.key_points:
            print(f"  - {p}")

        print("\n[ICD-11 MMS search context]")
        icd_ctx = build_icd_context_for_queries(symptom.icd_search_queries)
        ctx.icd_context = icd_ctx
        if icd_ctx.strip():
            print(icd_ctx[:8000])
            if len(icd_ctx) > 8000:
                print("\n... (truncated display)")
        else:
            print("(No ICD-11 credentials or no results — diagnosis agent continues with LLM only.)")

        ctx.log("phase", {"phase": WorkflowPhase.DIAGNOSIS.value})
        print("\n[Agent 2 — Diagnosis suggestions]")
        diagnosis: DiagnosisOutput = diagnosis_chain.invoke(
            {
                "symptom_json": symptom.model_dump_json(indent=2),
                "icd_context": icd_ctx or "(no ICD-11 API results)",
            }
        )
        ctx.diagnosis = diagnosis
        ctx.log("diagnosis_output", {"data": diagnosis.model_dump()})

        action, idx = _review_diagnosis(diagnosis)
        ctx.log("doctor_diagnosis_review", {"action": action, "index": idx})

        if action == "handoff":
            ctx.log("terminated", {"reason": "doctor_handoff_diagnosis"})
            print("\nProcess ended: clinician takes over.")
            return ctx
        if action == "restart":
            print("\nRestarting from symptom analysis agent...\n")
            continue

        assert idx is not None
        ctx.selected_diagnosis = diagnosis.candidates[idx]
        break

    # Treatment loop
    diagnosis_line = (
        f"{ctx.selected_diagnosis.title}\n"
        f"Rationale: {ctx.selected_diagnosis.rationale}\n"
        f"ICD-11: {ctx.selected_diagnosis.icd11_code or ''} {ctx.selected_diagnosis.icd11_uri or ''}".strip()
    )

    while True:
        ctx.log("phase", {"phase": WorkflowPhase.TREATMENT.value})
        print("\n[Agent 3 — Treatment proposal]")
        treatment = treatment_chain.invoke(
            {
                "case_text": case.as_prompt_context(),
                "diagnosis_line": diagnosis_line,
            }
        )
        ctx.treatment = treatment
        ctx.log("treatment_output", {"data": treatment.model_dump()})
        print(treatment.overview)
        print("\nGeneral measures:")
        for m in treatment.general_measures:
            print(f"  - {m}")
        print(f"\nFollow-up: {treatment.follow_up}")
        print(f"\n{treatment.educational_note}")

        choice = _review_treatment()
        ctx.log("doctor_treatment_review", {"action": choice})

        if choice == "H":
            ctx.log("terminated", {"reason": "doctor_handoff_treatment"})
            print("\nProcess ended: clinician takes over.")
            return ctx
        if choice == "R":
            print("\nSending back to treatment agent...\n")
            continue
        break

    ctx.log("phase", {"phase": WorkflowPhase.VERIFICATION.value})
    print("\n[Agent 4 — Verification / patient summary]")
    verification = verification_chain.invoke(
        {
            "case_text": case.as_prompt_context(),
            "diagnosis_line": diagnosis_line,
            "treatment_json": ctx.treatment.model_dump_json(indent=2),
        }
    )
    ctx.verification = verification
    ctx.log("verification_output", {"data": verification.model_dump()})

    print("\n========== Output for patient ==========\n")
    print(f"**{verification.patient_title}**\n")
    print(verification.patient_summary)
    print("\nWhat to do next:")
    for s in verification.what_to_do_next:
        print(f"  - {s}")
    print(f"\nWhen to seek care:\n{verification.when_to_seek_care}")
    print("\n========================================\n")

    ctx.log("phase", {"phase": WorkflowPhase.DONE.value})

    if log_path is not None:
        payload = {
            "case_schema": case.schema_version,
            "audit": _dump_audit(ctx),
        }
        log_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Session log written to {log_path}")

    return ctx
