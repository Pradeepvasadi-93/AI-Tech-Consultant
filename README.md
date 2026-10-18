# AI Tech Consultant

AI Tech Consultant combines three AI-assisted business workflows: **Knowledge Brain**, **Inbox Agent**, and **Meeting-to-Scope**. The Knowledge Brain is the shared retrieval service; downstream agents use its evidence to draft customer replies or scope project work.

> **Human review is required for uncertain answers, customer-facing messages, estimates, and scope changes.** Generated output is a draft, not an automatically approved business commitment.

## 1. Project overview

| Task | Purpose | Output | Key control |
|---|---|---|---|
| Task 1 — Knowledge Brain | Ingest and retrieve product/support knowledge | Grounded answers with source references or escalation | Missing evidence must not become invented facts |
| Task 2 — Inbox Agent | Classify customer emails and draft replies | Category, evidence-informed draft, review decision | Approval before sending unless a validated autonomy policy is explicitly enabled |
| Task 3 — Meeting-to-Scope | Convert meeting transcripts into scope and estimates | Requirements, feasibility notes, low/likely/high hours, proposal and change report | Human approval before a revised scope is accepted |

## 2. Architecture

```text
Knowledge sources -> ingestion/parsing -> chunks + embeddings -> vector store
                                                            |
                                                     Knowledge Brain API
                                                       /           \\
                                              Inbox Agent       Meeting-to-Scope
                                              classify/draft    extract/estimate
                                              review/send       propose/compare
                                                       \\           /
                                                       Human review
```

Task 1 project history references sitemap parsing, HTML parsing, an ingestion manifest/checkpoint, image processing, embeddings and Qdrant retrieval. Task 3 documentation describes FastAPI, LangGraph, Groq and Logfire. Verify exact implementation details and versions in the final source tree.

## 3. Suggested repository layout

```text
AI-Tech-Consultant/
├── README.md
├── DESIGN.md
├── EVALS.md
├── AI_LOG.md
├── .env.example
├── .gitignore
├── task1-knowledge-brain/
├── task2-inbox-agent/
├── task3-meeting-to-scope/
└── scripts/
```

This is a recommended integrated layout, not a claim that every directory already exists. Keep actual folder names if they differ and update commands to match.

## 4. Prerequisites and setup

- Python versions compatible with each task's `requirements.txt`.
- Node.js/npm if the Task 2 frontend requires them.
- API keys for the model provider(s) configured in code.
- Vector database and other dependencies required by Task 1.
- Task 1 reachable by downstream services.

For each task, follow its own dependency/configuration instructions. Copy `.env.example` to `.env` where required, and populate variable names defined by that task's config. Task 3 notes have referenced `GROQ_API_KEY`, `GROQ_MODEL`, and a Task 1 API base URL; verify the exact names in the current code. Never commit `.env`, keys, tokens, or customer data. `.env.example` must contain placeholders only.

## 5. Running locally

Reported development ports:
- Task 1: `http://localhost:8000`
- Task 3: `http://localhost:8003`

For Task 3, if the FastAPI object is named `app` in `app/main.py`, the typical command from the Task 3 root is:

```bash
uvicorn app.main:app --reload --port 8003
```

Use the actual entry point if it differs. Swagger UI is commonly available at `/docs` when enabled. The integrated one-command startup should not be considered complete until a root startup script is committed and tested from a clean checkout. Check Task 2's actual backend/frontend commands and ports in its configuration.

## 6. Tests and evaluation

Run Python tests from each task's project root:

```bash
python -m pytest -q
```

Run evaluation scripts from the correct project root using the module path documented by that task. Save raw case-level outputs. Separate API/rate-limit failures from behavioral failures. See [EVALS.md](EVALS.md) for current evidence and limitations.

## 7. Security and production readiness

- Treat webpages, emails, documents and transcripts as untrusted input; resist prompt injection.
- Validate requests and limit uploaded payload sizes.
- Use timeouts and bounded retries for external services.
- Avoid logging credentials or unnecessary customer data.
- Enforce authorization on approval/send endpoints.
- Preserve artifact versions and audit actor, timestamp and decision.
- Make dependency failures visible rather than returning misleading empty answers.
- Verify citations actually support generated claims.
- Add health checks, backups, monitoring and recovery procedures before production deployment.

## 8. Demo sequence

1. Ask Task 1 a question answerable from knowledge and show its source evidence.
2. Ask a question without sufficient evidence and show escalation.
3. Classify an email with Task 2 and review its draft before sending.
4. Generate scope, estimates and a proposal draft with Task 3.
5. Approve a baseline, submit a follow-up transcript, and show the change report.
6. Demonstrate a deliberate failure/uncertainty case and explain the safe behavior.

Use only data approved for demonstration.

## 9. Known gaps and submission checklist

- [ ] Confirm whether the original assignment requires Claude as the central model; Groq configuration alone does not prove compliance.
- [ ] Investigate Task 1 case KB-020, reported as answered when escalation was expected.
- [ ] Verify Task 2 draft quality and the 20-consecutive-unchanged-draft autonomous-send rule.
- [ ] Attach Task 3's final evaluation output and manually review semantic correctness.
- [ ] Run a paired model benchmark with measured quality, latency and cost.
- [ ] Implement and test one-command startup.
- [ ] Record a demo video including a failure case.
- [ ] Test from a clean checkout and exclude secrets.
