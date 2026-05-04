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
        "\n=== MedicineAI (clinical decision-support prototype) ===\n"
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


def run_through_diagnosis_only(
    case: PatientCase,
    *,
    interactive: bool = False,
) -> WorkflowContext:
    """
    Run symptom analysis and diagnosis ranking only (plus ICD-11 context).
    Does not select a working differential or run treatment / verification — for APIs where the
    clinician chooses the differential first, then ``continue_from_selected_diagnosis`` runs.
    """

    def say(*args: object, **kwargs: object) -> None:
        if interactive:
            print(*args, **kwargs)

    if interactive:
        _print_banner()

    ctx = WorkflowContext(case=case)
    symptom_chain = build_symptom_chain()
    diagnosis_chain = build_diagnosis_chain()

    ctx.log("phase", {"phase": WorkflowPhase.SYMPTOM.value})
    say("\n[Agent 1 — Symptom analysis]")
    symptom: SymptomAnalysisOutput = symptom_chain.invoke({"case_text": case.as_prompt_context()})
    ctx.symptom = symptom
    ctx.log("symptom_output", {"data": symptom.model_dump()})
    say(symptom.clinical_summary)
    say("\nKey points:")
    for p in symptom.key_points:
        say(f"  - {p}")

    say("\n[ICD-11 MMS search context]")
    icd_ctx = build_icd_context_for_queries(symptom.icd_search_queries)
    ctx.icd_context = icd_ctx
    if icd_ctx.strip():
        say(icd_ctx[:8000])
        if len(icd_ctx) > 8000:
            say("\n... (truncated display)")
    else:
        say("(No ICD-11 credentials or no results — diagnosis agent continues with LLM only.)")

    ctx.log("phase", {"phase": WorkflowPhase.DIAGNOSIS.value})
    say("\n[Agent 2 — Diagnosis suggestions]")
    diagnosis: DiagnosisOutput = diagnosis_chain.invoke(
        {
            "symptom_json": symptom.model_dump_json(indent=2),
            "icd_context": icd_ctx or "(no ICD-11 API results)",
        }
    )
    ctx.diagnosis = diagnosis
    ctx.log("diagnosis_output", {"data": diagnosis.model_dump()})

    ctx.log("stopped_after_diagnosis", {"reason": "awaiting_differential_selection"})
    return ctx


def run_case(
    case: PatientCase,
    *,
    log_path: Path | None = None,
    interactive: bool = True,
    auto_diagnosis_index: int = 0,
) -> WorkflowContext:
    """
    Run the full workflow. When ``interactive`` is False (e.g. HTTP API), stdin is not used:
    the first plausible diagnosis at ``auto_diagnosis_index`` is accepted and treatment is
    accepted on the first pass. No banner or agent prints are written to stdout.
    """

    def say(*args: object, **kwargs: object) -> None:
        if interactive:
            print(*args, **kwargs)

    if interactive:
        _print_banner()
    ctx = WorkflowContext(case=case)
    symptom_chain = build_symptom_chain()
    diagnosis_chain = build_diagnosis_chain()
    treatment_chain = build_treatment_chain()
    verification_chain = build_verification_chain()

    # Phase: symptom + diagnosis loop (restart from symptom)
    while True:
        ctx.log("phase", {"phase": WorkflowPhase.SYMPTOM.value})
        say("\n[Agent 1 — Symptom analysis]")
        symptom: SymptomAnalysisOutput = symptom_chain.invoke({"case_text": case.as_prompt_context()})
        ctx.symptom = symptom
        ctx.log("symptom_output", {"data": symptom.model_dump()})
        say(symptom.clinical_summary)
        say("\nKey points:")
        for p in symptom.key_points:
            say(f"  - {p}")

        say("\n[ICD-11 MMS search context]")
        icd_ctx = build_icd_context_for_queries(symptom.icd_search_queries)
        ctx.icd_context = icd_ctx
        if icd_ctx.strip():
            say(icd_ctx[:8000])
            if len(icd_ctx) > 8000:
                say("\n... (truncated display)")
        else:
            say("(No ICD-11 credentials or no results — diagnosis agent continues with LLM only.)")

        ctx.log("phase", {"phase": WorkflowPhase.DIAGNOSIS.value})
        say("\n[Agent 2 — Diagnosis suggestions]")
        diagnosis: DiagnosisOutput = diagnosis_chain.invoke(
            {
                "symptom_json": symptom.model_dump_json(indent=2),
                "icd_context": icd_ctx or "(no ICD-11 API results)",
            }
        )
        ctx.diagnosis = diagnosis
        ctx.log("diagnosis_output", {"data": diagnosis.model_dump()})

        if interactive:
            action, idx = _review_diagnosis(diagnosis)
        else:
            idx = max(0, min(auto_diagnosis_index, len(diagnosis.candidates) - 1))
            action, idx = "accept", idx
        ctx.log("doctor_diagnosis_review", {"action": action, "index": idx})

        if action == "handoff":
            ctx.log("terminated", {"reason": "doctor_handoff_diagnosis"})
            say("\nProcess ended: clinician takes over.")
            return ctx
        if action == "restart":
            say("\nRestarting from symptom analysis agent...\n")
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
        say("\n[Agent 3 — Treatment proposal]")
        treatment = treatment_chain.invoke(
            {
                "case_text": case.as_prompt_context(),
                "diagnosis_line": diagnosis_line,
            }
        )
        ctx.treatment = treatment
        ctx.log("treatment_output", {"data": treatment.model_dump()})
        say(treatment.overview)
        say("\nGeneral measures:")
        for m in treatment.general_measures:
            say(f"  - {m}")
        say(f"\nFollow-up: {treatment.follow_up}")
        say(f"\n{treatment.disclaimer_note}")

        if interactive:
            choice = _review_treatment()
        else:
            choice = "A"
        ctx.log("doctor_treatment_review", {"action": choice})

        if choice == "H":
            ctx.log("terminated", {"reason": "doctor_handoff_treatment"})
            say("\nProcess ended: clinician takes over.")
            return ctx
        if choice == "R":
            say("\nSending back to treatment agent...\n")
            continue
        break

    ctx.log("phase", {"phase": WorkflowPhase.VERIFICATION.value})
    say("\n[Agent 4 — Verification / patient summary]")
    verification = verification_chain.invoke(
        {
            "case_text": case.as_prompt_context(),
            "diagnosis_line": diagnosis_line,
            "treatment_json": ctx.treatment.model_dump_json(indent=2),
        }
    )
    ctx.verification = verification
    ctx.log("verification_output", {"data": verification.model_dump()})

    say("\n========== Output for patient ==========\n")
    say(f"**{verification.patient_title}**\n")
    say(verification.patient_summary)
    say("\nWhat to do next:")
    for s in verification.what_to_do_next:
        say(f"  - {s}")
    say(f"\nWhen to seek care:\n{verification.when_to_seek_care}")
    say("\n========================================\n")

    ctx.log("phase", {"phase": WorkflowPhase.DONE.value})

    if log_path is not None:
        payload = {
            "case_schema": case.schema_version,
            "audit": _dump_audit(ctx),
        }
        log_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        say(f"Session log written to {log_path}")

    return ctx


def continue_from_selected_diagnosis(
    case: PatientCase,
    *,
    symptom: SymptomAnalysisOutput,
    diagnosis: DiagnosisOutput,
    diagnosis_index: int,
    icd_context: str = "",
    interactive: bool = False,
) -> WorkflowContext:
    """
    Re-run only treatment → verification using existing symptom and diagnosis outputs.
    Use when the clinician changes which ranked differential should drive management,
    without re-invoking the symptom or diagnosis agents.
    """

    def say(*args: object, **kwargs: object) -> None:
        if interactive:
            print(*args, **kwargs)

    if not diagnosis.candidates:
        raise RuntimeError("Diagnosis has no candidates; cannot continue.")

    idx = max(0, min(diagnosis_index, len(diagnosis.candidates) - 1))

    ctx = WorkflowContext(case=case)
    ctx.symptom = symptom
    ctx.diagnosis = diagnosis
    ctx.icd_context = icd_context
    ctx.selected_diagnosis = diagnosis.candidates[idx]
    ctx.log("phase", {"phase": WorkflowPhase.SYMPTOM.value})
    ctx.log("symptom_output", {"data": symptom.model_dump(), "reused": True})
    ctx.log("phase", {"phase": WorkflowPhase.DIAGNOSIS.value})
    ctx.log("diagnosis_output", {"data": diagnosis.model_dump(), "reused": True})
    ctx.log("continue_from_diagnosis", {"diagnosis_index": idx})

    treatment_chain = build_treatment_chain()
    verification_chain = build_verification_chain()

    diagnosis_line = (
        f"{ctx.selected_diagnosis.title}\n"
        f"Rationale: {ctx.selected_diagnosis.rationale}\n"
        f"ICD-11: {ctx.selected_diagnosis.icd11_code or ''} {ctx.selected_diagnosis.icd11_uri or ''}".strip()
    )

    while True:
        ctx.log("phase", {"phase": WorkflowPhase.TREATMENT.value})
        say("\n[Agent 3 — Treatment proposal]")
        treatment = treatment_chain.invoke(
            {
                "case_text": case.as_prompt_context(),
                "diagnosis_line": diagnosis_line,
            }
        )
        ctx.treatment = treatment
        ctx.log("treatment_output", {"data": treatment.model_dump()})
        say(treatment.overview)
        say("\nGeneral measures:")
        for m in treatment.general_measures:
            say(f"  - {m}")
        say(f"\nFollow-up: {treatment.follow_up}")
        say(f"\n{treatment.disclaimer_note}")

        if interactive:
            choice = _review_treatment()
        else:
            choice = "A"
        ctx.log("doctor_treatment_review", {"action": choice})

        if choice == "H":
            ctx.log("terminated", {"reason": "doctor_handoff_treatment"})
            say("\nProcess ended: clinician takes over.")
            return ctx
        if choice == "R":
            say("\nSending back to treatment agent...\n")
            continue
        break

    ctx.log("phase", {"phase": WorkflowPhase.VERIFICATION.value})
    say("\n[Agent 4 — Verification / patient summary]")
    verification = verification_chain.invoke(
        {
            "case_text": case.as_prompt_context(),
            "diagnosis_line": diagnosis_line,
            "treatment_json": ctx.treatment.model_dump_json(indent=2),
        }
    )
    ctx.verification = verification
    ctx.log("verification_output", {"data": verification.model_dump()})

    say("\n========== Output for patient ==========\n")
    say(f"**{verification.patient_title}**\n")
    say(verification.patient_summary)
    say("\nWhat to do next:")
    for s in verification.what_to_do_next:
        say(f"  - {s}")
    say(f"\nWhen to seek care:\n{verification.when_to_seek_care}")
    say("\n========================================\n")

    ctx.log("phase", {"phase": WorkflowPhase.DONE.value})
    return ctx
