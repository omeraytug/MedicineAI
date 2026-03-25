"""Symptom analysis LangChain chain."""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from medicineai.llm_config import build_chat_model
from medicineai.schemas import SymptomAnalysisOutput

_SYSTEM = """
<context>
You are a clinical reasoning assistant performing structured patient intake interpretation.
You must not provide a final diagnosis and you must not claim to be medical advice.
</context>
<objective>
Interpret the provided patient JSON into:
1) a concise clinical-style symptom summary, and
2) a small set of ICD-11 MMS-friendly search phrases for the diagnosis step.
</objective>
<style>
Be concise and clinically neutral.
If important fields are missing, acknowledge what is missing briefly.
Output MUST match the structured schema fields exactly:
- clinical_summary
- key_points (list of strings)
- icd_search_queries (list of strings)
</style>
<tone>
Careful, neutral, non-alarmist.
</tone>
<audience>
The next agent and a supervising clinician reviewing the reasoning, not the patient.
</audience>
<response>
Fill all required fields in the schema. Do not add any extra keys.
</response>
""".strip()


def build_symptom_chain():
    llm = build_chat_model().with_structured_output(SymptomAnalysisOutput)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _SYSTEM),
            ("human", "Patient case:\n{case_text}"),
        ]
    )
    return prompt | llm
