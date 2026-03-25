"""Verification + patient-facing summary LangChain chain."""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from medicineai.llm_config import build_chat_model
from medicineai.schemas import VerificationOutput

_SYSTEM = """
<context>
You are creating a patient-facing explanation.
This output must not be used as medical advice.
</context>
<objective>
Transform the case context + chosen diagnosis context + treatment draft into:
- a plain-language summary a patient can understand, and
- clear next steps and safety-net guidance.
</objective>
<style>
Use plain language (upper middle school level).
Do not claim certainty. No dosages and no prescriptions.
Safety net: include warning signs and when to seek urgent care.
Output MUST match the structured schema fields exactly:
- patient_title
- patient_summary
- what_to_do_next (list of strings)
- when_to_seek_care
</style>
<tone>
Kind, clear, non-alarmist, safety-focused.
</tone>
<audience>
The patient/reader (lay audience).
</audience>
<response>
Fill all required fields; do not add extra keys.
</response>
""".strip()


def build_verification_chain():
    llm = build_chat_model().with_structured_output(VerificationOutput)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _SYSTEM),
            (
                "human",
                "Patient case (reference):\n{case_text}\n\n"
                "Diagnosis context:\n{diagnosis_line}\n\n"
                "Proposed management (draft):\n{treatment_json}\n",
            ),
        ]
    )
    return prompt | llm
