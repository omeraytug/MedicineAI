"""ICD-11 — plain-language explanation for clinicians (Streamlit multipage)."""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="ICD-11 — MedicineAI", page_icon="📚", layout="wide")

st.title("What is ICD-11?")

st.markdown(
    """
**ICD-11** is the *International Classification of Diseases*, **11th revision**, maintained by the **World Health Organization (WHO)**.

It is the global standard **nomenclature** for diseases, syndromes, injuries, and related health problems — essentially a **shared vocabulary and coding system** so that conditions can be recorded, compared, and reported consistently across countries and health systems.
"""
)

st.subheader("Why clinicians encounter it")
st.markdown(
    """
- **Documentation & billing** — many records and claims use ICD codes.
- **Statistics & public health** — aggregated coding supports epidemiology and policy.
- **Decision support** — systems sometimes link clinical content to ICD entities so suggestions stay aligned with recognised diagnoses.
"""
)

st.subheader("How MedicineAI uses it (when configured)")
st.markdown(
    """
When **WHO ICD-11 API** credentials are available in the deployment environment, MedicineAI may retrieve **short reference snippets** from the ICD-11 **MMS** (Mortality and Morbidity Statistics) foundation to enrich context for the **diagnosis-ranking** step.

That material is **supporting context** for the model — not a mandate to choose one code over another. If credentials are **not** set, the workflow still runs; the diagnosis step relies on the language model without live ICD lookup.

Whether ICD reference appears or not, **your selection of the working differential** in the interface is what ties later steps (management wording and patient summary) to a clinical hypothesis — not an ICD code alone.
"""
)

st.divider()
st.markdown(
    "**Further reading:** [WHO ICD-11](https://www.who.int/standards/classifications/classification-of-diseases) · "
    "[ICD API for developers](https://icd.who.int/icdapi)"
)
