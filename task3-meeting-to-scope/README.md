# Task 3 — Meeting-to-Scope (LangGraph + Groq)

Python/FastAPI application using **LangGraph** to orchestrate five distinct agent roles and **Groq-hosted LLMs** for transcript analysis, feasibility classification, scope generation, estimates, and proposal drafting. Task 1 remains the product knowledge source.

## Windows setup

Extract this folder to `D:\Assignment\AI-Tech-Consultant\task3-meeting-to-scope`.

```powershell
cd D:\Assignment\AI-Tech-Consultant
.\.venv\Scripts\Activate.ps1
cd .\task3-meeting-to-scope
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Set a valid Groq API key and a model currently enabled for your Groq account:

```env
GROQ_API_KEY=your_actual_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b
TASK1_API_BASE_URL=http://127.0.0.1:8000
TASK1_API_KEY=
DATABASE_PATH=data/meeting_to_scope.db
HOURLY_RATE=0
CURRENCY=USD
```

Model availability changes; if the example model is unavailable to your account, replace it with a currently supported Groq model. Do not commit `.env`.

Keep Task 1 running on port 8000. Start Task 3:

```powershell
uvicorn app.main:app --reload --port 8003
```

Open `http://127.0.0.1:8003/docs`.

## LangGraph orchestration

The compiled graph runs these nodes in order:

`Transcript Analyst -> Product Feasibility -> Scope Agent -> Estimation Agent -> Proposal and Review Agent`

The transcript analyst chunks long transcripts, retains short source excerpts, and merges extracted requirements. The feasibility node calls Task 1 `/query` for each requirement; missing Task 1 evidence is marked for clarification rather than assumed to prove a feature is unavailable. Deterministic Python handles persistence, versioning, approval gates, audit events, and change comparison.

## Demo workflow

1. `POST /projects` with the client/project name and transcript from `data/sample_transcripts/meeting_a.json`.
2. Review requirements, feasibility evidence, scope, estimates, assumptions, risks, and proposal.
3. `POST /projects/{id}/approve` with `{"version":1,"reviewer":"Demo reviewer","notes":"Reviewed"}` to establish the approved baseline.
4. `POST /projects/{id}/meetings/follow-up` with the transcript from `meeting_c.json`.
5. Inspect added/modified/removed/out-of-scope requirements. The approved baseline is not silently overwritten.
6. Review and approve the revised version explicitly.
7. `POST /projects/{id}/proposal/send` for an approved version. Delivery is simulated only; no client email is sent.

## Evaluation

Run `python -m evaluation.run_eval --base-url http://127.0.0.1:8003`. The 20-case harness submits transcripts and writes `evaluation/results.csv`; follow-up cases first establish and approve a baseline. It records structural signals and latency but does not automatically grade semantic correctness. Manually score each result against `expected_behavior` before reporting quality. Compare two supported model/configuration choices on the same cases and record quality, cost, latency, and failures.

## Safety and limitations

- All outputs are drafts; human approval is required before simulated proposal delivery.
- Estimates are planning ranges, not guaranteed delivery dates or binding commercial quotes.
- `HOURLY_RATE=0` means no price is quoted.
- Task 1's `/query` response contract may differ from the common fields expected here; verify it against your local API.
- Model-generated requirement IDs can be unstable between meetings; comparison uses IDs first and title matching as a fallback. Review change reports before approving.
