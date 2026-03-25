"""Treatment proposal LangChain chain (non-prescriptive)."""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from medicineai.llm_config import build_chat_model
from medicineai.schemas import TreatmentOutput

_SYSTEM = """You are assisting in an educational workflow. Propose general management themes
and supportive measures only—no drug dosages, no definitive prescriptions. Emphasize
discussion with a qualified clinician. Respect documented allergies if provided."""


def build_treatment_chain():
    llm = build_chat_model().with_structured_output(TreatmentOutput)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _SYSTEM),
            (
                "human",
                "Patient case:\n{case_text}\n\n"
                "Working diagnosis selected for the simulation:\n{diagnosis_line}\n",
            ),
        ]
    )
    return prompt | llm
