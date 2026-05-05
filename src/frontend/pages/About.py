"""About MedicineAI — doctor-facing overview (Streamlit multipage)."""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="About — MedicineAI", page_icon="🩺", layout="wide")

st.title("About MedicineAI")
st.markdown(
    "MedicineAI is a **clinical decision-support** tool. It helps you move from a case narrative "
    "to structured reasoning — symptom overview, ranked differentials, then management ideas and "
    "patient-facing language tied to **your** chosen working diagnosis."
)
st.info(
    "It does **not** replace clinical judgment, bedside assessment, or local protocols. "
    "You remain responsible for all decisions."
)

st.divider()
st.subheader("How the workflow fits together")

st.markdown(
    """
1. **You describe the case** — chief complaint and relevant context (symptoms, timing, history you choose to include).

2. **Run analysis** runs the first two computational steps only: a symptom-style summary and a **ranked list of diagnostic possibilities** with short rationales. Nothing about treatment or patient handouts is produced yet.

3. **You pick the working differential** that should drive the rest of the session — the rank that best matches your clinical read for *this* encounter.

4. **Generate treatment & patient summary** runs the next steps using **that** differential: a management-oriented overview and a plain-language summary suitable for patient communication.

Throughout, you can change the selected differential and regenerate those sections without re-running the initial symptom and differential list — so you are not locked into the first suggestion on the list.
"""
)

st.divider()
st.subheader("What each step is meant to do")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Symptom-style summary")
    st.markdown(
        "Turns your free-text narrative into a concise clinical-style picture of the presentation "
        "and pulls out bullet points that matter for reasoning forward."
    )

    st.markdown("#### Ranked differentials")
    st.markdown(
        "Offers several plausible explanations **ranked for discussion**, each with a short rationale. "
        "Think of it as a structured differential list to react to — not a single definitive label."
    )

with col2:
    st.markdown("#### Treatment-oriented overview")
    st.markdown(
        "After you fix a working differential, this step outlines broad management themes "
        "(education, follow-up, safety nets). It is **not** a prescription pad or protocol substitute."
    )

    st.markdown("#### Patient-facing summary")
    st.markdown(
        "Draft language you can adapt when explaining the situation and next steps to a patient — "
        "still under your edit and your institution’s standards."
    )

st.divider()
st.caption(
    "Optional reference material from **ICD-11** may appear when credentials are configured; "
    "see the **ICD-11** page for what that means."
)
