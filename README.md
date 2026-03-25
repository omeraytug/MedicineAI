# MedicineAI

Educational **multi-agent CLI** for exploring a sequential workflow: symptom analysis → diagnosis suggestions (with optional [WHO ICD-11 API](https://icd.who.int/icdapi/) search context) → doctor review → treatment proposal → doctor review → patient-facing summary.

**Not for clinical use.** This is a school project prototype; outputs are **not** medical advice.

## Architecture

- **LangChain** (`ChatOpenAI` + structured output) for four agents.
- **Plain Python orchestrator** for the state machine, loops, and terminal-based doctor reviews.
- Optional **ICD-11 MMS search** via OAuth2 client credentials (see `.env.example`).

## Setup

Requires **Python 3.14+** (see `.python-version`). This repo is set up for **[uv](https://docs.astral.sh/uv/)** (lockfile + project env).

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```bash
cd MedicineAI
uv sync                    # creates .venv and installs deps from uv.lock
cp .env.example .env       # add OPENAI_API_KEY (and optionally ICD_* credentials)
```

`uv sync` installs the package in editable mode from `pyproject.toml`. After that you can run commands with **`uv run`** (uses the project venv without activating it):

```bash
uv run medicineai validate patients_db/example_case.json
uv run medicineai run patients_db/example_case.json --log session.json
```

`run` needs `OPENAI_API_KEY`; `validate` does not call the APIs.

**Adding or upgrading dependencies:** change `pyproject.toml` and run `uv lock` (and commit `uv.lock`), or use `uv add <package>`.


## Usage

Validate a patient JSON file:

```bash
uv run medicineai validate patients_db/example_case.json
```

Run the full workflow (interactive prompts for doctor review steps):

```bash
uv run medicineai run patients_db/example_case.json --log session.json
```

Alternative entry point:

```bash
uv run python main.py run patients_db/example_case.json
```

## Patient case JSON

Example cases live under [`patients_db/`](patients_db/): `example_case.json` (sore throat), plus `cough_acute_respiratory.json`, `headache_tension_like.json`, `gastroenteritis_acute.json`, `low_back_strain.json`, `contact_dermatitis_rash.json`. Fields are defined in `schemas.PatientCase` (`demographics`, `chief_complaint`, `symptoms`, optional `history`, `medications`, `allergies`, `vitals`, `labs`).

## ICD-11 API

Register at the [WHO ICD API](https://icd.who.int/icdapi/Account/Register), set `ICD_CLIENT_ID` and `ICD_CLIENT_SECRET` in `.env`. If credentials are missing, the app still runs; the diagnosis agent uses only the LLM (with a note in the ICD context section).

If search URLs fail, check the current release id for MMS in the official WHO ICD API documentation and adjust `ICD_RELEASE_ID`.

