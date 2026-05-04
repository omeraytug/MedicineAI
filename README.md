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

Streamlit UI (optional):

```bash
API_URL=http://127.0.0.1:8000 uv run streamlit run src/frontend/app.py
```

## Docker (API + Streamlit)

Images are split: **`dockerfiles/Dockerfile.backend`** (FastAPI + agents) and **`dockerfiles/Dockerfile.frontend`** (Streamlit only).

```bash
cp .env.example .env   # set OPENAI_API_KEY, optional ICD_* (same as local dev)
docker compose up --build
```

- **API:** [http://localhost:8000](http://localhost:8000) (OpenAPI: [http://localhost:8000/docs](http://localhost:8000/docs))
- **Streamlit UI:** [http://localhost:8501](http://localhost:8501) — the UI container calls the API at `http://api:8000` via `API_URL`.

`docker compose` reads `.env` from the project root for both services (keys must be present for the API to call models; the UI image does not need API keys unless you add them for future use).

### Azure App Service (two separate Web Apps)

Compose hostname **`http://api:8000` does not exist on Azure.** Each app has its own URL. Configure **Application settings** (environment variables) on the Web App, not only in the image:

| Web App | Setting | Value |
|--------|---------|--------|
| **Backend** (FastAPI) | `WEBSITES_PORT` | `8000` |
| **Backend** | Same `.env` keys as locally (`OPENAI_API_KEY`, optional ICD-*, etc.) | … |
| **Frontend** (Streamlit) | `WEBSITES_PORT` | `8501` |
| **Frontend** | `API_URL` | **`https://<your-backend-app-name>.azurewebsites.net`** (no trailing slash; legacy: `MEDICINEAI_API_URL`) |

Use **`https://`** for Azure URLs. Restart both apps after changing settings.

Optional on the **backend**: `MEDICINEAI_CORS_ORIGINS` = `https://<your-frontend-app>.azurewebsites.net` (only needed if a **browser** calls the API directly; the default Streamlit app calls the API from **Python** on the server, so CORS is often unnecessary).

**Check:** open `https://<backend>/health` in a browser; it should return `{"status":"ok"}`.

## ICD-11 API (optional)

Set `ICD_CLIENT_ID` and `ICD_CLIENT_SECRET` in `.env`.
If credentials are missing, the app still runs; the diagnosis agent uses only the LLM (with a note in the ICD context section).

If ICD search returns no results or fails, adjust `ICD_RELEASE_ID` (MMS release id) in `.env` according to the WHO ICD-11 API documentation.

## Patient cases

Put JSON inputs in `patients_db/` (validated against `schemas.PatientCase`).
