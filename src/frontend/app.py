"""
Streamlit UI for MedicineAI.

Initial run: POST /v1/analyze (symptom + differentials only).
After doctor selects a differential: POST /v1/continue (treatment + patient summary).

Run API:  uv run uvicorn medicineai.api.main:app --host 127.0.0.1 --port 8000
Run UI:   API_URL=http://127.0.0.1:8000 uv run streamlit run src/frontend/app.py
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
import streamlit as st

# Backend base URL (Azure: set Application setting API_URL). MEDICINEAI_API_URL is legacy fallback.
API_URL = os.getenv("API_URL", os.getenv("MEDICINEAI_API_URL", "http://localhost:8000"))

EXAMPLE_PROMPTS: list[tuple[str, str]] = [
    (
        "Acute low back pain",
        "45-year-old with sudden onset low back pain after lifting a heavy box yesterday. "
        "Pain is central, worse with flexion, no radiation past the buttocks. No bowel or bladder changes.",
    ),
    (
        "Cough & fever",
        "32-year-old with dry cough for 5 days, fever to 38.5°C, mild pleuritic chest discomfort, "
        "fatigue. No chronic lung disease. Non-smoker.",
    ),
    (
        "Headache",
        "28-year-old with gradual bilateral pressure headache for 2 weeks, worse end of day. "
        "No focal neuro symptoms, no sudden thunderclap onset. Sleep and hydration help slightly.",
    ),
    (
        "Rash",
        "Adult with itchy erythematous patches on forearms after gardening; linear vesicles. "
        "Similar episode last summer. No fever.",
    ),
]


st.set_page_config(
    page_title="MedicineAI",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _call_continue_api(base_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/v1/continue"
    with httpx.Client(timeout=600.0) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        return r.json()


def _call_analyze_api(base_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/v1/analyze"
    with httpx.Client(timeout=600.0) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        return r.json()


def _analyze_and_store(payload: dict[str, Any]) -> bool:
    """Symptom + diagnosis agents only; no treatment until doctor uses /v1/continue."""
    with st.spinner("Running symptom analysis and differential ranking…"):
        try:
            data = _call_analyze_api(API_URL, payload)
        except httpx.HTTPStatusError as e:
            st.error(f"API error {e.response.status_code}: {e.response.text}")
            return False
        except httpx.RequestError as e:
            st.error(f"Could not reach the API: {e}")
            return False

    result = data.get("result", data)
    st.session_state["last_result"] = result
    st.session_state["last_case"] = {
        "question": payload["question"],
        "age": payload.get("age"),
        "sex": payload.get("sex"),
        "diagnosis_index": None,
    }
    st.session_state["show_treatment_patient"] = False
    return True


def _continue_and_store(prior: dict[str, Any], lc: dict[str, Any], diagnosis_index: int) -> bool:
    """Re-run treatment + summary only; keeps symptom and diagnosis list from prior result."""
    sym = prior.get("symptom")
    dx_block = prior.get("diagnosis")
    if not sym or not dx_block:
        st.error("Missing symptom or diagnosis in prior result; run **Run analysis** first.")
        return False

    body: dict[str, Any] = {
        "question": lc["question"],
        "symptom": sym,
        "diagnosis": dx_block,
        "diagnosis_index": diagnosis_index,
        "icd_context": prior.get("icd_context") or "",
    }
    if lc.get("age") is not None:
        body["age"] = lc["age"]
    if lc.get("sex"):
        body["sex"] = lc["sex"]

    with st.spinner("Updating treatment and patient summary for the selected differential (symptom & differentials unchanged)…"):
        try:
            data = _call_continue_api(API_URL, body)
        except httpx.HTTPStatusError as e:
            st.error(f"API error {e.response.status_code}: {e.response.text}")
            return False
        except httpx.RequestError as e:
            st.error(f"Could not reach the API: {e}")
            return False

    result = data.get("result", data)
    st.session_state["last_result"] = result
    st.session_state["last_case"] = {
        "question": lc["question"],
        "age": lc.get("age"),
        "sex": lc.get("sex"),
        "diagnosis_index": int(diagnosis_index),
    }
    st.session_state["show_treatment_patient"] = True
    return True


st.title("MedicineAI")
st.caption("Clinical decision support — case review, differentials, management, and patient-facing summary.")

with st.sidebar:
    st.subheader("Patient context (optional)")
    age_raw = st.text_input("Age (optional)", placeholder="e.g. 42")
    age_val: int | None = None
    if age_raw.strip():
        try:
            age_val = max(0, min(130, int(age_raw.strip())))
        except ValueError:
            st.sidebar.warning("Age must be a whole number; ignoring.")
    sex = st.text_input("Sex (optional)", placeholder="e.g. male, female")
    sex_val = sex.strip() or None

if "symptom_text" not in st.session_state:
    st.session_state["symptom_text"] = ""

with st.expander("Example prompts", expanded=False):
    st.caption("Insert a sample vignette into the field below.")
    ex_cols = st.columns(2)
    for i, (label, body) in enumerate(EXAMPLE_PROMPTS):
        with ex_cols[i % 2]:
            if st.button(label, key=f"example_btn_{i}", use_container_width=True):
                st.session_state["symptom_text"] = body
                st.rerun()

st.text_area(
    "Case narrative / chief complaint",
    height=160,
    placeholder="Describe presentation, duration, relevant history, meds, allergies…",
    key="symptom_text",
)

col_a, _ = st.columns([1, 5])
with col_a:
    submit = st.button("Run analysis", type="primary", use_container_width=True)

if submit:
    question = st.session_state.get("symptom_text", "").strip()
    if not question:
        st.warning("Enter a case narrative or use an example prompt.")
    else:
        payload: dict[str, Any] = {"question": question}
        if age_val is not None:
            payload["age"] = age_val
        if sex_val is not None:
            payload["sex"] = sex_val
        if _analyze_and_store(payload):
            st.rerun()

res = st.session_state.get("last_result")
show_34 = bool(st.session_state.get("show_treatment_patient", False))

if res:
    ver = res.get("verification") or {}
    sym = res.get("symptom") or {}
    tr = res.get("treatment") or {}
    dx = res.get("selected_diagnosis") or {}
    diagnosis_block = res.get("diagnosis") or {}
    candidates = diagnosis_block.get("candidates") or []
    lc = st.session_state.get("last_case") or {}

    st.divider()
    st.subheader("Workflow output")
    st.caption(
        "**Run analysis** produces §1–2 only. Choose a working differential, then generate §3–4 — "
        "no treatment or patient summary runs until then."
    )

    # 1 · Symptom agent
    st.markdown("### 1 · Symptom analysis")
    st.markdown(sym.get("clinical_summary") or "—")
    if sym.get("key_points"):
        st.markdown("**Key points**")
        for p in sym["key_points"]:
            st.markdown(f"- {p}")

    st.markdown("---")

    # 2 · Diagnosis agent
    st.markdown("### 2 · Diagnosis differentials")
    if candidates:
        selected_title = (dx or {}).get("title") if show_34 and res.get("verification") else None
        for i, c in enumerate(candidates):
            title = c.get("title", "")
            risk = " ⚠️ **Higher-risk differential**" if c.get("is_high_risk") else ""
            badge = ""
            if show_34 and selected_title and title == selected_title:
                badge = " *(working diagnosis for sections 3–4)*"
            st.markdown(f"**{i + 1}. {title}**{risk}{badge}")
            st.markdown(c.get("rationale") or "")
            icd_parts = [p for p in (c.get("icd11_code"), c.get("icd11_uri")) if p]
            if icd_parts:
                st.caption("ICD-11: " + " · ".join(icd_parts))
            st.markdown("")
    else:
        st.markdown("No diagnosis candidates in response.")

    icd_ctx = (res.get("icd_context") or "").strip()
    if icd_ctx:
        with st.expander("ICD-11 reference context (used for diagnosis)"):
            st.text(icd_ctx[:12000] + ("…" if len(icd_ctx) > 12000 else ""))

    # Doctor: must explicitly pick a differential (no implicit default); then generate §3–4 via /v1/continue
    if candidates and lc.get("question"):
        st.markdown("---")
        st.markdown("### Doctor selection")
        applied_raw = lc.get("diagnosis_index")
        applied_idx = (
            max(0, min(int(applied_raw), len(candidates) - 1)) if applied_raw is not None else None
        )

        case_sig = (lc.get("question", ""), applied_raw if applied_raw is not None else -1)
        if st.session_state.get("_dx_case_sig") != case_sig:
            st.session_state["_dx_case_sig"] = case_sig

        _PLACEHOLDER = "— Select a working differential —"
        _labels = [_PLACEHOLDER] + [
            f"{i + 1}. {candidates[i].get('title', 'Unknown')}" for i in range(len(candidates))
        ]
        # After analyze: force placeholder until doctor picks. After /v1/continue: show current selection.
        _default_i = 0 if applied_raw is None else (applied_idx or 0) + 1

        sel = st.selectbox(
            "Working differential for sections 3–4 (required)",
            _labels,
            index=min(_default_i, len(_labels) - 1),
            key=f"doctor_dx_sel_{case_sig}",
        )
        picked: int | None = None if sel == _PLACEHOLDER else _labels.index(sel) - 1

        if (
            applied_raw is not None
            and picked is not None
            and applied_idx is not None
            and picked != applied_idx
        ):
            st.session_state["show_treatment_patient"] = False

        choice_ok = picked is not None
        first_plan = applied_raw is None
        plan_outdated = (
            applied_raw is not None
            and picked is not None
            and applied_idx is not None
            and picked != applied_idx
        )
        gen_label = (
            "Generate treatment & patient summary"
            if first_plan
            else ("Update treatment & patient summary for selection" if plan_outdated else "Treatment matches selection")
        )
        gen_disabled = not choice_ok or (not first_plan and not plan_outdated)

        gen = st.button(
            gen_label,
            type="primary",
            disabled=gen_disabled,
            use_container_width=True,
            help="Runs treatment and patient-summary agents only; symptom analysis and differential list are unchanged.",
        )

        if first_plan:
            st.caption("Pick a differential above, then generate — the first rank is **not** applied until you select it.")
        elif plan_outdated:
            st.info("Selection changed — update to refresh sections 3–4 for the highlighted differential.")

        if gen and not gen_disabled and picked is not None:
            if _continue_and_store(res, lc, picked):
                st.rerun()

    st.markdown("---")

    # 3 · Treatment — only after /v1/continue
    if show_34 and res.get("verification"):
        st.markdown("### 3 · Treatment proposal")
        st.markdown(tr.get("overview") or "—")
        if tr.get("general_measures"):
            st.markdown("**General measures**")
            for m in tr["general_measures"]:
                st.markdown(f"- {m}")
        if tr.get("follow_up"):
            st.markdown(f"**Follow-up:** {tr['follow_up']}")

        st.markdown("---")

        # 4 · Verification agent (plain language)
        st.markdown("### 4 · Plain-language summary")
        st.markdown(f"**{ver.get('patient_title', 'Summary')}**")
        st.markdown(ver.get("patient_summary") or "")
        if ver.get("what_to_do_next"):
            st.markdown("**What to do next**")
            for item in ver["what_to_do_next"]:
                st.markdown(f"- {item}")
        if ver.get("when_to_seek_care"):
            st.markdown("**When to seek care**")
            st.markdown(ver["when_to_seek_care"])
    elif candidates and lc.get("question"):
        st.markdown("### 3 · Treatment proposal")
        st.info("Not generated yet — choose a working differential above, then **Generate treatment & patient summary**.")
        st.markdown("### 4 · Plain-language summary")
        st.info("Generated together with section 3 after your selection.")

    if show_34 and res.get("verification"):
        with st.expander("Raw JSON"):
            st.download_button(
                "Download JSON",
                data=json.dumps(res, indent=2, ensure_ascii=False),
                file_name="medicineai_response.json",
                mime="application/json",
                key="download_json",
            )
            st.json(res)
