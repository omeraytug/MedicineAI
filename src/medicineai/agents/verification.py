"""Verification + patient-facing summary LangChain chain."""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from medicineai.llm_config import build_chat_model
from medicineai.schemas import VerificationOutput

_SYSTEM = """You finalize an educational patient handout. Use plain language (approx. upper middle school level).
Do not claim certainty. Include safety netting (when to seek urgent care). No dosages."""


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
