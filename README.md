# MedicineAI

Clinical decision-support workflow: **symptom analysis** → **ranked differentials** → **doctor selection** → **treatment** → **patient-facing summary**.

You can run the same agent stack from the **terminal** (interactive CLI), **HTTP API**, or **Streamlit UI**.

---

## Ways to run

| Mode | What runs | Best for |
|------|-----------|----------|
| **CLI** (`medicineai run`) | Full pipeline with **interactive** prompts in the terminal (same agents as originally shipped) | Local JSON cases, keyboard review |
| **API** (`/v1/analyze` + `/v1/continue`) | First request: symptom + diagnosis only; second: treatment + summary for a chosen differential | Apps, automation, Streamlit |
| **API** (`/v1/ask`) | Full non-interactive pipeline in **one** request (optional; scripts/tools) | Batch / legacy integrations |
| **Streamlit** | Doctor-first flow aligned with `/v1/analyze` + `/v1/continue` | Web UI |

Setup once:

```bash
uv sync
cp .env.example .env   # OPENAI_API_KEY; optional ICD_* for WHO ICD-11 lookup
```

---

## Terminal (CLI) — full workflow, interactive

You **can** run the multi-agent system from the terminal. It loads a **patient case JSON** and walks through **symptom → diagnosis review → treatment review → verification** with prompts in the shell.

```bash
uv run medicineai validate patients_db/example_case.json
uv run medicineai run patients_db/example_case.json --log session.json
```

`--log session.json` writes the audit trail (agent outputs and review choices).

This path uses `run_case(..., interactive=True)` and does **not** use the split `/v1/analyze` + `/v1/continue` HTTP flow.

---

## HTTP API

Start the server (local):

```bash
uv run uvicorn medicineai.api.main:app --host 127.0.0.1 --port 8000
```

OpenAPI: [http://localhost:8000/docs](http://localhost:8000/docs)

| Endpoint | Purpose |
|----------|---------|
| `POST /v1/analyze` | Symptom agent + diagnosis rankings (+ ICD context). **No** treatment or patient summary. |
| `POST /v1/continue` | Pass prior `symptom` + `diagnosis` JSON and a `diagnosis_index`; runs **treatment + verification** only. |
| `POST /v1/ask` | One-shot non-interactive **full** workflow (optional). |

---

## Streamlit UI

Runs against the API base URL from **`API_URL`** (falls back to `MEDICINEAI_API_URL`, then `http://localhost:8000`).

```bash
# Terminal 1
uv run uvicorn medicineai.api.main:app --host 127.0.0.1 --port 8000

# Terminal 2
API_URL=http://127.0.0.1:8000 uv run streamlit run src/frontend/app.py
```

Typical flow: **Run analysis** → review §1–2 → choose a working differential → **Generate treatment & patient summary** (calls `/v1/continue`).

---

## Docker (API + Streamlit)

Images: **`dockerfiles/Dockerfile.backend`** (API + agents), **`dockerfiles/Dockerfile.frontend`** (Streamlit only).

```bash
cp .env.example .env
docker compose up --build
```

- API: [http://localhost:8000](http://localhost:8000)
- UI: [http://localhost:8501](http://localhost:8501) — set **`API_URL=http://api:8000`** in Compose for the UI service.

---

## Azure App Service (two Web Apps)

Compose name **`http://api:8000`** only applies inside Docker Compose. On Azure, set **`API_URL`** on the **frontend** app to your backend URL, e.g. `https://<backend-app>.azurewebsites.net` (no trailing slash).

| App | Application setting | Example |
|-----|---------------------|---------|
| Backend | `WEBSITES_PORT` | `8000` |
| Backend | `.env`-style keys | `OPENAI_API_KEY`, optional ICD-* |
| Frontend | `WEBSITES_PORT` | `8501` |
| Frontend | `API_URL` | `https://<backend-app>.azurewebsites.net` |

Restart apps after changing configuration. Check backend: `GET /health` → `{"status":"ok"}`.

---

## Screenshots

### CLI workflow (terminal)

![Symptom agent](artificats/symptom_agent.png)

![Diagnosis + first doctor review](artificats/diagnosis_agent_first_human_review.png)

![Treatment + second doctor review](artificats/treatment_agent_second_human_review.png)

![Verification agent output](artificats/verification_agent_output.png)

### Web UI (Streamlit)

Case intake and **Run analysis**:

![Streamlit case input](docs/images/ui-case-input.png)

Symptom + differentials and working-differential selection:

![Streamlit differentials and doctor selection](docs/images/ui-differentials.png)

Treatment proposal and patient-facing summary:

![Streamlit treatment and patient summary](docs/images/ui-plan-summary.png)

---

## Architecture

![Architecture flowchart](MedicineAI.png)

---

## ICD-11 API (optional)

Set `ICD_CLIENT_ID` and `ICD_CLIENT_SECRET` in `.env`. Without them, diagnosis still runs using the LLM; ICD context may be empty.

Tune `ICD_RELEASE_ID` per [WHO ICD-11 API](https://icd.who.int/icdapi) documentation if lookups fail.

---

## Patient cases

Put JSON inputs in **`patients_db/`**, validated against `schemas.PatientCase`. Use with **`medicineai validate`** / **`medicineai run`**.
