"""Symptom analysis LangChain chain."""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from medicineai.llm_config import build_chat_model
from medicineai.schemas import SymptomAnalysisOutput

_SYSTEM = """You are a clinical reasoning assistant for an educational simulation.
You do NOT provide a final diagnosis. Your job is to interpret structured patient data
and produce a concise symptom-oriented summary plus ICD-friendly search phrases.
Use careful, neutral clinical language. If data is missing, say so briefly."""


def build_symptom_chain():
    llm = build_chat_model().with_structured_output(SymptomAnalysisOutput)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _SYSTEM),
            ("human", "Patient case:\n{case_text}"),
        ]
    )
    return prompt | llm
