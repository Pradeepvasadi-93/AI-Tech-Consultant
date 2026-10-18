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

## Observability with Logfire

Task 3 emits spans for the request, full scope-generation run, each LangGraph node, each Groq JSON call, and each Task 1 knowledge query. Span attributes include stage names, counts, model name, status, and error type; transcript text, prompts, API keys, and client content are intentionally not attached as span attributes.

Install Logfire through `requirements.txt` (or run `pip install "logfire>=3.0,<5.0"`). Configure in `.env`:

```env
LOGFIRE_TOKEN=
LOGFIRE_SERVICE_NAME=task3-meeting-to-scope
LOGFIRE_CONSOLE=true
```

- **Local console traces:** leave `LOGFIRE_TOKEN` empty and set `LOGFIRE_CONSOLE=true`. Run the API in a terminal and submit `POST /projects`; inspect the terminal for the nested trace spans.
- **Logfire cloud dashboard:** create a project/token in Logfire and set `LOGFIRE_TOKEN` to that token. Keep it private. The application sends traces to Logfire only when a token is present.
- Set `LOGFIRE_CONSOLE=false` to turn off local console span output.

After changing `.env`, restart Uvicorn. The first `POST /projects` should show a `meeting_to_scope.generate_package` span with child `langgraph.node` spans for `transcript_analyst`, `product_feasibility`, `scope_agent`, `estimation_agent`, and `proposal_review_agent`. Groq calls appear as `groq.json_call`; Task 1 calls appear as `task1.knowledge_query`. Errors are tagged with status and error type.

## Evaluation

Run `python -m evaluation.run_eval --base-url http://127.0.0.1:8003`. The 20-case harness submits transcripts and writes `evaluation/results.csv`; follow-up cases first establish and approve a baseline. It records structural signals and latency but does not automatically grade semantic correctness. Manually score each result against `expected_behavior` before reporting quality. Compare two supported model/configuration choices on the same cases and record quality, cost, latency, and failures.

## Safety and limitations

- All outputs are drafts; human approval is required before simulated proposal delivery.
- Estimates are planning ranges, not guaranteed delivery dates or binding commercial quotes.
- `HOURLY_RATE=0` means no price is quoted.
- Task 1's `/query` response contract may differ from the common fields expected here; verify it against your local API.
- Model-generated requirement IDs can be unstable between meetings; comparison uses IDs first and title matching as a fallback. Review change reports before approving.
