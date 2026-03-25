"""Diagnosis suggestion LangChain chain (uses ICD-11 context in the prompt)."""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from medicineai.llm_config import build_chat_model
from medicineai.schemas import DiagnosisOutput

_SYSTEM = """You are a clinical reasoning assistant for an educational simulation.
Propose a short list of plausible differential diagnoses based on the symptom analysis
and the ICD-11 search snippets (when present). Prefer conditions grounded in the snippets
when they fit; you may add reasonable alternatives if needed. Mark is_high_risk true only
for typically urgent or high-stakes conditions (e.g. sepsis, suspected malignancy, stroke).
This is NOT a substitute for a licensed clinician."""


def build_diagnosis_chain():
    llm = build_chat_model().with_structured_output(DiagnosisOutput)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _SYSTEM),
            (
                "human",
                "Symptom analysis (structured):\n{symptom_json}\n\n"
                "ICD-11 MMS search context (may be empty):\n{icd_context}\n",
            ),
        ]
    )
    return prompt | llm
