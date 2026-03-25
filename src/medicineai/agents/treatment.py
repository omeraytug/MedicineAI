"""Treatment proposal LangChain chain (non-prescriptive)."""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from medicineai.llm_config import build_chat_model
from medicineai.schemas import TreatmentOutput

_SYSTEM = """
<context>
You are generating a non-prescriptive treatment draft for doctor review.
</context>
<objective>
Given the patient JSON and the selected diagnosis text from the previous step,
produce general management themes and supportive measures that a clinician would discuss.
</objective>
<style>
Non-prescriptive: do NOT include drug dosages, routes, or definitive prescriptions.
Respect documented allergies when provided.
Keep content general and actionable as "discussion points" for a clinician.
Output MUST match the structured schema fields exactly.
</style>
<tone>
Professional, respectful, safety-aware.
</tone>
<audience>
Supervising doctor reviewing a treatment draft, not the patient directly.
</audience>
<response>
Fill all required fields and do not add extra keys.
</response>
""".strip()


def build_treatment_chain():
    llm = build_chat_model().with_structured_output(TreatmentOutput)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _SYSTEM),
            (
                "human",
                "Patient case:\n{case_text}\n\n"
                "Working diagnosis selected for doctor review:\n{diagnosis_line}\n",
            ),
        ]
    )
    return prompt | llm
