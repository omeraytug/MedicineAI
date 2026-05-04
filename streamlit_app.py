"""
Streamlit UI for MedicineAI: sends questions to the FastAPI backend (`/v1/ask`).

Run API:  uv run uvicorn medicineai.api.main:app --host 127.0.0.1 --port 8000
Run UI:   uv run streamlit run streamlit_app.py
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
import streamlit as st

DEFAULT_API = os.getenv("MEDICINEAI_API_URL", "http://127.0.0.1:8000")


st.set_page_config(
    page_title="MedicineAI",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _call_api(base_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/v1/ask"
    with httpx.Client(timeout=600.0) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        return r.json()


st.title("MedicineAI")
st.caption("Clinical decision-support demo — not for real-world clinical use.")

with st.sidebar:
    st.subheader("Connection")
    api_base = st.text_input("API base URL", value=DEFAULT_API, help="FastAPI server root (no trailing slash).")
    st.subheader("Optional context")
    age_raw = st.text_input("Age (optional)", placeholder="e.g. 42")
    age_val: int | None = None
    if age_raw.strip():
        try:
            age_val = max(0, min(130, int(age_raw.strip())))
        except ValueError:
            st.sidebar.warning("Age must be a whole number; ignoring.")
    sex = st.text_input("Sex (optional)", placeholder="e.g. male, female")
    sex_val = sex.strip() or None
    diag_idx = st.number_input(
        "Diagnosis candidate index",
        min_value=0,
        max_value=7,
        value=0,
        help="Non-interactive runs pick one ranked diagnosis; 0 = top suggestion.",
    )

st.info(
    "**Disclaimer.** This tool is a research prototype. It does not provide medical advice. "
    "Always consult a qualified clinician for health decisions."
)

question = st.text_area(
    "Your question or symptom description",
    height=160,
    placeholder="Describe symptoms, duration, and anything relevant…",
)

col_a, col_b = st.columns([1, 5])
with col_a:
    submit = st.button("Submit", type="primary", use_container_width=True)

if submit:
    if not question.strip():
        st.warning("Enter a question or symptom description.")
    else:
        payload: dict[str, Any] = {
            "question": question.strip(),
            "diagnosis_index": int(diag_idx),
        }
        if age_val is not None:
            payload["age"] = age_val
        if sex_val is not None:
            payload["sex"] = sex_val

        with st.spinner("Running workflow (symptom → diagnosis → treatment → patient summary)…"):
            try:
                data = _call_api(api_base, payload)
            except httpx.HTTPStatusError as e:
                st.error(f"API error {e.response.status_code}: {e.response.text}")
                st.stop()
            except httpx.RequestError as e:
                st.error(f"Could not reach API at {api_base!r}: {e}")
                st.stop()

        st.session_state["last_result"] = data.get("result", data)

res = st.session_state.get("last_result")
if res:
    ver = res.get("verification") or {}
    sym = res.get("symptom") or {}
    tr = res.get("treatment") or {}
    dx = res.get("selected_diagnosis") or {}
    diagnosis_block = res.get("diagnosis") or {}
    candidates = diagnosis_block.get("candidates") or []

    st.divider()
    st.subheader("Multi-agent workflow output")
    st.caption(
        "Each stage runs in order: symptom analysis → ranked diagnoses → treatment → patient-facing summary."
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
    st.markdown("### 2 · Diagnosis suggestions")
    if candidates:
        selected_title = (dx or {}).get("title")
        for i, c in enumerate(candidates):
            title = c.get("title", "")
            risk = " ⚠️ **Higher-risk differential**" if c.get("is_high_risk") else ""
            badge = " *(selected for treatment)*" if selected_title and title == selected_title else ""
            st.markdown(f"**{i + 1}. {title}**{risk}{badge}")
            st.markdown(c.get("rationale") or "")
            icd_parts = [p for p in (c.get("icd11_code"), c.get("icd11_uri")) if p]
            if icd_parts:
                st.caption("ICD-11: " + " · ".join(icd_parts))
            st.markdown("")
    else:
        st.markdown("No diagnosis candidates in response.")

    st.markdown("---")

    # 3 · Treatment agent
    st.markdown("### 3 · Treatment proposal")
    st.markdown(tr.get("overview") or "—")
    if tr.get("general_measures"):
        st.markdown("**General measures**")
        for m in tr["general_measures"]:
            st.markdown(f"- {m}")
    if tr.get("follow_up"):
        st.markdown(f"**Follow-up:** {tr['follow_up']}")
    if tr.get("disclaimer_note"):
        st.caption(tr["disclaimer_note"])

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

    icd_ctx = (res.get("icd_context") or "").strip()
    if icd_ctx:
        with st.expander("ICD-11 reference context (used for diagnosis)"):
            st.text(icd_ctx[:12000] + ("…" if len(icd_ctx) > 12000 else ""))

    with st.expander("Raw JSON"):
        st.download_button(
            "Download JSON",
            data=json.dumps(res, indent=2, ensure_ascii=False),
            file_name="medicineai_response.json",
            mime="application/json",
            key="download_json",
        )
        st.json(res)
