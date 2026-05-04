# MedicineAI

Multi-agent clinical decision-support prototype: symptom analysis → diagnosis suggestions → doctor review → treatment proposal → doctor review → patient-facing summary.

## Demo (workflow screenshots)

### 1) Symptom agent

![Symptom agent](artificats/symptom_agent.png)

### 2) Diagnosis + first doctor review

![Diagnosis agent first doctor review](artificats/diagnosis_agent_first_human_review.png)

### 3) Treatment + second doctor review

![Treatment agent second doctor review](artificats/treatment_agent_second_human_review.png)

### 4) Verification / patient output

![Verification agent output](artificats/verification_agent_output.png)

## Architecture

![Architecture flowchart](MedicineAI.png)

## Run

```bash
uv sync
cp .env.example .env   # set OPENAI_API_KEY (+ optional ICD_* credentials)

uv run medicineai validate patients_db/example_case.json
uv run medicineai run patients_db/example_case.json --log session.json
```

The `--log session.json` file contains the full audit trail for that run (agent outputs + doctor decisions).

## Docker (API + Streamlit)

Images are split: **`dockerfiles/Dockerfile.backend`** (FastAPI + agents) and **`dockerfiles/Dockerfile.frontend`** (Streamlit only).

```bash
cp .env.example .env   # set OPENAI_API_KEY, optional ICD_* (same as local dev)
docker compose up --build
```

- **API:** [http://localhost:8000](http://localhost:8000) (OpenAPI: [http://localhost:8000/docs](http://localhost:8000/docs))
- **Streamlit UI:** [http://localhost:8501](http://localhost:8501) — the UI container calls the API at `http://api:8000` via `MEDICINEAI_API_URL`.

`docker compose` reads `.env` from the project root for both services (keys must be present for the API to call models; the UI image does not need API keys unless you add them for future use).

## ICD-11 API (optional)

Set `ICD_CLIENT_ID` and `ICD_CLIENT_SECRET` in `.env`.
If credentials are missing, the app still runs; the diagnosis agent uses only the LLM (with a note in the ICD context section).

If ICD search returns no results or fails, adjust `ICD_RELEASE_ID` (MMS release id) in `.env` according to the WHO ICD-11 API documentation.

## Patient cases

Put JSON inputs in `patients_db/` (validated against `schemas.PatientCase`).
