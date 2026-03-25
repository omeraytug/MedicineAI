# MedicineAI

Educational **multi-agent CLI** for exploring a sequential workflow: symptom analysis → diagnosis suggestions (with optional [WHO ICD-11 API](https://icd.who.int/icdapi/) search context) → doctor review → treatment proposal → doctor review → patient-facing summary.

**Not for clinical use.** This is a school project prototype; outputs are **not** medical advice.

## Architecture

- **LangChain** (`ChatOpenAI` + structured output) for four agents.
- **Plain Python orchestrator** for the state machine, loops, and terminal-based doctor reviews.
- Optional **ICD-11 MMS search** via OAuth2 client credentials (see `.env.example`).

## Setup

Requires **Python 3.10+**. Use a virtual environment:

```bash
cd MedicineAI
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
cp .env.example .env        # add OPENAI_API_KEY (and optionally ICD_* credentials)
```

`run` needs `OPENAI_API_KEY`; `validate` does not call the APIs.

## Usage

Validate a patient JSON file:

```bash
medicineai validate examples/case.json
```

Run the full workflow (interactive prompts for doctor review steps):

```bash
medicineai run examples/case.json --log session.json
```

Or:

```bash
python main.py run examples/case.json
```

## Patient case JSON

See [`examples/case.json`](examples/case.json). Fields are defined in `schemas.PatientCase` (`demographics`, `chief_complaint`, `symptoms`, optional `history`, `medications`, `allergies`, `vitals`, `labs`).

## ICD-11 API

Register at the [WHO ICD API](https://icd.who.int/icdapi/Account/Register), set `ICD_CLIENT_ID` and `ICD_CLIENT_SECRET` in `.env`. If credentials are missing, the app still runs; the diagnosis agent uses only the LLM (with a note in the ICD context section).

If search URLs fail, check the current release id for MMS in the official WHO ICD API documentation and adjust `ICD_RELEASE_ID`.

## Remote

```bash
git remote add origin git@github.com:omeraytug/MedicineAI.git   # if not already added
git push -u origin main
```
